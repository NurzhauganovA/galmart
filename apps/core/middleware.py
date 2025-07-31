import time
import logging
import uuid

from django.conf import settings
from django.utils.deprecation import MiddlewareMixin
from django.http import JsonResponse
from django.db import connection
from django.core.cache import cache
from apps.core.routers import DatabaseRouter

logger = logging.getLogger(__name__)


class RequestLoggingMiddleware(MiddlewareMixin):
    """Middleware для логирования запросов"""

    def process_request(self, request):
        """Начинаем отслеживание запроса"""
        request.start_time = time.time()
        request.request_id = str(uuid.uuid4())[:8]

        logger.info(
            f"Request started: {request.method} {request.path}",
            extra={
                'request_id': request.request_id,
                'method': request.method,
                'path': request.path,
                'user_agent': request.META.get('HTTP_USER_AGENT', ''),
                'ip': self.get_client_ip(request),
            }
        )

    def process_response(self, request, response):
        """Завершаем отслеживание запроса"""
        if hasattr(request, 'start_time'):
            duration = time.time() - request.start_time

            logger.info(
                f"Request completed: {request.method} {request.path} - {response.status_code}",
                extra={
                    'request_id': getattr(request, 'request_id', 'unknown'),
                    'method': request.method,
                    'path': request.path,
                    'status_code': response.status_code,
                    'duration': duration,
                    'db_queries': len(connection.queries) if settings.DEBUG else None,
                }
            )

        return response

    def get_client_ip(self, request):
        """Получает IP адрес клиента"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class DatabaseRoutingMiddleware(MiddlewareMixin):
    """Middleware для оптимизации роутинга базы данных"""

    def process_request(self, request):
        """Устанавливаем hints для роутинга БД"""
        # Определяем, если это запрос к аналитике
        if request.path.startswith('/api/analytics/'):
            request.db_routing_hint = 'analytics'
        else:
            request.db_routing_hint = 'default'


class RateLimitMiddleware(MiddlewareMixin):
    """Middleware для ограничения частоты запросов"""

    def process_request(self, request):
        """Проверяем лимиты запросов"""
        if not self.should_rate_limit(request):
            return None

        client_ip = self.get_client_ip(request)
        cache_key = f"rate_limit:{client_ip}"

        # Получаем текущий счетчик запросов
        current_requests = cache.get(cache_key, 0)

        # Проверяем лимит (например, 1000 запросов в час)
        rate_limit = 1000
        if current_requests >= rate_limit:
            return JsonResponse(
                {
                    'error': 'Rate limit exceeded',
                    'detail': f'Maximum {rate_limit} requests per hour allowed'
                },
                status=429
            )

        # Увеличиваем счетчик
        cache.set(cache_key, current_requests + 1, timeout=3600)  # 1 hour

        return None

    def should_rate_limit(self, request):
        """Определяет, нужно ли применять rate limiting"""
        # Не применяем к статическим файлам и health checks
        excluded_paths = ['/static/', '/media/', '/health/', '/metrics/']
        return not any(request.path.startswith(path) for path in excluded_paths)

    def get_client_ip(self, request):
        """Получает IP адрес клиента"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class HealthCheckMiddleware(MiddlewareMixin):
    """Middleware для проверки здоровья системы"""

    def process_request(self, request):
        """Проверяем health check запросы"""
        if request.path == '/health/':
            return self.health_check_response()
        return None

    def health_check_response(self):
        """Возвращает статус здоровья системы"""
        try:
            # Проверяем базу данных
            from django.db import connection
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")

            # Проверяем кеш
            cache.set('health_check', 'ok', timeout=60)
            if cache.get('health_check') != 'ok':
                raise Exception("Cache not working")

            # Проверяем Celery (опционально)
            from celery import current_app
            inspect = current_app.control.inspect()
            active_nodes = inspect.active()

            return JsonResponse({
                'status': 'healthy',
                'timestamp': time.time(),
                'services': {
                    'database': 'ok',
                    'cache': 'ok',
                    'celery': 'ok' if active_nodes else 'warning',
                }
            })

        except Exception as e:
            logger.error(f"Health check failed: {e}")

            return JsonResponse({
                'status': 'unhealthy',
                'timestamp': time.time(),
                'error': str(e)
            }, status=503)