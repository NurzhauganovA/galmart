from rest_framework.viewsets import ModelViewSet
from apps.core.pagination import StandardResultsSetPagination
from django.http import JsonResponse
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.core.cache import cache
from django.db import connection


class BaseViewSet(ModelViewSet):
    """Базовый ViewSet с общей функциональностью"""

    pagination_class = StandardResultsSetPagination

    def handle_exception(self, exc):
        """Обработка исключений"""
        if hasattr(exc, 'detail'):
            return Response(
                {'error': str(exc.detail), 'code': exc.__class__.__name__.lower()},
                status=exc.status_code if hasattr(exc, 'status_code') else status.HTTP_400_BAD_REQUEST
            )
        return super().handle_exception(exc)

    def get_cache_key(self, request):
        """Генерация ключа кэша на основе запроса"""
        return f"{self.__class__.__name__.lower()}:{request.path}:{request.GET.urlencode()}"


class HealthCheckView(APIView):
    """Проверка здоровья системы"""
    permission_classes = []

    def get(self, request):
        health_data = {
            'status': 'healthy',
            'services': {
                'database': self._check_database(),
                'cache': self._check_cache(),
                'celery': self._check_celery(),
            }
        }

        # Определяем общий статус
        all_healthy = all(
            service['status'] == 'ok'
            for service in health_data['services'].values()
        )

        if not all_healthy:
            health_data['status'] = 'degraded'
            return Response(health_data, status=status.HTTP_503_SERVICE_UNAVAILABLE)

        return Response(health_data)

    def _check_database(self):
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
            return {'status': 'ok'}
        except Exception as e:
            return {'status': 'error', 'error': str(e)}

    def _check_cache(self):
        try:
            cache.set('health_check', 'ok', 10)
            if cache.get('health_check') == 'ok':
                return {'status': 'ok'}
            else:
                return {'status': 'error', 'error': 'Cache read/write failed'}
        except Exception as e:
            return {'status': 'error', 'error': str(e)}

    def _check_celery(self):
        try:
            from celery import current_app
            inspect = current_app.control.inspect()
            active = inspect.active()
            if active:
                return {'status': 'ok', 'workers': len(active)}
            else:
                return {'status': 'warning', 'message': 'No active workers'}
        except Exception as e:
            return {'status': 'error', 'error': str(e)}


class SystemStatusView(APIView):
    """Расширенная информация о состоянии системы"""
    permission_classes = []

    def get(self, request):
        return Response({
            'system': self._get_system_info(),
            'database': self._get_database_info(),
            'cache': self._get_cache_info(),
            'application': self._get_app_info(),
        })

    def _get_system_info(self):
        try:
            import psutil
            return {
                'cpu_percent': psutil.cpu_percent(),
                'memory_percent': psutil.virtual_memory().percent,
                'disk_percent': psutil.disk_usage('/').percent,
            }
        except ImportError:
            return {'error': 'psutil not available'}

    def _get_database_info(self):
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT count(*) FROM django_session")
                sessions = cursor.fetchone()[0]
            return {
                'active_sessions': sessions,
                'connection_status': 'ok'
            }
        except Exception as e:
            return {'error': str(e)}

    def _get_cache_info(self):
        try:
            # Получаем статистику Redis
            import redis
            r = redis.from_url(cache._cache.get_connection_pool().connection_kwargs['host'])
            info = r.info()
            return {
                'connected_clients': info.get('connected_clients', 0),
                'used_memory_human': info.get('used_memory_human', 'N/A'),
                'keyspace_hits': info.get('keyspace_hits', 0),
                'keyspace_misses': info.get('keyspace_misses', 0),
            }
        except Exception as e:
            return {'error': str(e)}

    def _get_app_info(self):
        from django.conf import settings
        return {
            'debug': settings.DEBUG,
            'allowed_hosts': settings.ALLOWED_HOSTS,
            'timezone': settings.TIME_ZONE,
            'language_code': settings.LANGUAGE_CODE,
        }


# Error handlers
def bad_request(request, exception=None):
    """Обработчик ошибки 400"""
    return JsonResponse({
        'error': 'Неверный запрос',
        'code': 'bad_request',
        'status_code': 400
    }, status=400)


def permission_denied(request, exception=None):
    """Обработчик ошибки 403"""
    return JsonResponse({
        'error': 'Доступ запрещен',
        'code': 'permission_denied',
        'status_code': 403
    }, status=403)


def page_not_found(request, exception=None):
    """Обработчик ошибки 404"""
    return JsonResponse({
        'error': 'Страница не найдена',
        'code': 'not_found',
        'status_code': 404
    }, status=404)


def server_error(request):
    """Обработчик ошибки 500"""
    return JsonResponse({
        'error': 'Внутренняя ошибка сервера',
        'code': 'server_error',
        'status_code': 500
    }, status=500)