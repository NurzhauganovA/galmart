from django.db import models
from django.utils import timezone
from django.core.validators import MinValueValidator
from django.conf import settings
from datetime import timedelta
from django.utils.translation import gettext_lazy as _
import uuid


class ReservationStatus(models.TextChoices):
    PENDING = 'pending', _('Pending')
    CONFIRMED = 'confirmed', _('Confirmed')
    CANCELLED = 'cancelled', _('Cancelled')
    EXPIRED = 'expired', _('Expired')


class Reservation(models.Model):
    """Модель бронирования"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='reservations'
    )
    product = models.ForeignKey(
        'products.Product',
        on_delete=models.CASCADE,
        related_name='reservations'
    )
    quantity = models.PositiveIntegerField(
        _('quantity'),
        validators=[MinValueValidator(1)]
    )
    status = models.CharField(
        _('status'),
        max_length=20,
        choices=ReservationStatus.choices,
        default=ReservationStatus.PENDING
    )
    price_per_item = models.DecimalField(
        _('price per item'),
        max_digits=10,
        decimal_places=2
    )
    total_price = models.DecimalField(
        _('total price'),
        max_digits=12,
        decimal_places=2
    )
    expires_at = models.DateTimeField(_('expires at'))
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    confirmed_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)

    # Дополнительная информация
    notes = models.TextField(_('notes'), blank=True)
    customer_info = models.JSONField(_('customer info'), default=dict, blank=True)

    class Meta:
        db_table = 'reservations'
        indexes = [
            models.Index(fields=['user']),
            models.Index(fields=['product']),
            models.Index(fields=['status']),
            models.Index(fields=['expires_at']),
            models.Index(fields=['created_at']),
            models.Index(fields=['-created_at']),
            models.Index(fields=['user', 'status']),
            models.Index(fields=['product', 'status']),
        ]
        constraints = [
            models.CheckConstraint(
                check=models.Q(quantity__gt=0),
                name='positive_quantity'
            ),
            models.CheckConstraint(
                check=models.Q(total_price__gte=0),
                name='non_negative_total_price'
            ),
        ]

    def save(self, *args, **kwargs):
        if not self.expires_at:
            self.expires_at = timezone.now() + timedelta(
                minutes=settings.RESERVATION_TIMEOUT_MINUTES
            )
        if not self.total_price:
            self.total_price = self.price_per_item * self.quantity
        super().save(*args, **kwargs)

    @property
    def is_expired(self):
        return timezone.now() > self.expires_at