from celery import shared_task
from django.utils import timezone
from django.core.cache import cache
from apps.reservations.services import ReservationService
from apps.reservations.models import Reservation, ReservationStatus
import logging

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def cleanup_expired_reservations(self):
    """
    Периодическая задача для очистки просроченных бронирований
    """
    try:
        service = ReservationService()
        count = service.cleanup_expired_reservations()

        logger.info(f"Cleaned up {count} expired reservations")

        # Обновляем метрики в кеше
        cache.set('expired_reservations_cleaned', count, timeout=3600)

        return {
            'status': 'success',
            'cleaned_count': count,
            'timestamp': timezone.now().isoformat()
        }

    except Exception as exc:
        logger.error(f"Error cleaning expired reservations: {exc}")

        # Повторяем задачу с экспоненциальной задержкой
        countdown = 2 ** self.request.retries * 60  # 1, 2, 4 минуты
        raise self.retry(exc=exc, countdown=countdown)


@shared_task(bind=True)
def send_reservation_reminder(self, reservation_id):
    """
    Отправка напоминания о скором истечении бронирования
    """
    try:
        reservation = Reservation.objects.get(
            id=reservation_id,
            status=ReservationStatus.PENDING
        )

        # Проверяем, что бронь еще не истекла
        if not reservation.is_expired:
            from apps.notifications.services import NotificationService
            notification_service = NotificationService()

            # Отправляем напоминание
            notification_service.send_reservation_reminder(reservation)

            logger.info(f"Reminder sent for reservation {reservation_id}")
            return {'status': 'success', 'reservation_id': str(reservation_id)}
        else:
            logger.info(f"Reservation {reservation_id} already expired, skipping reminder")
            return {'status': 'skipped', 'reason': 'expired'}

    except Reservation.DoesNotExist:
        logger.warning(f"Reservation {reservation_id} not found for reminder")
        return {'status': 'error', 'reason': 'not_found'}
    except Exception as exc:
        logger.error(f"Error sending reminder for reservation {reservation_id}: {exc}")
        raise


@shared_task(bind=True, max_retries=5)
def process_reservation_confirmation(self, reservation_id, user_id):
    """
    Асинхронное подтверждение бронирования с дополнительной обработкой
    """
    try:
        service = ReservationService()
        reservation = service.confirm_reservation(reservation_id, user_id)

        # Дополнительная обработка после подтверждения
        from apps.analytics.tasks import track_conversion
        track_conversion.delay(reservation_id, 'reservation_confirmed')

        # Обновляем статистику в реальном времени
        from apps.analytics.services import AnalyticsService
        analytics = AnalyticsService()
        analytics.update_realtime_metrics('reservations_confirmed', 1)

        logger.info(f"Reservation {reservation_id} confirmed successfully")

        return {
            'status': 'success',
            'reservation_id': str(reservation_id),
            'total_price': float(reservation.total_price)
        }

    except Exception as exc:
        logger.error(f"Error confirming reservation {reservation_id}: {exc}")

        # Повторяем с увеличивающейся задержкой
        countdown = min(2 ** self.request.retries * 30, 300)  # макс 5 минут
        raise self.retry(exc=exc, countdown=countdown)