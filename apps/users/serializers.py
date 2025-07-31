from rest_framework import serializers
from django.contrib.auth import get_user_model, authenticate
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    """Основной сериализатор пользователя"""

    full_name = serializers.SerializerMethodField()
    reservations_count = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name',
            'full_name', 'phone', 'is_active', 'is_verified',
            'date_joined', 'reservations_count'
        ]
        read_only_fields = ['id', 'date_joined', 'is_verified']

    def get_full_name(self, obj):
        """Полное имя пользователя"""
        return f"{obj.first_name} {obj.last_name}".strip()

    def get_reservations_count(self, obj):
        """Количество бронирований пользователя"""
        return getattr(obj, 'reservations_count', obj.reservations.count())


class UserRegistrationSerializer(serializers.ModelSerializer):
    """Сериализатор для регистрации пользователя"""

    password = serializers.CharField(write_only=True, validators=[validate_password])
    password_confirm = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = [
            'username', 'email', 'password', 'password_confirm',
            'first_name', 'last_name', 'phone'
        ]

    def validate(self, attrs):
        """Валидация паролей"""
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError({
                'password_confirm': 'Пароли не совпадают'
            })
        return attrs

    def validate_email(self, value):
        """Валидация уникальности email"""
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError(
                'Пользователь с таким email уже существует'
            )
        return value

    def create(self, validated_data):
        """Создание пользователя"""
        validated_data.pop('password_confirm')
        password = validated_data.pop('password')

        user = User.objects.create_user(**validated_data)
        user.set_password(password)
        user.is_active = False  # Требует активации
        user.save()

        return user


class UserProfileSerializer(serializers.ModelSerializer):
    """Сериализатор профиля пользователя"""

    full_name = serializers.SerializerMethodField()
    avatar_url = serializers.SerializerMethodField()
    stats = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name',
            'full_name', 'phone', 'avatar_url', 'date_joined',
            'last_login', 'is_verified', 'stats'
        ]
        read_only_fields = [
            'id', 'username', 'date_joined', 'last_login', 'is_verified'
        ]

    def get_full_name(self, obj):
        return f"{obj.first_name} {obj.last_name}".strip()

    def get_avatar_url(self, obj):
        """URL аватара пользователя"""
        # Интеграция с Gravatar или локальными аватарами
        import hashlib
        email_hash = hashlib.md5(obj.email.lower().encode()).hexdigest()
        return f"https://www.gravatar.com/avatar/{email_hash}?d=identicon&s=150"

    def get_stats(self, obj):
        """Статистика пользователя"""
        from apps.reservations.models import Reservation, ReservationStatus

        return {
            'total_reservations': obj.reservations.count(),
            'active_reservations': obj.reservations.filter(
                status=ReservationStatus.PENDING
            ).count(),
            'confirmed_reservations': obj.reservations.filter(
                status=ReservationStatus.CONFIRMED
            ).count(),
        }


class PasswordChangeSerializer(serializers.Serializer):
    """Сериализатор для смены пароля"""

    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True, validators=[validate_password])
    new_password_confirm = serializers.CharField(required=True)

    def validate_old_password(self, value):
        """Валидация старого пароля"""
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError('Неверный старый пароль')
        return value

    def validate(self, attrs):
        """Валидация новых паролей"""
        if attrs['new_password'] != attrs['new_password_confirm']:
            raise serializers.ValidationError({
                'new_password_confirm': 'Пароли не совпадают'
            })
        return attrs


class PasswordResetSerializer(serializers.Serializer):
    """Сериализатор для сброса пароля"""

    email = serializers.EmailField(required=True)

    def validate_email(self, value):
        """Валидация существования email"""
        # Не раскрываем информацию о существовании пользователя
        return value


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Кастомный сериализатор для JWT токенов"""

    def validate(self, attrs):
        data = super().validate(attrs)

        # Добавляем дополнительную информацию о пользователе
        data['user'] = {
            'id': self.user.id,
            'username': self.user.username,
            'email': self.user.email,
            'full_name': f"{self.user.first_name} {self.user.last_name}".strip(),
            'is_verified': getattr(self.user, 'is_verified', True),
        }

        return data