import pytest
from django.utils import timezone
from apps.analytics.services import AnalyticsService
from apps.analytics.models import RealtimeMetric, ConversionEvent
from tests.factories import ReservationFactory
from datetime import timedelta


@pytest.mark.django_db
class TestAnalyticsService:
    """Тесты для сервиса аналитики"""

    def setup_method(self):
        self.service = AnalyticsService()

    def test_track_reservation_created(self):
        """Тест отслеживания создания бронирования"""
        reservation = ReservationFactory()

        with patch('apps.analytics.services.RealtimeMetric.objects') as mock_metric:
            self.service.track_reservation_created(reservation)

            # Проверяем, что события записываются
            assert ConversionEvent.objects.filter(
                event_type='reservation_created',
                reservation_id=reservation.id
            ).exists()

    def test_get_realtime_metrics(self):
        """Тест получения метрик в реальном времени"""
        # Создаем тестовые метрики
        RealtimeMetric.objects.create(
            metric_name='test_metric',
            value=10,
            timestamp=timezone.now()
        )
        RealtimeMetric.objects.create(
            metric_name='test_metric',
            value=5,
            timestamp=timezone.now()
        )

        metrics = self.service.get_realtime_metrics(['test_metric'], hours=1)

        assert metrics['test_metric'] == 15

    def test_get_conversion_funnel(self):
        """Тест получения воронки конверсии"""
        reservation = ReservationFactory()

        # Создаем события конверсии
        ConversionEvent.objects.create(
            event_type='reservation_created',
            reservation_id=reservation.id,
            user_id=reservation.user_id
        )
        ConversionEvent.objects.create(
            event_type='reservation_confirmed',
            reservation_id=reservation.id,
            user_id=reservation.user_id
        )

        funnel = self.service.get_conversion_funnel(days=7)

        assert funnel['reservation_created'] == 1
        assert funnel['reservation_confirmed'] == 1