import django_filters
from django_filters import rest_framework as filters
from django.utils import timezone
from datetime import timedelta
from apps.reservations.models import Reservation, ReservationStatus


class ReservationFilter(filters.FilterSet):
    """Фильтры для бронирований"""

    # Фильтр по статусу
    status = filters.ChoiceFilter(choices=ReservationStatus.choices)

    # Фильтр по продукту
    product = filters.NumberFilter(field_name='product__id')
    product_name = filters.CharFilter(
        field_name='product__name',
        lookup_expr='icontains'
    )

    # Фильтр по диапазону дат
    created_after = filters.DateTimeFilter(
        field_name='created_at',
        lookup_expr='gte'
    )
    created_before = filters.DateTimeFilter(
        field_name='created_at',
        lookup_expr='lte'
    )

    # Фильтр по диапазону цен
    min_price = filters.NumberFilter(
        field_name='total_price',
        lookup_expr='gte'
    )
    max_price = filters.NumberFilter(
        field_name='total_price',
        lookup_expr='lte'
    )

    # Фильтр по количеству
    min_quantity = filters.NumberFilter(
        field_name='quantity',
        lookup_expr='gte'
    )
    max_quantity = filters.NumberFilter(
        field_name='quantity',
        lookup_expr='lte'
    )

    # Специальные фильтры
    is_expired = filters.BooleanFilter(method='filter_expired')
    expires_soon = filters.NumberFilter(method='filter_expires_soon')

    class Meta:
        model = Reservation
        fields = [
            'status', 'product', 'product_name',
            'created_after', 'created_before',
            'min_price', 'max_price',
            'min_quantity', 'max_quantity',
            'is_expired', 'expires_soon'
        ]

    def filter_expired(self, queryset, name, value):
        """Фильтр просроченных бронирований"""
        if value:
            return queryset.filter(
                expires_at__lt=timezone.now(),
                status=ReservationStatus.PENDING
            )
        else:
            return queryset.filter(
                expires_at__gte=timezone.now()
            )

    def filter_expires_soon(self, queryset, name, value):
        """Фильтр бронирований, истекающих в ближайшие N минут"""
        if value:
            expires_threshold = timezone.now() + timedelta(minutes=value)
            return queryset.filter(
                expires_at__lte=expires_threshold,
                expires_at__gte=timezone.now(),
                status=ReservationStatus.PENDING
            )
        return queryset