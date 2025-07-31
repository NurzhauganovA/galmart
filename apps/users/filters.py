from django.db.models import Q
from django_filters import rest_framework as filters
from django.contrib.auth import get_user_model

User = get_user_model()


class UserFilter(filters.FilterSet):
    """Фильтры для пользователей"""

    # Поиск по имени и email
    search = filters.CharFilter(method='filter_search')

    # Фильтр по статусу
    is_active = filters.BooleanFilter()
    is_verified = filters.BooleanFilter()
    is_staff = filters.BooleanFilter()

    # Фильтр по дате регистрации
    registered_after = filters.DateFilter(field_name='date_joined', lookup_expr='gte')
    registered_before = filters.DateFilter(field_name='date_joined', lookup_expr='lte')

    class Meta:
        model = User
        fields = [
            'search', 'is_active', 'is_verified', 'is_staff',
            'registered_after', 'registered_before'
        ]

    def filter_search(self, queryset, name, value):
        """Поиск по имени, фамилии и email"""
        return queryset.filter(
            Q(first_name__icontains=value) |
            Q(last_name__icontains=value) |
            Q(email__icontains=value) |
            Q(username__icontains=value)
        )