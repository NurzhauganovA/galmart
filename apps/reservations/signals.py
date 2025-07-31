from django.db.models.signals import post_save, pre_save, post_delete
from django.dispatch import receiver
from django.utils import timezone
from django.core.cache import cache
from apps.reservations.models import Reservation, ReservationStatus
from apps.products.models import ProductStock
from apps.notifications.services import NotificationService
from apps.analytics.services import AnalyticsService
import logging

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Reservation)
def reservation_post_save(sender, instance, created, **kwargs):
    """Обработка после сохранения бронирования"""
    try:
        notification_service = NotificationService()
        analytics_service = AnalyticsService()

        if created:
            # Новое бронирование создано
            logger.info(f"Reservation created: {instance.id}")

            # Отправляем событие в Kafka
            notification_service.send_reservation_created(instance)

            # Планируем напоминание за 5 минут до истечения
            from apps.reservations.tasks import send_reservation_reminder
            from datetime import timedelta

            reminder_time = instance.expires_at - timedelta(minutes=5)
            if reminder_time > timezone.now():
                send_reservation_reminder.apply_async(
                    args=[str(instance.id)],
                    eta=reminder_time
                )

        else:
            # Бронирование обновлено
            # Проверяем изменение статуса
            if hasattr(instance, '_original_status'):
                if instance._original_status != instance.status:
                    if instance.status == ReservationStatus.CONFIRMED:
                        notification_service.send_reservation_confirmed(instance)
                        analytics_service.track_reservation_confirmed(instance)

                    elif instance.status in [ReservationStatus.CANCELLED, ReservationStatus.EXPIRED]:
                        notification_service.send_reservation_cancelled(instance)
                        analytics_service.track_reservation_cancelled(instance)

        # Обновляем кеш статистики
        cache.delete('reservation_stats')
        cache.delete(f'user_reservations:{instance.user_id}')

    except Exception as e:
        logger.error(f"Error in reservation_post_save signal: {e}")


@receiver(pre_save, sender=Reservation)
def reservation_pre_save(sender, instance, **kwargs):
    """Обработка перед сохранением бронирования"""
    try:
        # Сохраняем оригинальный статус для отслеживания изменений
        if instance.pk:
            try:
                original = Reservation.objects.get(pk=instance.pk)
                instance._original_status = original.status
            except Reservation.DoesNotExist:
                instance._original_status = None

        # Валидация бизнес-правил
        if instance.status == ReservationStatus.CONFIRMED:
            if instance.expires_at and timezone.now() > instance.expires_at:
                logger.warning(f"Attempting to confirm expired reservation: {instance.id}")
                instance.status = ReservationStatus.EXPIRED

    except Exception as e:
        logger.error(f"Error in reservation_pre_save signal: {e}")


@receiver(post_delete, sender=Reservation)
def reservation_post_delete(sender, instance, **kwargs):
    """Обработка после удаления бронирования"""
    try:
        # Освобождаем зарезервированный товар
        if instance.status == ReservationStatus.PENDING:
            stock = ProductStock.objects.select_for_update().get(
                product=instance.product
            )
            stock.reserved_quantity = max(0, stock.reserved_quantity - instance.quantity)
            stock.save(update_fields=['reserved_quantity', 'last_updated'])

            # Очищаем кеш
            cache.delete(f"product_stock:{instance.product.id}")

        # Очищаем связанный кеш
        cache.delete('reservation_stats')
        cache.delete(f'user_reservations:{instance.user_id}')

        logger.info(f"Reservation deleted: {instance.id}")

    except Exception as e:
        logger.error(f"Error in reservation_post_delete signal: {e}")