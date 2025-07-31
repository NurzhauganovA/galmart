import pytest
from unittest.mock import patch, Mock
from apps.reservations.tasks import cleanup_expired_reservations
from apps.reservations.models import ReservationStatus
from tests.factories import ReservationFactory
from django.utils import timezone
from datetime import timedelta


@pytest.mark.django_db
class TestCeleryTasks:
    """Тесты для Celery задач"""

    def test_cleanup_expired_reservations(self):
        """Тест очистки просроченных бронирований"""
        # Создаем просроченное бронирование
        expired_reservation = ReservationFactory(
            status=ReservationStatus.PENDING,
            expires_at=timezone.now() - timedelta(minutes=30)
        )

        # Создаем активное бронирование
        active_reservation = ReservationFactory(
            status=ReservationStatus.PENDING,
            expires_at=timezone.now() + timedelta(minutes=30)
        )

        with patch('apps.reservations.tasks.ReservationService') as mock_service:
            mock_service_instance = Mock()
            mock_service_instance.cleanup_expired_reservations.return_value = 1
            mock_service.return_value = mock_service_instance

            result = cleanup_expired_reservations()

            assert result['status'] == 'success'
            assert result['cleaned_count'] == 1
            mock_service_instance.cleanup_expired_reservations.assert_called_once()