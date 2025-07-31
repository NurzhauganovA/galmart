from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from django.core.cache import cache
import logging

User = get_user_model()
logger = logging.getLogger(__name__)


@receiver(post_save, sender=User)
def user_post_save(sender, instance, created, **kwargs):
    """Обработка после сохранения пользователя"""
    try:
        if created:
            # Новый пользователь зарегистрирован
            logger.info(f"New user registered: {instance.email}")

            # Отправляем welcome email
            from apps.notifications.tasks import send_welcome_email
            send_welcome_email.delay(instance.id)

            # Создаем профиль пользователя (если нужно)
            # UserProfile.objects.get_or_create(user=instance)

        # Очищаем кеш пользователя
        cache.delete(f"user_profile:{instance.id}")

    except Exception as e:
        logger.error(f"Error in user_post_save signal: {e}")