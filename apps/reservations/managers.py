from django.db import models
from django.utils import timezone
from datetime import timedelta


class ReservationManager(models.Manager):
    """Менеджер для модели Reservation"""

    def active(self):
        """Активные бронирования"""
        from apps.reservations.models import ReservationStatus
        return self.filter(status=ReservationStatus.PENDING)

    def expired(self):
        """Просроченные бронирования"""
        from apps.reservations.models import ReservationStatus
        return self.filter(
            status=ReservationStatus.PENDING,
            expires_at__lt=timezone.now()
        )

    def expiring_soon(self, minutes=15):
        """Бронирования, истекающие в ближайшее время"""
        from apps.reservations.models import ReservationStatus
        threshold = timezone.now() + timedelta(minutes=minutes)
        return self.filter(
            status=ReservationStatus.PENDING,
            expires_at__lte=threshold,
            expires_at__gt=timezone.now()
        )

    def confirmed(self):
        """Подтвержденные бронирования"""
        from apps.reservations.models import ReservationStatus
        return self.filter(status=ReservationStatus.CONFIRMED)

    def cancelled(self):
        """Отмененные бронирования"""
        from apps.reservations.models import ReservationStatus
        return self.filter(status__in=[
            ReservationStatus.CANCELLED,
            ReservationStatus.EXPIRED
        ])

    def by_user(self, user):
        """Бронирования пользователя"""
        return self.filter(user=user)

    def by_product(self, product):
        """Бронирования товара"""
        return self.filter(product=product)

    def today(self):
        """Бронирования за сегодня"""
        today = timezone.now().date()
        return self.filter(created_at__date=today)

    def this_week(self):
        """Бронирования за эту неделю"""
        week_ago = timezone.now() - timedelta(days=7)
        return self.filter(created_at__gte=week_ago)

    def revenue_stats(self, start_date=None, end_date=None):
        """Статистика выручки"""
        from apps.reservations.models import ReservationStatus
        queryset = self.filter(status=ReservationStatus.CONFIRMED)

        if start_date:
            queryset = queryset.filter(confirmed_at__gte=start_date)
        if end_date:
            queryset = queryset.filter(confirmed_at__lte=end_date)

        return queryset.aggregate(
            total_revenue=models.Sum('total_price'),
            count=models.Count('id'),
            avg_order_value=models.Avg('total_price')
        )