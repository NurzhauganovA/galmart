from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.reservations.views import (
    ReservationViewSet,
    ReservationStatsView,
    UserReservationHistoryView
)

app_name = 'reservations'

# Router для ViewSets
router = DefaultRouter()
router.register('', ReservationViewSet, basename='reservation')

urlpatterns = [
    # Статистика бронирований
    path('stats/', ReservationStatsView.as_view(), name='reservation-stats'),

    # История бронирований пользователя
    path('history/', UserReservationHistoryView.as_view(), name='reservation-history'),

    # CRUD операции и действия
    path('', include(router.urls)),
]