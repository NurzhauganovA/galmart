from django.core.cache import cache
from django.db.models import Q, F
from typing import List, Optional, Dict, Any
from apps.core.services.base import BaseService
from apps.products.models import Product, ProductStock, Category


class ProductService(BaseService):
    """Сервис для работы с товарами"""

    def validate_data(self, data: Dict[str, Any]) -> bool:
        required_fields = ['name', 'price', 'sku']
        return all(field in data for field in required_fields)

    def get_product_with_stock(self, product_id: int) -> Optional[Product]:
        """Получение товара с информацией об остатках"""
        cache_key = f"product_with_stock:{product_id}"
        product = cache.get(cache_key)

        if not product:
            try:
                product = Product.objects.select_related('stock', 'category').get(
                    id=product_id,
                    is_active=True
                )
                cache.set(cache_key, product, timeout=300)  # 5 минут
            except Product.DoesNotExist:
                return None

        return product

    def search_products(self, query: str, category_id: Optional[int] = None,
                        min_price: Optional[float] = None, max_price: Optional[float] = None,
                        in_stock_only: bool = True) -> List[Product]:
        """Поиск товаров с фильтрацией"""
        queryset = Product.objects.select_related('category', 'stock').filter(
            is_active=True
        )

        # Поиск по названию и описанию
        if query:
            queryset = queryset.filter(
                Q(name__icontains=query) |
                Q(description__icontains=query) |
                Q(sku__icontains=query)
            )

        # Фильтр по категории
        if category_id:
            queryset = queryset.filter(category_id=category_id)

        # Фильтр по цене
        if min_price is not None:
            queryset = queryset.filter(price__gte=min_price)
        if max_price is not None:
            queryset = queryset.filter(price__lte=max_price)

        # Только товары в наличии
        if in_stock_only:
            queryset = queryset.filter(
                stock__quantity__gt=F('stock__reserved_quantity')
            )

        return queryset.order_by('-created_at')

    def update_stock(self, product_id: int, quantity: int) -> ProductStock:
        """Обновление остатков товара"""
        try:
            stock = ProductStock.objects.select_for_update().get(product_id=product_id)
            stock.quantity = quantity
            stock.version += 1
            stock.save(update_fields=['quantity', 'version', 'last_updated'])

            # Очищаем кеш
            cache.delete(f"product_stock:{product_id}")
            cache.delete(f"product_with_stock:{product_id}")

            return stock
        except ProductStock.DoesNotExist:
            raise BusinessLogicError("Информация об остатках не найдена")