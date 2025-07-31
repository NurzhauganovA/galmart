from django.db import models
from django.core.validators import MinValueValidator
from django.utils.translation import gettext_lazy as _
from decimal import Decimal


class Category(models.Model):
    """Категория товаров"""
    name = models.CharField(_('name'), max_length=100)
    slug = models.SlugField(_('slug'), unique=True)
    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='children'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'categories'
        verbose_name_plural = 'Categories'
        indexes = [
            models.Index(fields=['slug']),
            models.Index(fields=['parent']),
        ]


class Product(models.Model):
    """Модель товара"""
    name = models.CharField(_('name'), max_length=200)
    slug = models.SlugField(_('slug'), unique=True)
    description = models.TextField(_('description'), blank=True)
    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        related_name='products'
    )
    price = models.DecimalField(
        _('price'),
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    sku = models.CharField(_('SKU'), max_length=50, unique=True)
    is_active = models.BooleanField(_('is active'), default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Метаданные для SEO
    meta_title = models.CharField(max_length=200, blank=True)
    meta_description = models.TextField(max_length=300, blank=True)

    class Meta:
        db_table = 'products'
        indexes = [
            models.Index(fields=['slug']),
            models.Index(fields=['sku']),
            models.Index(fields=['category']),
            models.Index(fields=['is_active']),
            models.Index(fields=['created_at']),
            models.Index(fields=['-created_at']),  # Для сортировки по убыванию
        ]

    def __str__(self):
        return self.name


class ProductStock(models.Model):
    """Модель остатков товара"""
    product = models.OneToOneField(
        Product,
        on_delete=models.CASCADE,
        related_name='stock'
    )
    quantity = models.PositiveIntegerField(_('quantity'), default=0)
    reserved_quantity = models.PositiveIntegerField(_('reserved quantity'), default=0)
    last_updated = models.DateTimeField(auto_now=True)
    version = models.PositiveIntegerField(default=1)  # Для оптимистичной блокировки

    class Meta:
        db_table = 'product_stocks'
        indexes = [
            models.Index(fields=['product']),
            models.Index(fields=['last_updated']),
        ]

    @property
    def available_quantity(self):
        return max(0, self.quantity - self.reserved_quantity)

    def can_reserve(self, quantity):
        return self.available_quantity >= quantity