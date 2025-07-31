from datetime import timedelta

from django.db import transaction, models
from django.utils import timezone
from django.core.cache import cache
from django.conf import settings
from decimal import Decimal
from typing import Dict, Any, Optional, List
import uuid

from apps.core.services.base import BaseService
from apps.core.exceptions import BusinessLogicError, InsufficientStockError
from apps.products.models import Product, ProductStock
from apps.reservations.models import Reservation, ReservationStatus
from apps.notifications.services import NotificationService
from apps.analytics.services import AnalyticsService


class ReservationService(BaseService):
    """Сервис для работы с бронированиями"""

    def __init__(self):
        super().__init__()
        self.notification_service = NotificationService()
        self.analytics_service = AnalyticsService()

    def validate_data(self, data: Dict[str, Any]) -> bool:
        """Валидация данных для создания брони"""
        required_fields = ['user_id', 'product_id', 'quantity']
        return all(field in data for field in required_fields)

    @transaction.atomic
    def create_reservation(self, user_id: int, product_id: int, quantity: int,
                           customer_info: Optional[Dict] = None) -> Reservation:
        """
        Создание бронирования с проверкой остатков
        """
        try:
            # Получаем продукт с блокировкой для обновления
            product = Product.objects.select_for_update().get(
                id=product_id,
                is_active=True
            )

            # Получаем остатки с оптимистичной блокировкой
            stock = ProductStock.objects.select_for_update().get(product=product)

            # Проверяем возможность резервирования
            if not stock.can_reserve(quantity):
                raise InsufficientStockError(
                    f"Недостаточно товара. Доступно: {stock.available_quantity}, запрошено: {quantity}"
                )

            # Проверяем лимиты пользователя
            active_reservations_count = Reservation.objects.filter(
                user_id=user_id,
                status=ReservationStatus.PENDING
            ).count()

            if active_reservations_count >= settings.MAX_RESERVATION_PER_USER:
                raise BusinessLogicError(
                    f"Превышен лимит активных броней: {settings.MAX_RESERVATION_PER_USER}"
                )

            # Создаем бронирование
            reservation = Reservation.objects.create(
                user_id=user_id,
                product=product,
                quantity=quantity,
                price_per_item=product.price,
                customer_info=customer_info or {},
                expires_at=timezone.now() + timedelta(
                    minutes=settings.RESERVATION_TIMEOUT_MINUTES
                )
            )

            # Резервируем товар
            stock.reserved_quantity += quantity
            stock.version += 1
            stock.save(update_fields=['reserved_quantity', 'version', 'last_updated'])

            # Очищаем кеш продукта
            cache.delete(f"product_stock:{product_id}")

            # Отправляем уведомление
            self.notification_service.send_reservation_created(reservation)

            # Записываем в аналитику
            self.analytics_service.track_reservation_created(reservation)

            self.logger.info(f"Reservation created: {reservation.id}")
            return reservation

        except Product.DoesNotExist:
            raise BusinessLogicError("Товар не найден или неактивен")
        except ProductStock.DoesNotExist:
            raise BusinessLogicError("Информация об остатках товара не найдена")

    @transaction.atomic
    def confirm_reservation(self, reservation_id: uuid.UUID, user_id: int) -> Reservation:
        """Подтверждение бронирования"""
        try:
            reservation = Reservation.objects.select_for_update().get(
                id=reservation_id,
                user_id=user_id,
                status=ReservationStatus.PENDING
            )

            if reservation.is_expired:
                # Автоматически отменяем просроченную бронь
                return self.cancel_reservation(reservation_id, user_id, auto_cancel=True)

            # Подтверждаем бронь
            reservation.status = ReservationStatus.CONFIRMED
            reservation.confirmed_at = timezone.now()
            reservation.save(update_fields=['status', 'confirmed_at', 'updated_at'])

            # Уменьшаем общий остаток и резерв
            stock = ProductStock.objects.select_for_update().get(
                product=reservation.product
            )
            stock.quantity -= reservation.quantity
            stock.reserved_quantity -= reservation.quantity
            stock.version += 1
            stock.save(update_fields=['quantity', 'reserved_quantity', 'version', 'last_updated'])

            # Очищаем кеш
            cache.delete(f"product_stock:{reservation.product.id}")

            # Отправляем уведомления
            self.notification_service.send_reservation_confirmed(reservation)

            # Аналитика
            self.analytics_service.track_reservation_confirmed(reservation)

            self.logger.info(f"Reservation confirmed: {reservation.id}")
            return reservation

        except Reservation.DoesNotExist:
            raise BusinessLogicError("Бронирование не найдено")

    @transaction.atomic
    def cancel_reservation(self, reservation_id: uuid.UUID, user_id: int,
                           auto_cancel: bool = False) -> Reservation:
        """Отмена бронирования"""
        try:
            reservation = Reservation.objects.select_for_update().get(
                id=reservation_id,
                user_id=user_id if not auto_cancel else models.Q()
            )

            if reservation.status not in [ReservationStatus.PENDING]:
                raise BusinessLogicError("Нельзя отменить уже обработанную бронь")

            # Отменяем бронь
            new_status = ReservationStatus.EXPIRED if auto_cancel else ReservationStatus.CANCELLED
            reservation.status = new_status
            reservation.cancelled_at = timezone.now()
            reservation.save(update_fields=['status', 'cancelled_at', 'updated_at'])

            # Освобождаем резерв
            stock = ProductStock.objects.select_for_update().get(
                product=reservation.product
            )
            stock.reserved_quantity -= reservation.quantity
            stock.version += 1
            stock.save(update_fields=['reserved_quantity', 'version', 'last_updated'])

            # Очищаем кеш
            cache.delete(f"product_stock:{reservation.product.id}")

            # Уведомления
            if not auto_cancel:
                self.notification_service.send_reservation_cancelled(reservation)

            # Аналитика
            self.analytics_service.track_reservation_cancelled(reservation)

            self.logger.info(f"Reservation {'expired' if auto_cancel else 'cancelled'}: {reservation.id}")
            return reservation

        except Reservation.DoesNotExist:
            raise BusinessLogicError("Бронирование не найдено")

    def get_user_reservations(self, user_id: int, status: Optional[str] = None) -> List[Reservation]:
        """Получение списка бронирований пользователя"""
        queryset = Reservation.objects.select_related('product').filter(user_id=user_id)

        if status:
            queryset = queryset.filter(status=status)

        return queryset.order_by('-created_at')

    def cleanup_expired_reservations(self) -> int:
        """Очистка просроченных бронирований (для Celery задачи)"""
        expired_reservations = Reservation.objects.filter(
            status=ReservationStatus.PENDING,
            expires_at__lt=timezone.now()
        ).select_related('product')

        count = 0
        for reservation in expired_reservations:
            try:
                self.cancel_reservation(
                    reservation.id,
                    reservation.user_id,
                    auto_cancel=True
                )
                count += 1
            except Exception as e:
                self.logger.error(f"Error cancelling expired reservation {reservation.id}: {e}")

        return count