from celery import shared_task
from django.utils import timezone
from django.db.models import Count, Sum, Avg
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)


@shared_task(bind=True)
def update_daily_analytics(self):
    """
    Обновление ежедневной аналитики
    """
    try:
        from apps.analytics.services import AnalyticsService
        from apps.reservations.models import Reservation, ReservationStatus
        from apps.products.models import Product

        service = AnalyticsService()
        today = timezone.now().date()

        # Собираем статистику за сегодня
        daily_stats = {
            'date': today,
            'reservations_created': Reservation.objects.filter(
                created_at__date=today
            ).count(),
            'reservations_confirmed': Reservation.objects.filter(
                confirmed_at__date=today,
                status=ReservationStatus.CONFIRMED
            ).count(),
            'reservations_cancelled': Reservation.objects.filter(
                cancelled_at__date=today,
                status__in=[ReservationStatus.CANCELLED, ReservationStatus.EXPIRED]
            ).count(),
            'total_revenue': Reservation.objects.filter(
                confirmed_at__date=today,
                status=ReservationStatus.CONFIRMED
            ).aggregate(
                total=Sum('total_price')
            )['total'] or 0,
            'active_products': Product.objects.filter(is_active=True).count(),
        }

        # Сохраняем в аналитическую базу
        service.save_daily_analytics(daily_stats)

        # Обновляем trending products
        update_trending_products.delay()

        logger.info(f"Daily analytics updated for {today}")

        return {
            'status': 'success',
            'date': today.isoformat(),
            'stats': daily_stats
        }

    except Exception as exc:
        logger.error(f"Error updating daily analytics: {exc}")
        raise


@shared_task(bind=True)
def update_trending_products(self):
    """
    Обновление трендовых товаров на основе бронирований
    """
    try:
        from apps.analytics.services import AnalyticsService
        from apps.reservations.models import Reservation, ReservationStatus

        service = AnalyticsService()

        # Анализируем последние 7 дней
        week_ago = timezone.now() - timedelta(days=7)

        trending_data = Reservation.objects.filter(
            created_at__gte=week_ago,
            status__in=[ReservationStatus.PENDING, ReservationStatus.CONFIRMED]
        ).values('product_id', 'product__name').annotate(
            reservation_count=Count('id'),
            total_quantity=Sum('quantity'),
            avg_price=Avg('price_per_item')
        ).order_by('-reservation_count')[:20]

        service.update_trending_products(list(trending_data))

        logger.info("Trending products updated")

        return {
            'status': 'success',
            'trending_count': len(trending_data)
        }

    except Exception as exc:
        logger.error(f"Error updating trending products: {exc}")
        raise


@shared_task(bind=True)
def track_conversion(self, reservation_id, event_type):
    """
    Отслеживание конверсий для аналитики
    """
    try:
        from apps.analytics.services import AnalyticsService

        service = AnalyticsService()
        service.track_conversion_event(reservation_id, event_type)

        logger.info(f"Conversion tracked: {event_type} for reservation {reservation_id}")

        return {
            'status': 'success',
            'reservation_id': reservation_id,
            'event_type': event_type
        }

    except Exception as exc:
        logger.error(f"Error tracking conversion: {exc}")
        raise