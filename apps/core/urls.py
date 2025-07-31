from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.core.views import HealthCheckView, SystemStatusView

app_name = 'core'

urlpatterns = [
    path('health/', HealthCheckView.as_view(), name='health-check'),
    path('status/', SystemStatusView.as_view(), name='system-status'),
]