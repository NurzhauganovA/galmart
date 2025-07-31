from rest_framework import serializers
from apps.products.models import Product, Category, ProductStock


class CategorySerializer(serializers.ModelSerializer):
    """Сериализатор категории"""

    children = serializers.SerializerMethodField()
    products_count = serializers.SerializerMethodField()
    parent_name = serializers.CharField(source='parent.name', read_only=True)

    class Meta:
        model = Category
        fields = [
            'id', 'name', 'slug', 'parent', 'parent_name',
            'children', 'products_count', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_children(self, obj):
        """Дочерние категории"""
        if hasattr(obj, 'prefetched_children'):
            children = obj.prefetched_children
        else:
            children = obj.children.all()

        return CategorySerializer(children, many=True, context=self.context).data

    def get_products_count(self, obj):
        """Количество товаров в категории"""
        return getattr(obj, 'products_count', obj.products.filter(is_active=True).count())


class ProductStockSerializer(serializers.ModelSerializer):
    """Сериализатор остатков товара"""

    available_quantity = serializers.ReadOnlyField()
    status = serializers.SerializerMethodField()

    class Meta:
        model = ProductStock
        fields = [
            'quantity', 'reserved_quantity', 'available_quantity',
            'last_updated', 'version', 'status'
        ]
        read_only_fields = ['last_updated', 'version', 'available_quantity']

    def get_status(self, obj):
        """Статус наличия товара"""
        if obj.available_quantity == 0:
            return 'out_of_stock'
        elif obj.available_quantity <= 5:
            return 'low_stock'
        else:
            return 'in_stock'


class ProductBriefSerializer(serializers.ModelSerializer):
    """Краткий сериализатор товара для списков"""

    category_name = serializers.CharField(source='category.name', read_only=True)
    category_slug = serializers.CharField(source='category.slug', read_only=True)
    stock_status = serializers.SerializerMethodField()
    available_quantity = serializers.SerializerMethodField()
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = [
            'id', 'name', 'slug', 'price', 'sku',
            'category_name', 'category_slug', 'stock_status',
            'available_quantity', 'image_url', 'is_active'
        ]

    def get_stock_status(self, obj):
        """Статус наличия"""
        if hasattr(obj, 'stock'):
            if obj.stock.available_quantity == 0:
                return 'out_of_stock'
            elif obj.stock.available_quantity <= 5:
                return 'low_stock'
            else:
                return 'in_stock'
        return 'unknown'

    def get_available_quantity(self, obj):
        """Доступное количество"""
        if hasattr(obj, 'stock'):
            return obj.stock.available_quantity
        return 0

    def get_image_url(self, obj):
        """URL изображения товара"""
        # Заглушка для изображения
        return f"https://via.placeholder.com/300x300.png?text={obj.name[:20]}"


class ProductDetailSerializer(serializers.ModelSerializer):
    """Подробный сериализатор товара"""

    category = CategorySerializer(read_only=True)
    stock = ProductStockSerializer(read_only=True)
    images = serializers.SerializerMethodField()
    reviews_stats = serializers.SerializerMethodField()
    related_products = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = [
            'id', 'name', 'slug', 'description', 'category',
            'price', 'sku', 'is_active', 'stock', 'images',
            'reviews_stats', 'related_products', 'meta_title',
            'meta_description', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_images(self, obj):
        """Изображения товара"""
        # Заглушка для изображений
        return [
            f"https://via.placeholder.com/800x600.png?text={obj.name[:20]}",
            f"https://via.placeholder.com/800x600.png?text={obj.name[:20]}-2",
        ]

    def get_reviews_stats(self, obj):
        """Статистика отзывов"""
        # Заглушка для отзывов
        return {
            'average_rating': 4.5,
            'total_reviews': 25,
            'rating_distribution': {
                '5': 15,
                '4': 7,
                '3': 2,
                '2': 1,
                '1': 0
            }
        }

    def get_related_products(self, obj):
        """Связанные товары"""
        related = Product.objects.filter(
            category=obj.category,
            is_active=True
        ).exclude(id=obj.id)[:4]

        return ProductBriefSerializer(related, many=True, context=self.context).data


class ProductCreateUpdateSerializer(serializers.ModelSerializer):
    """Сериализатор для создания/обновления товара"""

    initial_stock = serializers.IntegerField(write_only=True, required=False, default=0)

    class Meta:
        model = Product
        fields = [
            'name', 'slug', 'description', 'category', 'price',
            'sku', 'is_active', 'meta_title', 'meta_description',
            'initial_stock'
        ]

    def validate_sku(self, value):
        """Валидация уникальности SKU"""
        if self.instance:
            # При обновлении исключаем текущий объект
            if Product.objects.filter(sku=value).exclude(id=self.instance.id).exists():
                raise serializers.ValidationError('Товар с таким SKU уже существует')
        else:
            # При создании проверяем уникальность
            if Product.objects.filter(sku=value).exists():
                raise serializers.ValidationError('Товар с таким SKU уже существует')
        return value

    def create(self, validated_data):
        """Создание товара с остатками"""
        initial_stock = validated_data.pop('initial_stock', 0)
        product = super().create(validated_data)

        # Создаем или обновляем остатки
        ProductStock.objects.update_or_create(
            product=product,
            defaults={'quantity': initial_stock}
        )

        return product