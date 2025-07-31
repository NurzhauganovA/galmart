from django.db import models
from django.utils import timezone


class ProductManager(models.Manager):
    """Менеджер для модели Product"""

    def active(self):
        """Активные товары"""
        return self.filter(is_active=True)

    def in_stock(self):
        """Товары в наличии"""
        return self.select_related('stock').filter(
            is_active=True,
            stock__quantity__gt=models.F('stock__reserved_quantity')
        )

    def by_category(self, category):
        """Товары по категории"""
        return self.filter(category=category, is_active=True)

    def search(self, query):
        """Поиск товаров"""
        return self.filter(
            models.Q(name__icontains=query) |
            models.Q(description__icontains=query) |
            models.Q(sku__icontains=query),
            is_active=True
        )

    def price_range(self, min_price=None, max_price=None):
        """Фильтр по диапазону цен"""
        queryset = self.all()
        if min_price is not None:
            queryset = queryset.filter(price__gte=min_price)
        if max_price is not None:
            queryset = queryset.filter(price__lte=max_price)
        return queryset


class CategoryManager(models.Manager):
    """Менеджер для модели Category"""

    def root_categories(self):
        """Корневые категории"""
        return self.filter(parent__isnull=True)

    def with_products(self):
        """Категории с товарами"""
        return self.filter(products__is_active=True).distinct()