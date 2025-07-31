import pytest
from django.core.cache import cache
from apps.products.services import ProductService
from tests.factories import ProductFactory, CategoryFactory, ProductStockFactory


@pytest.mark.django_db
class TestProductService:
    """Тесты для сервиса товаров"""

    def setup_method(self):
        self.service = ProductService()
        cache.clear()  # Очищаем кеш перед каждым тестом

    def test_get_product_with_stock_cached(self):
        """Тест получения товара с кешированием"""
        product = ProductFactory()
        stock = ProductStockFactory(product=product)

        # Первый запрос - из БД
        result1 = self.service.get_product_with_stock(product.id)
        assert result1.id == product.id

        # Второй запрос - из кеша
        result2 = self.service.get_product_with_stock(product.id)
        assert result2.id == product.id

        # Проверяем, что товар кешируется
        cache_key = f"product_with_stock:{product.id}"
        assert cache.get(cache_key) is not None

    def test_search_products_by_name(self):
        """Тест поиска товаров по названию"""
        category = CategoryFactory()
        product1 = ProductFactory(name='iPhone 15', category=category)
        product2 = ProductFactory(name='Samsung Galaxy', category=category)
        ProductStockFactory(product=product1, quantity=10)
        ProductStockFactory(product=product2, quantity=5)

        results = self.service.search_products(query='iPhone')

        assert len(results) == 1
        assert results[0].id == product1.id

    def test_search_products_with_filters(self):
        """Тест поиска товаров с фильтрами"""
        category = CategoryFactory()
        expensive_product = ProductFactory(price=500, category=category)
        cheap_product = ProductFactory(price=50, category=category)
        ProductStockFactory(product=expensive_product, quantity=10)
        ProductStockFactory(product=cheap_product, quantity=5)

        # Поиск товаров дороже 100
        results = self.service.search_products(
            query='',
            min_price=100,
            category_id=category.id
        )

        assert len(results) == 1
        assert results[0].id == expensive_product.id

    def test_update_stock(self):
        """Тест обновления остатков товара"""
        product = ProductFactory()
        stock = ProductStockFactory(product=product, quantity=50)

        updated_stock = self.service.update_stock(product.id, 100)

        assert updated_stock.quantity == 100
        assert updated_stock.version == stock.version + 1