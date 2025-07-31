from rest_framework import permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import ReadOnlyModelViewSet
from rest_framework.views import APIView
from django.db.models import Count, Sum, Avg
from django.utils import timezone
from datetime import timedelta
from django.core.cache import cache

from apps.core.views import BaseViewSet
from apps.analytics.models import RealtimeMetric, ConversionEvent, DailyAnalytics
from apps.analytics.serializers import (
    RealtimeMetricSerializer, ConversionEventSerializer, DailyAnalyticsSerializer
)
from apps.analytics.services import AnalyticsService


class AnalyticsViewSet(ReadOnlyModelViewSet):
    """ViewSet для аналитических данных"""
    queryset = RealtimeMetric.objects.all()
    serializer_class = RealtimeMetricSerializer
    permission_classes = [permissions.IsAdminUser]

    @action(detail=False, methods=['get'])
    def summary(self, request):
        """Сводка по метrikам"""
        metrics = ['reservations_created', 'reservations_confirmed', 'revenue']

        summary_data = {}
        for metric in metrics:
            last_hour = RealtimeMetric.objects.filter(
                metric_name=metric,
                timestamp__gte=timezone.now() - timedelta(hours=1)
            ).aggregate(total=Sum('value'))

            summary_data[metric] = last_hour['total'] or 0

        return Response(summary_data)


class DashboardView(APIView):
    """Главный дашборд с основными метриками"""
    permission_classes = [permissions.IsAdminUser]

    def get(self, request):
        # Проверяем кеш
        cache_key = 'analytics_dashboard'
        cached_data = cache.get(cache_key)
        if cached_data:
            return Response(cached_data)

        service = AnalyticsService()

        # Основные метрики за последние 24 часа
        metrics_24h = service.get_realtime_metrics([
            'reservations_created',
            'reservations_confirmed',
            'reservations_cancelled',
            'revenue'
        ], hours=24)

        # Конверсия
        funnel_data = service.get_conversion_funnel(days=7)

        # Трендовые товары
        trending = service.get_trending_products()

        # Статистика по дням за последнюю неделю
        week_ago = timezone.now().date() - timedelta(days=7)
        daily_stats = service.get_daily_analytics(week_ago, timezone.now().date())

        dashboard_data = {
            'metrics_24h': metrics_24h,
            'conversion_funnel': funnel_data,
            'trending_products': trending[:10],
            'daily_stats': [
                {
                    'date': stat.date.isoformat(),
                    'reservations_created': stat.reservations_created,
                    'reservations_confirmed': stat.reservations_confirmed,
                    'revenue': float(stat.total_revenue),
                }
                for stat in daily_stats
            ],
            'summary': {
                'total_revenue_24h': metrics_24h.get('revenue', 0),
                'conversion_rate': self._calculate_conversion_rate(funnel_data),
                'active_products': trending.__len__() if trending else 0,
            }
        }

        # Кешируем на 5 минут
        cache.set(cache_key, dashboard_data, timeout=300)

        return Response(dashboard_data)

    def _calculate_conversion_rate(self, funnel_data):
        """Расчет коэффициента конверсии"""
        created = funnel_data.get('reservation_created', 0)
        confirmed = funnel_data.get('reservation_confirmed', 0)

        if created == 0:
            return 0

        return round((confirmed / created) * 100, 2)


class RealtimeMetricsView(APIView):
    """Метрики в реальном времени"""
    permission_classes = [permissions.IsAdminUser]

    def get(self, request):
        hours = int(request.query_params.get('hours', 1))
        metric_names = request.query_params.getlist('metrics', [
            'reservations_created', 'reservations_confirmed', 'revenue'
        ])

        service = AnalyticsService()
        metrics = service.get_realtime_metrics(metric_names, hours=hours)

        # Получаем временные ряды
        time_series = {}
        for metric_name in metric_names:
            time_series[metric_name] = list(
                RealtimeMetric.objects.filter(
                    metric_name=metric_name,
                    timestamp__gte=timezone.now() - timedelta(hours=hours)
                ).values('timestamp', 'value').order_by('timestamp')
            )

        return Response({
            'totals': metrics,
            'time_series': time_series,
            'period': f'{hours}h',
            'updated_at': timezone.now().isoformat()
        })


class ConversionFunnelView(APIView):
    """Воронка конверсии"""
    permission_classes = [permissions.IsAdminUser]

    def get(self, request):
        days = int(request.query_params.get('days', 7))

        service = AnalyticsService()
        funnel_data = service.get_conversion_funnel(days=days)

        # Расчет коэффициентов конверсии
        steps = [
            'reservation_created',
            'reservation_confirmed'
        ]

        funnel_with_rates = []
        previous_count = None

        for step in steps:
            count = funnel_data.get(step, 0)
            rate = None

            if previous_count is not None and previous_count > 0:
                rate = round((count / previous_count) * 100, 2)

            funnel_with_rates.append({
                'step': step,
                'count': count,
                'conversion_rate': rate
            })

            previous_count = count

        return Response({
            'funnel': funnel_with_rates,
            'period_days': days,
            'overall_conversion_rate': self._calculate_overall_conversion(funnel_data)
        })

    def _calculate_overall_conversion(self, funnel_data):
        """Общий коэффициент конверсии"""
        created = funnel_data.get('reservation_created', 0)
        confirmed = funnel_data.get('reservation_confirmed', 0)

        if created == 0:
            return 0

        return round((confirmed / created) * 100, 2)


class TrendingProductsView(APIView):
    """Трендовые товары"""
    permission_classes = [permissions.IsAdminUser]

    def get(self, request):
        service = AnalyticsService()
        trending = service.get_trending_products()

        return Response({
            'trending_products': trending,
            'count': len(trending),
            'updated_at': timezone.now().isoformat()
        })


class RevenueAnalyticsView(APIView):
    """Аналитика выручки"""
    permission_classes = [permissions.IsAdminUser]

    def get(self, request):
        period = request.query_params.get('period', 'week')  # week, month, year

        if period == 'week':
            start_date = timezone.now().date() - timedelta(days=7)
        elif period == 'month':
            start_date = timezone.now().date() - timedelta(days=30)
        elif period == 'year':
            start_date = timezone.now().date() - timedelta(days=365)
        else:
            start_date = timezone.now().date() - timedelta(days=7)

        end_date = timezone.now().date()

        service = AnalyticsService()
        daily_stats = service.get_daily_analytics(start_date, end_date)

        # Агрегированная статистика
        total_revenue = sum(float(stat.total_revenue) for stat in daily_stats)
        total_orders = sum(stat.reservations_confirmed for stat in daily_stats)
        avg_order_value = total_revenue / total_orders if total_orders > 0 else 0

        # Данные по дням
        daily_data = [
            {
                'date': stat.date.isoformat(),
                'revenue': float(stat.total_revenue),
                'orders': stat.reservations_confirmed,
                'avg_order_value': float(
                    stat.total_revenue) / stat.reservations_confirmed if stat.reservations_confirmed > 0 else 0
            }
            for stat in daily_stats
        ]

        return Response({
            'summary': {
                'total_revenue': total_revenue,
                'total_orders': total_orders,
                'avg_order_value': round(avg_order_value, 2),
                'period': period,
                'days': len(daily_stats)
            },
            'daily_data': daily_data
        })