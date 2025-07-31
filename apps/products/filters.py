from django_filters import rest_framework as filters
from django.db.models import Q, F
from apps.products.models import Product, Category


class ProductFilter(filters.FilterSet):
    """Фильтры для товаров"""

    # Поиск по названию и описанию
    search = filters.CharFilter(method='filter_search')

    # Фильтр по категории
    category = filters.ModelChoiceFilter(queryset=Category.objects.all())
    category_slug = filters.CharFilter(field_name='category__slug')

    # Фильтр по цене
    min_price = filters.NumberFilter(field_name='price', lookup_expr='gte')
    max_price = filters.NumberFilter(field_name='price', lookup_expr='lte')
    price_range = filters.RangeFilter(field_name='price')

    # Фильтр по наличию
    in_stock = filters.BooleanFilter(method='filter_in_stock')
    min_stock = filters.NumberFilter(method='filter_min_stock')

    # Фильтр по активности
    is_active = filters.BooleanFilter()

    # Фильтр по дате создания
    created_after = filters.DateFilter(field_name='created_at', lookup_expr='gte')
    created_before = filters.DateFilter(field_name='created_at', lookup_expr='lte')

    class Meta:
        model = Product
        fields = [
            'search', 'category', 'category_slug',
            'min_price', 'max_price', 'price_range',
            'in_stock', 'min_stock', 'is_active',
            'created_after', 'created_before'
        ]

    def filter_search(self, queryset, name, value):
        """Поиск по названию, описанию и SKU"""
        return queryset.filter(
            Q(name__icontains=value) |
            Q(description__icontains=value) |
            Q(sku__icontains=value)
        )

    def filter_in_stock(self, queryset, name, value):
        """Фильтр товаров в наличии"""
        if value:
            return queryset.filter(
                stock__quantity__gt=F('stock__reserved_quantity')
            )
        else:
            return queryset.filter(
                stock__quantity__lte=F('stock__reserved_quantity')
            )

    def filter_min_stock(self, queryset, name, value):
        """Фильтр по минимальному остатку"""
        return queryset.filter(
            stock__quantity__gte=value + F('stock__reserved_quantity')
        )