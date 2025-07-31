from rest_framework import serializers
from apps.analytics.models import RealtimeMetric, ConversionEvent, DailyAnalytics


class RealtimeMetricSerializer(serializers.ModelSerializer):
    """Сериализатор для метрик в реальном времени"""

    class Meta:
        model = RealtimeMetric
        fields = ['id', 'metric_name', 'value', 'timestamp', 'metadata']
        read_only_fields = ['id', 'timestamp']


class ConversionEventSerializer(serializers.ModelSerializer):
    """Сериализатор для событий конверсии"""

    class Meta:
        model = ConversionEvent
        fields = ['id', 'event_type', 'reservation_id', 'user_id', 'timestamp', 'metadata']
        read_only_fields = ['id', 'timestamp']


class DailyAnalyticsSerializer(serializers.ModelSerializer):
    """Сериализатор для ежедневной аналитики"""

    conversion_rate = serializers.SerializerMethodField()
    avg_order_value = serializers.SerializerMethodField()

    class Meta:
        model = DailyAnalytics
        fields = [
            'id', 'date', 'reservations_created', 'reservations_confirmed',
            'reservations_cancelled', 'total_revenue', 'active_products',
            'unique_users', 'conversion_rate', 'avg_order_value', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']

    def get_conversion_rate(self, obj):
        """Коэффициент конверсии"""
        if obj.reservations_created == 0:
            return 0
        return round((obj.reservations_confirmed / obj.reservations_created) * 100, 2)

    def get_avg_order_value(self, obj):
        """Средний чек"""
        if obj.reservations_confirmed == 0:
            return 0
        return round(float(obj.total_revenue) / obj.reservations_confirmed, 2)