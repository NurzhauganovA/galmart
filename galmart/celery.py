import os
from celery import Celery
from django.conf import settings

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'galmart.settings.production')

app = Celery('galmart')

app.config_from_object(settings, namespace='CELERY')

app.autodiscover_tasks()

app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='Asia/Almaty',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 минут
    task_soft_time_limit=25 * 60,  # 25 минут
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    worker_max_tasks_per_child=1000,
)

app.conf.beat_schedule = {
    'cleanup-expired-reservations': {
        'task': 'apps.reservations.tasks.cleanup_expired_reservations',
        'schedule': 60.0,  # каждую минуту
    },
    'update-analytics': {
        'task': 'apps.analytics.tasks.update_daily_analytics',
        'schedule': 3600.0,  # каждый час
    },
    'health-check': {
        'task': 'apps.core.tasks.health_check',
        'schedule': 300.0,  # каждые 5 минут
    },
}


@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')