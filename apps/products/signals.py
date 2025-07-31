from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.core.cache import cache
from apps.products.models import Product, ProductStock
import logging

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Product)
def product_post_save(sender, instance, created, **kwargs):
    """Обработка после сохранения товара"""
    try:
        if created:
            # Создаем запись об остатках для нового товара
            ProductStock.objects.get_or_create(
                product=instance,
                defaults={'quantity': 0, 'reserved_quantity': 0}
            )
            logger.info(f"Product created with stock: {instance.id}")

        # Очищаем кеш
        cache.delete(f"product_with_stock:{instance.id}")
        cache.delete("product_list")

        # Обновляем поисковый индекс (если используется)
        if hasattr(instance, 'update_search_index'):
            instance.update_search_index()

    except Exception as e:
        logger.error(f"Error in product_post_save signal: {e}")


@receiver(post_save, sender=ProductStock)
def product_stock_post_save(sender, instance, created, **kwargs):
    """Обработка после сохранения остатков товара"""
    try:
        # Очищаем кеш товара
        cache.delete(f"product_stock:{instance.product.id}")
        cache.delete(f"product_with_stock:{instance.product.id}")

        # Проверяем низкие остатки
        if instance.available_quantity <= 5:  # Порог низких остатков
            from apps.notifications.tasks import send_low_stock_alert
            send_low_stock_alert.delay(instance.product.id, instance.available_quantity)

        logger.debug(f"Product stock updated: {instance.product.id}, available: {instance.available_quantity}")

    except Exception as e:
        logger.error(f"Error in product_stock_post_save signal: {e}")