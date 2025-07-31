from django.db import models
from django.utils import timezone


class TimestampedManager(models.Manager):
    """Базовый менеджер для моделей с timestamp полями"""

    def recent(self, days=7):
        """Записи за последние N дней"""
        since = timezone.now() - timezone.timedelta(days=days)
        return self.filter(created_at__gte=since)

    def today(self):
        """Записи за сегодня"""
        today = timezone.now().date()
        return self.filter(created_at__date=today)

    def this_month(self):
        """Записи за этот месяц"""
        now = timezone.now()
        start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        return self.filter(created_at__gte=start_of_month)