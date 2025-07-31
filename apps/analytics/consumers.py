from django.utils import timezone
from apps.analytics.models import RealtimeMetric, ConversionEvent
import logging

logger = logging.getLogger(__name__)


class AnalyticsEventConsumer:
    """Обработчик аналитических событий"""

    def process_event(self, event_data, key=None):
        """Основной метод обработки аналитических событий"""
        event_type = event_data.get('event_type')
        data = event_data.get('data', {})

        handler_map = {
            'page_view': self.handle_page_view,
            'product_view': self.handle_product_view,
            'search_query': self.handle_search_query,
            'user_action': self.handle_user_action,
            'system_metric': self.handle_system_metric,
        }

        handler = handler_map.get(event_type)
        if handler:
            try:
                handler(data, event_data.get('timestamp'))
                logger.debug(f"Processed analytics event: {event_type}")
            except Exception as e:
                logger.error(f"Error processing analytics event {event_type}: {e}")
                raise
        else:
            logger.warning(f"Unknown analytics event type: {event_type}")

    def handle_page_view(self, data, timestamp=None):
        """Обработка просмотров страниц"""
        try:
            from apps.analytics.services import AnalyticsService

            service = AnalyticsService()
            service.track_page_view(
                path=data.get('path'),
                user_id=data.get('user_id'),
                session_id=data.get('session_id'),
                timestamp=timestamp
            )

        except Exception as e:
            logger.error(f"Error tracking page view: {e}")

    def handle_product_view(self, data, timestamp=None):
        """Обработка просмотров товаров"""
        try:
            from apps.analytics.services import AnalyticsService

            service = AnalyticsService()
            service.track_product_view(
                product_id=data.get('product_id'),
                user_id=data.get('user_id'),
                session_id=data.get('session_id'),
                timestamp=timestamp
            )

        except Exception as e:
            logger.error(f"Error tracking product view: {e}")

    def handle_search_query(self, data, timestamp=None):
        """Обработка поисковых запросов"""
        try:
            from apps.analytics.services import AnalyticsService

            service = AnalyticsService()
            service.track_search_query(
                query=data.get('query'),
                results_count=data.get('results_count', 0),
                user_id=data.get('user_id'),
                timestamp=timestamp
            )

        except Exception as e:
            logger.error(f"Error tracking search query: {e}")

    def handle_user_action(self, data, timestamp=None):
        """Обработка действий пользователей"""
        try:
            # Обновляем метрики в реальном времени
            metric_name = data.get('action')
            if metric_name:
                RealtimeMetric.objects.create(
                    metric_name=metric_name,
                    value=data.get('value', 1),
                    timestamp=timezone.now(),
                    metadata=data.get('metadata', {})
                )

        except Exception as e:
            logger.error(f"Error tracking user action: {e}")

    def handle_system_metric(self, data, timestamp=None):
        """Обработка системных метрик"""
        try:
            RealtimeMetric.objects.create(
                metric_name=f"system.{data.get('metric_name')}",
                value=data.get('value'),
                timestamp=timezone.now(),
                metadata={
                    'host': data.get('host'),
                    'service': data.get('service'),
                    **data.get('metadata', {})
                }
            )

        except Exception as e:
            logger.error(f"Error tracking system metric: {e}")