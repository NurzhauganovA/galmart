from celery import shared_task
from django.core.cache import cache
from django.db import connection
from django.utils import timezone
import psutil
import logging

logger = logging.getLogger(__name__)


@shared_task(bind=True)
def health_check(self):
    """
    Проверка здоровья системы
    """
    try:
        health_data = {
            'timestamp': timezone.now().isoformat(),
            'database': check_database_health(),
            'cache': check_cache_health(),
            'system': check_system_health(),
        }

        # Сохраняем результаты в кеш
        cache.set('system_health', health_data, timeout=600)  # 10 минут

        # Определяем общий статус
        overall_status = 'healthy'
        if not all([
            health_data['database']['status'] == 'ok',
            health_data['cache']['status'] == 'ok',
            health_data['system']['cpu_percent'] < 80,
            health_data['system']['memory_percent'] < 80
        ]):
            overall_status = 'warning'

        health_data['overall_status'] = overall_status

        logger.info(f"Health check completed: {overall_status}")

        return health_data

    except Exception as exc:
        logger.error(f"Health check failed: {exc}")
        return {
            'timestamp': timezone.now().isoformat(),
            'overall_status': 'error',
            'error': str(exc)
        }


def check_database_health():
    """Проверка здоровья базы данных"""
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()

        return {
            'status': 'ok',
            'response_time_ms': 0  # Можно измерить время ответа
        }
    except Exception as e:
        return {
            'status': 'error',
            'error': str(e)
        }


def check_cache_health():
    """Проверка здоровья кеша"""
    try:
        test_key = 'health_check_test'
        test_value = 'ok'

        cache.set(test_key, test_value, timeout=60)
        retrieved_value = cache.get(test_key)
        cache.delete(test_key)

        if retrieved_value == test_value:
            return {'status': 'ok'}
        else:
            return {'status': 'error', 'error': 'Cache value mismatch'}

    except Exception as e:
        return {
            'status': 'error',
            'error': str(e)
        }


def check_system_health():
    """Проверка системных ресурсов"""
    try:
        return {
            'cpu_percent': psutil.cpu_percent(interval=1),
            'memory_percent': psutil.virtual_memory().percent,
            'disk_percent': psutil.disk_usage('/').percent,
            'load_average': psutil.getloadavg()[0] if hasattr(psutil, 'getloadavg') else 0
        }
    except Exception as e:
        return {
            'error': str(e)
        }