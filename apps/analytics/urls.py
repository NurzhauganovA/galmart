from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.analytics.views import (
    AnalyticsViewSet,
    DashboardView,
    RealtimeMetricsView,
    ConversionFunnelView,
    TrendingProductsView,
    RevenueAnalyticsView
)

app_name = 'analytics'

# Router для ViewSets
router = DefaultRouter()
router.register('metrics', AnalyticsViewSet, basename='analytics')

urlpatterns = [
    # Дашборд с основными метриками
    path('dashboard/', DashboardView.as_view(), name='analytics-dashboard'),

    # Метрики в реальном времени
    path('realtime/', RealtimeMetricsView.as_view(), name='realtime-metrics'),

    # Воронка конверсии
    path('funnel/', ConversionFunnelView.as_view(), name='conversion-funnel'),

    # Трендовые товары
    path('trending/', TrendingProductsView.as_view(), name='trending-products'),

    # Аналитика выручки
    path('revenue/', RevenueAnalyticsView.as_view(), name='revenue-analytics'),

    # ViewSets
    path('', include(router.urls)),
]