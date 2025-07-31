from rest_framework import permissions
from rest_framework.permissions import BasePermission


class IsOwnerOrReadOnly(BasePermission):
    """
    Разрешение только владельцу объекта для записи.
    Для остальных - только чтение.
    """

    def has_object_permission(self, request, view, obj):
        # Read permissions для любого запроса
        if request.method in permissions.SAFE_METHODS:
            return True

        # Write permissions только для владельца объекта
        return obj.user == request.user


class IsOwner(BasePermission):
    """Разрешение только владельцу объекта"""

    def has_object_permission(self, request, view, obj):
        return obj.user == request.user


class IsAdminOrReadOnly(BasePermission):
    """Разрешение админу для записи, остальным - только чтение"""

    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user and request.user.is_staff


class IsVerifiedUser(BasePermission):
    """Разрешение только верифицированным пользователям"""

    def has_permission(self, request, view):
        return (
                request.user and
                request.user.is_authenticated and
                getattr(request.user, 'is_verified', True)
        )


class CanCreateReservation(BasePermission):
    """Разрешение на создание бронирования"""

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        # Проверяем лимиты пользователя
        if view.action == 'create':
            from apps.reservations.models import Reservation, ReservationStatus
            active_count = Reservation.objects.filter(
                user=request.user,
                status=ReservationStatus.PENDING
            ).count()

            return active_count < 5  # MAX_RESERVATION_PER_USER

        return True