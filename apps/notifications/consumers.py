from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.contrib.auth import get_user_model
from django.conf import settings
from apps.reservations.models import Reservation
from apps.notifications.tasks import send_email_notification, send_sms_notification
import logging


User = get_user_model()
logger = logging.getLogger(__name__)


class ReservationEventConsumer:
    """Обработчик событий бронирования"""

    def process_event(self, event_data, key=None):
        """Основной метод обработки событий"""
        event_type = event_data.get('event_type')
        data = event_data.get('data', {})

        handler_map = {
            'reservation_created': self.handle_reservation_created,
            'reservation_confirmed': self.handle_reservation_confirmed,
            'reservation_cancelled': self.handle_reservation_cancelled,
            'reservation_expired': self.handle_reservation_expired,
        }

        handler = handler_map.get(event_type)
        if handler:
            try:
                handler(data)
                logger.info(f"Successfully processed {event_type}")
            except Exception as e:
                logger.error(f"Error processing {event_type}: {e}")
                raise
        else:
            logger.warning(f"Unknown event type: {event_type}")

    def handle_reservation_created(self, data):
        """Обработка создания бронирования"""
        reservation_id = data.get('reservation_id')
        user_id = data.get('user_id')

        try:
            reservation = Reservation.objects.select_related('user', 'product').get(
                id=reservation_id
            )

            # Отправляем email подтверждение
            send_email_notification.delay(
                to_email=reservation.user.email,
                subject='Бронирование создано',
                template_name='emails/reservation_created.html',
                context={
                    'reservation': {
                        'id': str(reservation.id),
                        'product_name': reservation.product.name,
                        'quantity': reservation.quantity,
                        'total_price': float(reservation.total_price),
                        'expires_at': reservation.expires_at.strftime('%d.%m.%Y %H:%M'),
                    },
                    'user': reservation.user,
                }
            )

            # Планируем напоминание за 5 минут до истечения
            from apps.reservations.tasks import send_reservation_reminder
            from datetime import timedelta
            from django.utils import timezone

            reminder_time = reservation.expires_at - timedelta(minutes=5)
            if reminder_time > timezone.now():
                send_reservation_reminder.apply_async(
                    args=[str(reservation.id)],
                    eta=reminder_time
                )

        except Reservation.DoesNotExist:
            logger.error(f"Reservation {reservation_id} not found for created event")

    def handle_reservation_confirmed(self, data):
        """Обработка подтверждения бронирования"""
        reservation_id = data.get('reservation_id')

        try:
            reservation = Reservation.objects.select_related('user', 'product').get(
                id=reservation_id
            )

            # Отправляем подтверждение
            send_email_notification.delay(
                to_email=reservation.user.email,
                subject='Бронирование подтверждено',
                template_name='emails/reservation_confirmed.html',
                context={
                    'reservation': {
                        'id': str(reservation.id),
                        'product_name': reservation.product.name,
                        'quantity': reservation.quantity,
                        'total_price': float(reservation.total_price),
                    },
                    'user': reservation.user,
                }
            )

            # Если есть номер телефона, отправляем SMS
            if reservation.user.phone:
                message = (
                    f"Ваше бронирование #{str(reservation.id)[:8]} подтверждено. "
                    f"Товар: {reservation.product.name}, сумма: {reservation.total_price} тенге."
                )
                send_sms_notification.delay(reservation.user.phone, message)

        except Reservation.DoesNotExist:
            logger.error(f"Reservation {reservation_id} not found for confirmed event")

    def handle_reservation_cancelled(self, data):
        """Обработка отмены бронирования"""
        reservation_id = data.get('reservation_id')

        try:
            reservation = Reservation.objects.select_related('user', 'product').get(
                id=reservation_id
            )

            send_email_notification.delay(
                to_email=reservation.user.email,
                subject='Бронирование отменено',
                template_name='emails/reservation_cancelled.html',
                context={
                    'reservation': {
                        'id': str(reservation.id),
                        'product_name': reservation.product.name,
                        'quantity': reservation.quantity,
                    },
                    'user': reservation.user,
                }
            )

        except Reservation.DoesNotExist:
            logger.error(f"Reservation {reservation_id} not found for cancelled event")

    def handle_reservation_expired(self, data):
        """Обработка истечения бронирования"""
        reservation_id = data.get('reservation_id')

        try:
            reservation = Reservation.objects.select_related('user', 'product').get(
                id=reservation_id
            )

            send_email_notification.delay(
                to_email=reservation.user.email,
                subject='Бронирование истекло',
                template_name='emails/reservation_expired.html',
                context={
                    'reservation': {
                        'id': str(reservation.id),
                        'product_name': reservation.product.name,
                        'quantity': reservation.quantity,
                    },
                    'user': reservation.user,
                }
            )

        except Reservation.DoesNotExist:
            logger.error(f"Reservation {reservation_id} not found for expired event")