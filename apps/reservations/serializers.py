from rest_framework import serializers
from django.utils import timezone
from apps.reservations.models import Reservation, ReservationStatus
from apps.products.serializers import ProductBriefSerializer
from apps.users.serializers import UserSerializer


class ReservationCreateSerializer(serializers.Serializer):
    """Сериализатор для создания бронирования"""

    product_id = serializers.IntegerField()
    quantity = serializers.IntegerField(min_value=1, max_value=100)
    customer_info = serializers.JSONField(required=False, default=dict)
    notes = serializers.CharField(max_length=500, required=False, allow_blank=True)

    def validate_product_id(self, value):
        """Валидация существования товара"""
        from apps.products.models import Product

        try:
            product = Product.objects.get(id=value, is_active=True)
        except Product.DoesNotExist:
            raise serializers.ValidationError('Товар не найден или неактивен')

        return value

    def validate_quantity(self, value):
        """Валидация количества"""
        if value <= 0:
            raise serializers.ValidationError('Количество должно быть больше 0')
        if value > 100:
            raise serializers.ValidationError('Максимальное количество: 100')
        return value


class ReservationSerializer(serializers.ModelSerializer):
    """Основной сериализатор бронирования"""

    product = ProductBriefSerializer(read_only=True)
    user = UserSerializer(read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    is_expired = serializers.BooleanField(read_only=True)
    time_remaining = serializers.SerializerMethodField()
    can_confirm = serializers.SerializerMethodField()
    can_cancel = serializers.SerializerMethodField()

    class Meta:
        model = Reservation
        fields = [
            'id', 'user', 'product', 'quantity', 'status', 'status_display',
            'price_per_item', 'total_price', 'expires_at', 'created_at',
            'updated_at', 'confirmed_at', 'cancelled_at', 'is_expired',
            'time_remaining', 'can_confirm', 'can_cancel', 'notes',
            'customer_info'
        ]
        read_only_fields = [
            'id', 'user', 'price_per_item', 'total_price', 'expires_at',
            'created_at', 'updated_at', 'confirmed_at', 'cancelled_at'
        ]

    def get_time_remaining(self, obj):
        """Оставшееся время брони в секундах"""
        if obj.status != ReservationStatus.PENDING:
            return None

        if obj.is_expired:
            return 0

        remaining = obj.expires_at - timezone.now()
        return max(0, int(remaining.total_seconds()))

    def get_can_confirm(self, obj):
        """Можно ли подтвердить бронирование"""
        return (
                obj.status == ReservationStatus.PENDING and
                not obj.is_expired
        )

    def get_can_cancel(self, obj):
        """Можно ли отменить бронирование"""
        return obj.status == ReservationStatus.PENDING


class ReservationUpdateSerializer(serializers.ModelSerializer):
    """Сериализатор для обновления бронирования"""

    class Meta:
        model = Reservation
        fields = ['notes', 'customer_info']

    def validate(self, attrs):
        """Валидация возможности обновления"""
        if self.instance.status != ReservationStatus.PENDING:
            raise serializers.ValidationError(
                'Можно изменять только активные бронирования'
            )

        if self.instance.is_expired:
            raise serializers.ValidationError('Бронирование истекло')

        return attrs


class ReservationStatsSerializer(serializers.Serializer):
    """Сериализатор статистики бронирований"""

    total_reservations = serializers.IntegerField()
    active_reservations = serializers.IntegerField()
    confirmed_reservations = serializers.IntegerField()
    cancelled_reservations = serializers.IntegerField()
    expired_reservations = serializers.IntegerField()
    total_revenue = serializers.DecimalField(max_digits=12, decimal_places=2)
    average_order_value = serializers.DecimalField(max_digits=10, decimal_places=2)
    conversion_rate = serializers.FloatField()