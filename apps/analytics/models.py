from django.db import models
from django.utils import timezone


class RealtimeMetric(models.Model):
    """Модель для хранения метрик в реальном времени"""
    metric_name = models.CharField(max_length=100, db_index=True)
    value = models.FloatField()
    timestamp = models.DateTimeField(default=timezone.now, db_index=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = 'analytics_realtime_metrics'
        routing_key = 'analytics'  # Для роутинга в аналитическую БД
        indexes = [
            models.Index(fields=['metric_name', 'timestamp']),
            models.Index(fields=['timestamp']),
        ]


class ConversionEvent(models.Model):
    """Модель для отслеживания конверсий"""
    event_type = models.CharField(max_length=50)
    reservation_id = models.UUIDField(db_index=True)
    user_id = models.IntegerField(db_index=True)
    timestamp = models.DateTimeField(default=timezone.now)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = 'analytics_conversion_events'
        routing_key = 'analytics'
        indexes = [
            models.Index(fields=['event_type', 'timestamp']),
            models.Index(fields=['reservation_id']),
            models.Index(fields=['user_id', 'timestamp']),
        ]


class DailyAnalytics(models.Model):
    """Модель для ежедневной аналитики"""
    date = models.DateField(unique=True, db_index=True)
    reservations_created = models.IntegerField(default=0)
    reservations_confirmed = models.IntegerField(default=0)
    reservations_cancelled = models.IntegerField(default=0)
    total_revenue = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    active_products = models.IntegerField(default=0)
    unique_users = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'analytics_daily_stats'
        routing_key = 'analytics'
        ordering = ['-date']