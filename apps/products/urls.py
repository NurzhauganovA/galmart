from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.products.views import (
    ProductViewSet,
    CategoryViewSet,
    ProductStockViewSet,
    ProductSearchView,
    ProductRecommendationsView
)

app_name = 'products'

# Router для ViewSets
router = DefaultRouter()
router.register('categories', CategoryViewSet, basename='category')
router.register('stock', ProductStockViewSet, basename='product-stock')
router.register('', ProductViewSet, basename='product')

urlpatterns = [
    # Поиск товаров
    path('search/', ProductSearchView.as_view(), name='product-search'),

    # Рекомендации
    path('<int:product_id>/recommendations/',
         ProductRecommendationsView.as_view(), name='product-recommendations'),

    # CRUD операции
    path('', include(router.urls)),
]