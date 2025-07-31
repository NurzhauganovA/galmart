from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler
import logging

logger = logging.getLogger(__name__)


class BaseBusinessException(Exception):
    """Базовое исключение для бизнес-логики"""
    default_message = "Произошла ошибка в бизнес-логике"
    default_code = "business_error"

    def __init__(self, message=None, code=None):
        self.message = message or self.default_message
        self.code = code or self.default_code
        super().__init__(self.message)


class BusinessLogicError(BaseBusinessException):
    """Общая ошибка бизнес-логики"""
    default_message = "Ошибка выполнения операции"
    default_code = "business_logic_error"


class InsufficientStockError(BaseBusinessException):
    """Недостаток товара"""
    default_message = "Недостаточно товара на складе"
    default_code = "insufficient_stock"


class ReservationExpiredError(BaseBusinessException):
    """Бронирование истекло"""
    default_message = "Время бронирования истекло"
    default_code = "reservation_expired"


class ReservationLimitExceededError(BaseBusinessException):
    """Превышен лимит бронирований"""
    default_message = "Превышен лимит активных бронирований"
    default_code = "reservation_limit_exceeded"


class ProductNotFoundError(BaseBusinessException):
    """Товар не найден"""
    default_message = "Товар не найден или недоступен"
    default_code = "product_not_found"


class UserNotFoundError(BaseBusinessException):
    """Пользователь не найден"""
    default_message = "Пользователь не найден"
    default_code = "user_not_found"


class ValidationError(BaseBusinessException):
    """Ошибка валидации"""
    default_message = "Ошибка валидации данных"
    default_code = "validation_error"


class AuthenticationError(BaseBusinessException):
    """Ошибка аутентификации"""
    default_message = "Ошибка аутентификации"
    default_code = "authentication_error"


class PermissionDeniedError(BaseBusinessException):
    """Доступ запрещен"""
    default_message = "Недостаточно прав доступа"
    default_code = "permission_denied"


def custom_exception_handler(exc, context):
    """Кастомный обработчик исключений"""
    # Получаем стандартный ответ
    response = exception_handler(exc, context)

    # Если это наше бизнес исключение
    if isinstance(exc, BaseBusinessException):
        return Response(
            {
                'error': exc.message,
                'code': exc.code,
                'timestamp': context['request'].META.get('HTTP_X_REQUEST_ID', ''),
            },
            status=status.HTTP_400_BAD_REQUEST
        )

    # Если стандартный обработчик вернул ответ
    if response is not None:
        custom_response_data = {
            'error': 'Произошла ошибка при обработке запроса',
            'code': 'api_error',
            'details': response.data,
            'status_code': response.status_code
        }

        # Логируем ошибку
        logger.error(
            f"API Error: {exc}",
            extra={
                'status_code': response.status_code,
                'path': context['request'].path,
                'method': context['request'].method,
                'user': context['request'].user.id if hasattr(context['request'], 'user') else None
            }
        )

        response.data = custom_response_data

    return response