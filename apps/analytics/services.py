from django.db import models
from django.utils import timezone
from django.core.cache import cache
from django.conf import settings
from typing import Dict, Any, List, Optional
from datetime import timedelta, date
import json
import logging

from apps.core.services.base import BaseService
from apps.analytics.models import RealtimeMetric, ConversionEvent, DailyAnalytics

logger = logging.getLogger(__name__)


class AnalyticsService(BaseService):
    """Сервис для работы с аналитикой"""

    def validate_data(self, data: Dict[str, Any]) -> bool:
        return True  # Аналитика принимает любые данные

    def track_reservation_created(self, reservation):
        """Отслеживание создания бронирования"""
        self._create_conversion_event(
            event_type='reservation_created',
            reservation_id=reservation.id,
            user_id=reservation.user_id,
            metadata={
                'product_id': reservation.product_id,
                'quantity': reservation.quantity,
                'total_price': float(reservation.total_price),
            }
        )

        # Обновляем метрики в реальном времени
        self.update_realtime_metrics('reservations_created', 1)

    def track_reservation_confirmed(self, reservation):
        """Отслеживание подтверждения бронирования"""
        self._create_conversion_event(
            event_type='reservation_confirmed',
            reservation_id=reservation.id,
            user_id=reservation.user_id,
            metadata={
                'product_id': reservation.product_id,
                'total_price': float(reservation.total_price),
            }
        )

        # Обновляем метрики
        self.update_realtime_metrics('reservations_confirmed', 1)
        self.update_realtime_metrics('revenue', float(reservation.total_price))

    def track_reservation_cancelled(self, reservation):
        """Отслеживание отмены бронирования"""
        self._create_conversion_event(
            event_type='reservation_cancelled',
            reservation_id=reservation.id,
            user_id=reservation.user_id,
            metadata={
                'product_id': reservation.product_id,
                'reason': 'user_cancelled',
            }
        )

        self.update_realtime_metrics('reservations_cancelled', 1)

    def track_page_view(self, path: str, user_id: Optional[int] = None,
                        session_id: Optional[str] = None, timestamp: Optional[str] = None):
        """Отслеживание просмотров страниц"""
        RealtimeMetric.objects.using('analytics').create(
            metric_name='page_view',
            value=1,
            timestamp=timezone.now(),
            metadata={
                'path': path,
                'user_id': user_id,
                'session_id': session_id,
            }
        )

    def track_product_view(self, product_id: int, user_id: Optional[int] = None,
                           session_id: Optional[str] = None, timestamp: Optional[str] = None):
        """Отслеживание просмотров товаров"""
        RealtimeMetric.objects.using('analytics').create(
            metric_name='product_view',
            value=1,
            timestamp=timezone.now(),
            metadata={
                'product_id': product_id,
                'user_id': user_id,
                'session_id': session_id,
            }
        )

    def track_search_query(self, query: str, results_count: int = 0,
                           user_id: Optional[int] = None, timestamp: Optional[str] = None):
        """Отслеживание поисковых запросов"""
        RealtimeMetric.objects.using('analytics').create(
            metric_name='search_query',
            value=1,
            timestamp=timezone.now(),
            metadata={
                'query': query,
                'results_count': results_count,
                'user_id': user_id,
            }
        )

    def update_realtime_metrics(self, metric_name: str, value: float):
        """Обновление метрик в реальном времени"""
        RealtimeMetric.objects.using('analytics').create(
            metric_name=metric_name,
            value=value,
            timestamp=timezone.now()
        )

        # Также обновляем кеш для быстрого доступа
        cache_key = f"realtime_metric:{metric_name}"
        current_value = cache.get(cache_key, 0)
        cache.set(cache_key, current_value + value, timeout=3600)

    def get_realtime_metrics(self, metric_names: List[str],
                             hours: int = 1) -> Dict[str, float]:
        """Получение метрик в реальном времени"""
        since = timezone.now() - timedelta(hours=hours)

        metrics = RealtimeMetric.objects.using('analytics').filter(
            metric_name__in=metric_names,
            timestamp__gte=since
        ).values('metric_name').annotate(
            total_value=models.Sum('value')
        )

        result = {}
        for metric in metrics:
            result[metric['metric_name']] = metric['total_value'] or 0

        return result

    def save_daily_analytics(self, stats: Dict[str, Any]):
        """Сохранение ежедневной аналитики"""
        date_value = stats['date']

        analytics, created = DailyAnalytics.objects.using('analytics').get_or_create(
            date=date_value,
            defaults=stats
        )

        if not created:
            # Обновляем существующую запись
            for key, value in stats.items():
                if key != 'date':
                    setattr(analytics, key, value)
            analytics.save(using='analytics')

        return analytics

    def get_daily_analytics(self, start_date: date, end_date: date) -> List[DailyAnalytics]:
        """Получение ежедневной аналитики за период"""
        return list(
            DailyAnalytics.objects.using('analytics').filter(
                date__range=[start_date, end_date]
            ).order_by('date')
        )

    def update_trending_products(self, trending_data: List[Dict[str, Any]]):
        """Обновление информации о трендовых товарах"""
        cache.set(
            'trending_products',
            trending_data,
            timeout=3600  # 1 hour
        )

    def get_trending_products(self) -> List[Dict[str, Any]]:
        """Получение трендовых товаров"""
        return cache.get('trending_products', [])

    def track_conversion_event(self, reservation_id: str, event_type: str):
        """Отслеживание событий конверсии"""
        try:
            from apps.reservations.models import Reservation
            reservation = Reservation.objects.get(id=reservation_id)

            ConversionEvent.objects.using('analytics').create(
                event_type=event_type,
                reservation_id=reservation_id,
                user_id=reservation.user_id,
                metadata={
                    'product_id': reservation.product_id,
                    'total_price': float(reservation.total_price),
                }
            )

        except Exception as e:
            logger.error(f"Error tracking conversion event: {e}")

    def get_conversion_funnel(self, days: int = 7) -> Dict[str, int]:
        """Получение воронки конверсии"""
        since = timezone.now() - timedelta(days=days)

        conversions = ConversionEvent.objects.using('analytics').filter(
            timestamp__gte=since
        ).values('event_type').annotate(
            count=models.Count('id')
        )

        result = {}
        for conversion in conversions:
            result[conversion['event_type']] = conversion['count']

        return result

    def _create_conversion_event(self, event_type: str, reservation_id: str,
                                 user_id: int, metadata: Dict[str, Any]):
        """Создание события конверсии"""
        ConversionEvent.objects.using('analytics').create(
            event_type=event_type,
            reservation_id=reservation_id,
            user_id=user_id,
            metadata=metadata
        )