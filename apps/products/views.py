from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema, OpenApiParameter
from drf_spectacular.types import OpenApiTypes

from rest_framework import permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.views import BaseViewSet
from apps.products.models import Product, Category, ProductStock
from apps.products.serializers import (
    ProductDetailSerializer, ProductBriefSerializer,
    CategorySerializer, ProductStockSerializer
)
from apps.products.services import ProductService
from apps.products.filters import ProductFilter


class CategoryViewSet(BaseViewSet):
    """ViewSet для категорий"""

    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [permissions.AllowAny]
    lookup_field = 'slug'
    search_fields = ['name']
    ordering = ['name']


class ProductViewSet(BaseViewSet):
    """ViewSet для товаров"""

    queryset = Product.objects.select_related('category', 'stock').filter(is_active=True)
    permission_classes = [permissions.AllowAny]
    filter_backends = [DjangoFilterBackend]
    filterset_class = ProductFilter
    search_fields = ['name', 'description', 'sku']
    ordering_fields = ['name', 'price', 'created_at']
    ordering = ['-created_at']
    lookup_field = 'slug'

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.product_service = ProductService()

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return ProductDetailSerializer
        return ProductBriefSerializer

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name='q',
                type=OpenApiTypes.STR,
                description='Поисковый запрос'
            ),
            OpenApiParameter(
                name='category',
                type=OpenApiTypes.INT,
                description='ID категории'
            ),
            OpenApiParameter(
                name='min_price',
                type=OpenApiTypes.FLOAT,
                description='Минимальная цена'
            ),
            OpenApiParameter(
                name='max_price',
                type=OpenApiTypes.FLOAT,
                description='Максимальная цена'
            ),
            OpenApiParameter(
                name='in_stock_only',
                type=OpenApiTypes.BOOL,
                description='Только товары в наличии'
            ),
        ],
        description="Поиск товаров с фильтрацией"
    )
    @action(detail=False, methods=['get'])
    def search(self, request):
        """Расширенный поиск товаров"""
        query = request.query_params.get('q', '')
        category_id = request.query_params.get('category')
        min_price = request.query_params.get('min_price')
        max_price = request.query_params.get('max_price')
        in_stock_only = request.query_params.get('in_stock_only', 'true').lower() == 'true'

        # Преобразуем параметры
        if category_id:
            try:
                category_id = int(category_id)
            except ValueError:
                category_id = None

        if min_price:
            try:
                min_price = float(min_price)
            except ValueError:
                min_price = None

        if max_price:
            try:
                max_price = float(max_price)
            except ValueError:
                max_price = None

        # Выполняем поиск
        products = self.product_service.search_products(
            query=query,
            category_id=category_id,
            min_price=min_price,
            max_price=max_price,
            in_stock_only=in_stock_only
        )

        page = self.paginate_queryset(products)
        if page is not None:
            serializer = ProductBriefSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = ProductBriefSerializer(products, many=True)
        return Response(serializer.data)


class ProductSearchView(APIView):
    """Расширенный поиск товаров"""
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        query = request.query_params.get('q', '')
        category_id = request.query_params.get('category')
        min_price = request.query_params.get('min_price')
        max_price = request.query_params.get('max_price')
        in_stock_only = request.query_params.get('in_stock_only', 'true').lower() == 'true'
        sort_by = request.query_params.get('sort_by', 'relevance')

        service = ProductService()
        products = service.search_products(
            query=query,
            category_id=int(category_id) if category_id else None,
            min_price=float(min_price) if min_price else None,
            max_price=float(max_price) if max_price else None,
            in_stock_only=in_stock_only
        )

        # Сортировка
        if sort_by == 'price_asc':
            products = products.order_by('price')
        elif sort_by == 'price_desc':
            products = products.order_by('-price')
        elif sort_by == 'name':
            products = products.order_by('name')
        elif sort_by == 'newest':
            products = products.order_by('-created_at')

        # Пагинация
        from apps.core.pagination import StandardResultsSetPagination
        paginator = StandardResultsSetPagination()
        page = paginator.paginate_queryset(products, request)

        serializer = ProductBriefSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)


class ProductRecommendationsView(APIView):
    """Рекомендации товаров"""
    permission_classes = [permissions.AllowAny]

    def get(self, request, product_id):
        try:
            product = Product.objects.get(id=product_id)
        except Product.DoesNotExist:
            return Response(
                {'error': 'Товар не найден'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Простой алгоритм рекомендаций на основе категории
        recommendations = Product.objects.filter(
            category=product.category,
            is_active=True
        ).exclude(id=product_id).order_by('?')[:6]

        serializer = ProductBriefSerializer(recommendations, many=True)
        return Response(serializer.data)


class ProductStockViewSet(BaseViewSet):
    """Управление остатками товаров"""
    queryset = ProductStock.objects.select_related('product')
    serializer_class = ProductStockSerializer
    permission_classes = [permissions.IsAdminUser]

    @action(detail=True, methods=['post'])
    def update_stock(self, request, pk=None):
        """Обновление остатков товара"""
        stock = self.get_object()
        new_quantity = request.data.get('quantity')

        if new_quantity is None:
            return Response(
                {'error': 'Количество обязательно'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            new_quantity = int(new_quantity)
            if new_quantity < 0:
                raise ValueError("Количество не может быть отрицательным")
        except (ValueError, TypeError):
            return Response(
                {'error': 'Неверное количество'},
                status=status.HTTP_400_BAD_REQUEST
            )

        stock.quantity = new_quantity
        stock.save()

        serializer = self.get_serializer(stock)
        return Response(serializer.data)