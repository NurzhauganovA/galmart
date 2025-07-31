from celery import shared_task
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def send_email_notification(self, to_email, subject, template_name, context):
    """
    Отправка email уведомлений
    """
    try:
        html_message = render_to_string(template_name, context)

        send_mail(
            subject=subject,
            message='',  # Текстовая версия (пустая, используем HTML)
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[to_email],
            html_message=html_message,
            fail_silently=False
        )

        logger.info(f"Email sent to {to_email}: {subject}")

        return {
            'status': 'success',
            'to_email': to_email,
            'subject': subject
        }

    except Exception as exc:
        logger.error(f"Error sending email to {to_email}: {exc}")

        # Повторяем с задержкой
        countdown = 2 ** self.request.retries * 60
        raise self.retry(exc=exc, countdown=countdown)


@shared_task(bind=True)
def send_sms_notification(self, phone_number, message):
    """
    Отправка SMS уведомлений (заглушка для интеграции с SMS сервисом)
    """
    try:
        # Здесь должна быть интеграция с SMS сервисом
        # Например, Twilio, SMS.ru и т.д.

        logger.info(f"SMS would be sent to {phone_number}: {message}")

        return {
            'status': 'success',
            'phone_number': phone_number,
            'message': message
        }

    except Exception as exc:
        logger.error(f"Error sending SMS to {phone_number}: {exc}")
        raise
