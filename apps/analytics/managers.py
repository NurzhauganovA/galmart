from django.db import models
from django.utils import timezone
from datetime import timedelta


class RealtimeMetricManager(models.Manager):
    """Менеджер для метрик в реальном времени"""

    def last_hour(self):
        """Метрики за последний час"""
        hour_ago = timezone.now() - timedelta(hours=1)
        return self.filter(timestamp__gte=hour_ago)

    def last_day(self):
        """Метрики за последний день"""
        day_ago = timezone.now() - timedelta(days=1)
        return self.filter(timestamp__gte=day_ago)

    def by_metric(self, metric_name):
        """Метрики по названию"""
        return self.filter(metric_name=metric_name)

    def aggregate_by_hour(self, metric_name, hours=24):
        """Агрегация метрик по часам"""
        since = timezone.now() - timedelta(hours=hours)
        return self.filter(
            metric_name=metric_name,
            timestamp__gte=since
        ).extra(
            select={'hour': "date_trunc('hour', timestamp)"}
        ).values('hour').annotate(
            total_value=models.Sum('value'),
            avg_value=models.Avg('value'),
            count=models.Count('id')
        ).order_by('hour')


class ConversionEventManager(models.Manager):
    """Менеджер для событий конверсии"""

    def by_event_type(self, event_type):
        """События по типу"""
        return self.filter(event_type=event_type)

    def funnel_data(self, days=7):
        """Данные воронки конверсии"""
        since = timezone.now() - timedelta(days=days)
        return self.filter(timestamp__gte=since).values('event_type').annotate(
            count=models.Count('id')
        ).order_by('event_type')

    def conversion_rate(self, from_event, to_event, days=7):
        """Расчет коэффициента конверсии"""
        since = timezone.now() - timedelta(days=days)

        from_count = self.filter(
            event_type=from_event,
            timestamp__gte=since
        ).count()

        to_count = self.filter(
            event_type=to_event,
            timestamp__gte=since
        ).count()

        if from_count == 0:
            return 0

        return (to_count / from_count) * 100