from django.conf import settings
from typing import Dict, Any
import json

from django.utils import timezone
from kafka import KafkaProducer
from apps.core.services.base import BaseService
from apps.reservations.models import Reservation


class NotificationService(BaseService):
    """Сервис для отправки уведомлений"""

    def __init__(self):
        super().__init__()
        self.producer = KafkaProducer(
            bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
            value_serializer=lambda v: json.dumps(v).encode('utf-8'),
            key_serializer=lambda k: str(k).encode('utf-8') if k else None,
        )

    def validate_data(self, data: Dict[str, Any]) -> bool:
        return 'event_type' in data and 'data' in data

    def _send_event(self, topic: str, event_type: str, data: Dict[str, Any], key: str = None):
        """Базовый метод отправки события в Kafka"""
        try:
            message = {
                'event_type': event_type,
                'data': data,
                'timestamp': timezone.now().isoformat()
            }

            self.producer.send(
                topic=topic,
                key=key,
                value=message
            )
            self.producer.flush()

            self.logger.info(f"Event sent to Kafka: {event_type}")

        except Exception as e:
            self.logger.error(f"Failed to send event to Kafka: {e}")

    def send_reservation_created(self, reservation: Reservation):
        """Уведомление о создании брони"""
        self._send_event(
            topic='reservation_events',
            event_type='reservation_created',
            data={
                'reservation_id': str(reservation.id),
                'user_id': reservation.user_id,
                'product_id': reservation.product_id,
                'quantity': reservation.quantity,
                'expires_at': reservation.expires_at.isoformat(),
            },
            key=str(reservation.user_id)
        )

    def send_reservation_confirmed(self, reservation: Reservation):
        """Уведомление о подтверждении брони"""
        self._send_event(
            topic='reservation_events',
            event_type='reservation_confirmed',
            data={
                'reservation_id': str(reservation.id),
                'user_id': reservation.user_id,
                'product_id': reservation.product_id,
                'total_price': float(reservation.total_price),
            },
            key=str(reservation.user_id)
        )

    def send_reservation_cancelled(self, reservation: Reservation):
        """Уведомление об отмене брони"""
        self._send_event(
            topic='reservation_events',
            event_type='reservation_cancelled',
            data={
                'reservation_id': str(reservation.id),
                'user_id': reservation.user_id,
                'product_id': reservation.product_id,
            },
            key=str(reservation.user_id)
        )