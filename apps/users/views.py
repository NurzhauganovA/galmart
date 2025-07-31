from rest_framework import status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet
from rest_framework.generics import CreateAPIView, RetrieveUpdateAPIView
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_decode
from django.utils.encoding import force_str
from drf_spectacular.utils import extend_schema

from apps.core.views import BaseViewSet
from apps.users.serializers import (
    UserSerializer, UserRegistrationSerializer, UserProfileSerializer,
    PasswordChangeSerializer, PasswordResetSerializer
)
from apps.users.filters import UserFilter

User = get_user_model()


class UserViewSet(BaseViewSet):
    """ViewSet для управления пользователями"""
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_class = UserFilter
    search_fields = ['email', 'first_name', 'last_name']
    ordering_fields = ['date_joined', 'email']
    ordering = ['-date_joined']

    def get_permissions(self):
        """Разные права для разных действий"""
        if self.action == 'create':
            return [permissions.AllowAny()]
        elif self.action in ['update', 'partial_update', 'destroy']:
            return [permissions.IsAuthenticated()]
        return super().get_permissions()

    def get_queryset(self):
        """Пользователи видят только свой профиль, админы - всех"""
        if self.request.user.is_staff:
            return User.objects.all()
        return User.objects.filter(id=self.request.user.id)

    @extend_schema(description="Деактивировать аккаунт пользователя")
    @action(detail=True, methods=['post'])
    def deactivate(self, request, pk=None):
        """Деактивация пользователя"""
        user = self.get_object()
        user.is_active = False
        user.save()
        return Response({'status': 'User deactivated'})

    @extend_schema(description="Получить статистику пользователя")
    @action(detail=True, methods=['get'])
    def stats(self, request, pk=None):
        """Статистика пользователя"""
        user = self.get_object()
        from apps.reservations.models import Reservation

        stats = {
            'total_reservations': user.reservations.count(),
            'active_reservations': user.reservations.filter(
                status='pending'
            ).count(),
            'confirmed_reservations': user.reservations.filter(
                status='confirmed'
            ).count(),
        }
        return Response(stats)


class UserRegistrationView(CreateAPIView):
    """Регистрация пользователя"""
    serializer_class = UserRegistrationSerializer
    permission_classes = [permissions.AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        # Отправляем email для активации
        from apps.notifications.tasks import send_activation_email
        send_activation_email.delay(user.id)

        return Response({
            'message': 'Пользователь создан. Проверьте email для активации.',
            'user_id': user.id
        }, status=status.HTTP_201_CREATED)


class UserActivationView(APIView):
    """Активация аккаунта пользователя"""
    permission_classes = [permissions.AllowAny]

    def get(self, request, uidb64, token):
        try:
            uid = force_str(urlsafe_base64_decode(uidb64))
            user = User.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            user = None

        if user and default_token_generator.check_token(user, token):
            user.is_active = True
            user.is_verified = True
            user.save()
            return Response({'message': 'Аккаунт успешно активирован'})

        return Response(
            {'error': 'Неверная ссылка активации'},
            status=status.HTTP_400_BAD_REQUEST
        )


class UserProfileView(RetrieveUpdateAPIView):
    """Профиль текущего пользователя"""
    serializer_class = UserProfileSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user


class PasswordChangeView(APIView):
    """Смена пароля"""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = PasswordChangeSerializer(
            data=request.data,
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)

        user = request.user
        user.set_password(serializer.validated_data['new_password'])
        user.save()

        return Response({'message': 'Пароль успешно изменен'})


class PasswordResetView(APIView):
    """Сброс пароля"""
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = PasswordResetSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data['email']
        try:
            user = User.objects.get(email=email)
            # Отправляем email для сброса пароля
            from apps.notifications.tasks import send_password_reset_email
            send_password_reset_email.delay(user.id)
        except User.DoesNotExist:
            # Не раскрываем информацию о существовании пользователя
            pass

        return Response({
            'message': 'Если аккаунт существует, инструкции отправлены на email'
        })


class PasswordResetConfirmView(APIView):
    """Подтверждение сброса пароля"""
    permission_classes = [permissions.AllowAny]

    def post(self, request, uidb64, token):
        try:
            uid = force_str(urlsafe_base64_decode(uidb64))
            user = User.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            return Response(
                {'error': 'Неверная ссылка сброса пароля'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not default_token_generator.check_token(user, token):
            return Response(
                {'error': 'Неверный или истекший токен'},
                status=status.HTTP_400_BAD_REQUEST
            )

        new_password = request.data.get('new_password')
        if not new_password:
            return Response(
                {'error': 'Новый пароль обязателен'},
                status=status.HTTP_400_BAD_REQUEST
            )

        user.set_password(new_password)
        user.save()

        return Response({'message': 'Пароль успешно изменен'})