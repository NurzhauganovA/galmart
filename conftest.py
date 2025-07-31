import pytest
from django.conf import settings
from django.test import override_settings
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model
from apps.products.models import Product, Category, ProductStock
from apps.reservations.models import Reservation
import factory
from decimal import Decimal

User = get_user_model()


@pytest.fixture(scope='session')
def django_db_setup():
    """Настройка тестовой базы данных"""
    settings.DATABASES['default'] = {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'galmart_test',
        'USER': 'postgres',
        'PASSWORD': '5693',
        'HOST': 'localhost',
        'PORT': '5432',
    }


@pytest.fixture
def api_client():
    """API клиент для тестов"""
    return APIClient()


@pytest.fixture
def user():
    """Создание тестового пользователя"""
    return User.objects.create_user(
        username='testuser',
        email='test@example.com',
        password='testpass123'
    )


@pytest.fixture
def authenticated_client(api_client, user):
    """Аутентифицированный API клиент"""
    api_client.force_authenticate(user=user)
    return api_client


@pytest.fixture
def category():
    """Создание тестовой категории"""
    return Category.objects.create(
        name='Test Category',
        slug='test-category'
    )


@pytest.fixture
def product(category):
    """Создание тестового товара"""
    product = Product.objects.create(
        name='Test Product',
        slug='test-product',
        description='Test description',
        category=category,
        price=Decimal('100.00'),
        sku='TEST-001'
    )

    # Создаем остатки
    ProductStock.objects.create(
        product=product,
        quantity=50,
        reserved_quantity=0
    )

    return product