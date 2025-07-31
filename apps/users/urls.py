from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
    TokenVerifyView,
)
from apps.users.views import (
    UserViewSet,
    UserProfileView,
    UserRegistrationView,
    UserActivationView,
    PasswordChangeView,
    PasswordResetView,
    PasswordResetConfirmView
)

app_name = 'users'

# Router для ViewSets
router = DefaultRouter()
router.register('', UserViewSet, basename='user')

urlpatterns = [
    # Аутентификация JWT
    path('auth/login/', TokenObtainPairView.as_view(), name='token-obtain-pair'),
    path('auth/refresh/', TokenRefreshView.as_view(), name='token-refresh'),
    path('auth/verify/', TokenVerifyView.as_view(), name='token-verify'),

    # Регистрация и активация
    path('auth/register/', UserRegistrationView.as_view(), name='user-register'),
    path('auth/activate/<uidb64>/<token>/', UserActivationView.as_view(), name='user-activate'),

    # Смена пароля
    path('auth/password/change/', PasswordChangeView.as_view(), name='password-change'),
    path('auth/password/reset/', PasswordResetView.as_view(), name='password-reset'),
    path('auth/password/reset/confirm/<uidb64>/<token>/',
         PasswordResetConfirmView.as_view(), name='password-reset-confirm'),

    # Профиль пользователя
    path('profile/', UserProfileView.as_view(), name='user-profile'),

    # CRUD операции с пользователями
    path('', include(router.urls)),
]