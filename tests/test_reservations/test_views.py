import pytest
from django.urls import reverse
from rest_framework import status
from apps.reservations.models import ReservationStatus
from tests.factories import UserFactory, ProductFactory, ProductStockFactory, ReservationFactory


@pytest.mark.django_db
class TestReservationViewSet:
    """Тесты для API бронирований"""

    def setup_method(self):
        self.user = UserFactory()
        self.product = ProductFactory()
        self.stock = ProductStockFactory(product=self.product, quantity=50)

    def test_create_reservation_success(self, authenticated_client):
        """Тест создания бронирования через API"""
        url = reverse('reservation-list')
        data = {
            'product_id': self.product.id,
            'quantity': 5,
            'customer_info': {'notes': 'Test reservation'}
        }

        response = authenticated_client.post(url, data, format='json')

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['product']['id'] == self.product.id
        assert response.data['quantity'] == 5
        assert response.data['status'] == ReservationStatus.PENDING

    def test_create_reservation_insufficient_stock(self, authenticated_client):
        """Тест создания бронирования при недостатке товара"""
        url = reverse('reservation-list')
        data = {
            'product_id': self.product.id,
            'quantity': 100,  # Больше, чем доступно
        }

        response = authenticated_client.post(url, data, format='json')

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data['code'] == 'insufficient_stock'

    def test_confirm_reservation_success(self, authenticated_client):
        """Тест подтверждения бронирования через API"""
        reservation = ReservationFactory(
            user=authenticated_client.handler._force_user,
            product=self.product,
            status=ReservationStatus.PENDING
        )

        url = reverse('reservation-confirm', kwargs={'pk': reservation.id})
        response = authenticated_client.post(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data['status'] == ReservationStatus.CONFIRMED

    def test_cancel_reservation_success(self, authenticated_client):
        """Тест отмены бронирования через API"""
        reservation = ReservationFactory(
            user=authenticated_client.handler._force_user,
            product=self.product,
            status=ReservationStatus.PENDING
        )

        url = reverse('reservation-cancel', kwargs={'pk': reservation.id})
        response = authenticated_client.post(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data['status'] == ReservationStatus.CANCELLED

    def test_my_reservations(self, authenticated_client):
        """Тест получения списка бронирований пользователя"""
        user = authenticated_client.handler._force_user
        reservations = ReservationFactory.create_batch(3, user=user)

        url = reverse('reservation-my-reservations')
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] == 3

    def test_unauthorized_access(self, api_client):
        """Тест неавторизованного доступа"""
        url = reverse('reservation-list')
        response = api_client.get(url)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED