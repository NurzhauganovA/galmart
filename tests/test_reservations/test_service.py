import pytest
from django.utils import timezone
from django.test import TransactionTestCase
from decimal import Decimal
from unittest.mock import patch, Mock

from apps.reservations.services import ReservationService
from apps.reservations.models import Reservation, ReservationStatus
from apps.core.exceptions import BusinessLogicError, InsufficientStockError
from tests.factories import UserFactory, ProductFactory, ProductStockFactory


@pytest.mark.django_db
class TestReservationService:
    """Тесты для сервиса бронирований"""

    def setup_method(self):
        self.service = ReservationService()
        self.user = UserFactory()
        self.product = ProductFactory()
        self.stock = ProductStockFactory(product=self.product, quantity=50, reserved_quantity=0)

    def test_create_reservation_success(self):
        """Тест успешного создания бронирования"""
        reservation = self.service.create_reservation(
            user_id=self.user.id,
            product_id=self.product.id,
            quantity=5
        )

        assert reservation.user_id == self.user.id
        assert reservation.product_id == self.product.id
        assert reservation.quantity == 5
        assert reservation.status == ReservationStatus.PENDING
        assert reservation.total_price == self.product.price * 5

        # Проверяем, что товар зарезервирован
        self.stock.refresh_from_db()
        assert self.stock.reserved_quantity == 5

    def test_create_reservation_insufficient_stock(self):
        """Тест создания бронирования при недостатке товара"""
        with pytest.raises(InsufficientStockError):
            self.service.create_reservation(
                user_id=self.user.id,
                product_id=self.product.id,
                quantity=100  # Больше, чем доступно
            )

    def test_create_reservation_exceeds_user_limit(self):
        """Тест превышения лимита бронирований на пользователя"""
        # Создаем максимальное количество активных бронирований
        for _ in range(5):  # MAX_RESERVATION_PER_USER = 5
            ReservationFactory(user=self.user, status=ReservationStatus.PENDING)

        with pytest.raises(BusinessLogicError, match="Превышен лимит активных броней"):
            self.service.create_reservation(
                user_id=self.user.id,
                product_id=self.product.id,
                quantity=1
            )

    def test_confirm_reservation_success(self):
        """Тест успешного подтверждения бронирования"""
        reservation = self.service.create_reservation(
            user_id=self.user.id,
            product_id=self.product.id,
            quantity=5
        )

        confirmed_reservation = self.service.confirm_reservation(
            reservation_id=reservation.id,
            user_id=self.user.id
        )

        assert confirmed_reservation.status == ReservationStatus.CONFIRMED
        assert confirmed_reservation.confirmed_at is not None

        # Проверяем, что товар списан из остатков
        self.stock.refresh_from_db()
        assert self.stock.quantity == 45  # 50 - 5
        assert self.stock.reserved_quantity == 0

    def test_cancel_reservation_success(self):
        """Тест успешной отмены бронирования"""
        reservation = self.service.create_reservation(
            user_id=self.user.id,
            product_id=self.product.id,
            quantity=5
        )

        cancelled_reservation = self.service.cancel_reservation(
            reservation_id=reservation.id,
            user_id=self.user.id
        )

        assert cancelled_reservation.status == ReservationStatus.CANCELLED
        assert cancelled_reservation.cancelled_at is not None

        # Проверяем, что резерв освобожден
        self.stock.refresh_from_db()
        assert self.stock.reserved_quantity == 0

    @patch('apps.reservations.services.NotificationService')
    @patch('apps.reservations.services.AnalyticsService')
    def test_create_reservation_with_notifications(self, mock_analytics, mock_notifications):
        """Тест создания бронирования с уведомлениями"""
        mock_notification_service = Mock()
        mock_analytics_service = Mock()
        mock_notifications.return_value = mock_notification_service
        mock_analytics.return_value = mock_analytics_service

        reservation = self.service.create_reservation(
            user_id=self.user.id,
            product_id=self.product.id,
            quantity=5
        )

        # Проверяем, что сервисы были вызваны
        mock_notification_service.send_reservation_created.assert_called_once_with(reservation)
        mock_analytics_service.track_reservation_created.assert_called_once_with(reservation)