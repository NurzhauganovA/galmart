from django.core.management.base import BaseCommand
from django.conf import settings
from kafka import KafkaConsumer
import json
import logging
from apps.notifications.consumers import ReservationEventConsumer
from apps.analytics.consumers import AnalyticsEventConsumer

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Start Kafka consumers for processing events'

    def add_arguments(self, parser):
        parser.add_argument(
            '--topics',
            type=str,
            default='reservation_events,analytics_events',
            help='Comma-separated list of topics to consume'
        )
        parser.add_argument(
            '--group-id',
            type=str,
            default=settings.KAFKA_CONSUMER_GROUP_ID,
            help='Kafka consumer group ID'
        )

    def handle(self, *args, **options):
        topics = options['topics'].split(',')
        group_id = options['group_id']

        self.stdout.write(
            self.style.SUCCESS(f'Starting Kafka consumer for topics: {", ".join(topics)}')
        )

        # Создаем потребителя
        consumer = KafkaConsumer(
            *topics,
            bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
            group_id=group_id,
            value_deserializer=lambda m: json.loads(m.decode('utf-8')),
            key_deserializer=lambda k: k.decode('utf-8') if k else None,
            auto_offset_reset='latest',
            enable_auto_commit=True,
            consumer_timeout_ms=1000,
        )

        # Создаем обработчики событий
        event_processors = {
            'reservation_events': ReservationEventConsumer(),
            'analytics_events': AnalyticsEventConsumer(),
        }

        try:
            for message in consumer:
                topic = message.topic
                event_data = message.value
                key = message.key

                logger.info(f"Received event from {topic}: {event_data.get('event_type')}")

                if topic in event_processors:
                    try:
                        event_processors[topic].process_event(event_data, key)
                    except Exception as e:
                        logger.error(f"Error processing event from {topic}: {e}")
                else:
                    logger.warning(f"No processor found for topic: {topic}")

        except KeyboardInterrupt:
            self.stdout.write(self.style.SUCCESS('Kafka consumer stopped'))
        finally:
            consumer.close()