from rest_framework import status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema, OpenApiParameter
from drf_spectacular.types import OpenApiTypes

from apps.core.views import BaseViewSet
from apps.core.exceptions import BusinessLogicError, InsufficientStockError
from apps.reservations.serializers import ReservationSerializer, ReservationCreateSerializer
from apps.reservations.services import ReservationService
from apps.reservations.filters import ReservationFilter

from rest_framework.views import APIView
from django.db.models import Count, Sum, Avg
from django.utils import timezone
from datetime import timedelta

from apps.reservations.models import Reservation, ReservationStatus


class ReservationViewSet(BaseViewSet):
    """ViewSet для работы с бронированиями"""

    queryset = Reservation.objects.select_related('product', 'user').all()
    serializer_class = ReservationSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_class = ReservationFilter
    search_fields = ['product__name', 'product__sku']
    ordering_fields = ['created_at', 'expires_at', 'total_price']
    ordering = ['-created_at']

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.reservation_service = ReservationService()

    def get_queryset(self):
        """Пользователь видит только свои бронирования"""
        return self.queryset.filter(user=self.request.user)

    @extend_schema(
        request=ReservationCreateSerializer,
        responses={201: ReservationSerializer, 400: 'Bad Request'},
        description="Создание нового бронирования"
    )
    def create(self, request):
        """Создание бронирования"""
        serializer = ReservationCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            reservation = self.reservation_service.create_reservation(
                user_id=request.user.id,
                product_id=serializer.validated_data['product_id'],
                quantity=serializer.validated_data['quantity'],
                customer_info=serializer.validated_data.get('customer_info', {})
            )

            response_serializer = ReservationSerializer(reservation)
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)

        except InsufficientStockError as e:
            return Response(
                {'error': str(e), 'code': 'insufficient_stock'},
                status=status.HTTP_400_BAD_REQUEST
            )
        except BusinessLogicError as e:
            return Response(
                {'error': str(e), 'code': 'business_logic_error'},
                status=status.HTTP_400_BAD_REQUEST
            )

    @extend_schema(
        responses={200: ReservationSerializer, 404: 'Not Found'},
        description="Подтверждение бронирования"
    )
    @action(detail=True, methods=['post'])
    def confirm(self, request, pk=None):
        """Подтверждение бронирования"""
        try:
            reservation = self.reservation_service.confirm_reservation(
                reservation_id=pk,
                user_id=request.user.id
            )

            serializer = ReservationSerializer(reservation)
            return Response(serializer.data)

        except BusinessLogicError as e:
            return Response(
                {'error': str(e), 'code': 'business_logic_error'},
                status=status.HTTP_400_BAD_REQUEST
            )

    @extend_schema(
        responses={200: ReservationSerializer, 404: 'Not Found'},
        description="Отмена бронирования"
    )
    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """Отмена бронирования"""
        try:
            reservation = self.reservation_service.cancel_reservation(
                reservation_id=pk,
                user_id=request.user.id
            )

            serializer = ReservationSerializer(reservation)
            return Response(serializer.data)

        except BusinessLogicError as e:
            return Response(
                {'error': str(e), 'code': 'business_logic_error'},
                status=status.HTTP_400_BAD_REQUEST
            )

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name='status',
                type=OpenApiTypes.STR,
                description='Фильтр по статусу',
                enum=[choice[0] for choice in ReservationStatus.choices]
            )
        ],
        description="Получение списка бронирований пользователя"
    )
    @action(detail=False, methods=['get'])
    def my_reservations(self, request):
        """Получение бронирований текущего пользователя"""
        status_filter = request.query_params.get('status')
        reservations = self.reservation_service.get_user_reservations(
            user_id=request.user.id,
            status=status_filter
        )

        page = self.paginate_queryset(reservations)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(reservations, many=True)
        return Response(serializer.data)


class ReservationStatsView(APIView):
    """Статистика бронирований"""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        # Базовая статистика
        total_reservations = Reservation.objects.count()
        active_reservations = Reservation.objects.filter(
            status=ReservationStatus.PENDING
        ).count()

        # Статистика по статусам
        status_stats = Reservation.objects.values('status').annotate(
            count=Count('id')
        )

        # Статистика за период
        today = timezone.now().date()
        week_ago = today - timedelta(days=7)
        month_ago = today - timedelta(days=30)

        today_stats = Reservation.objects.filter(created_at__date=today).aggregate(
            count=Count('id'),
            total_amount=Sum('total_price')
        )

        week_stats = Reservation.objects.filter(
            created_at__date__gte=week_ago
        ).aggregate(
            count=Count('id'),
            total_amount=Sum('total_price'),
            avg_amount=Avg('total_price')
        )

        month_stats = Reservation.objects.filter(
            created_at__date__gte=month_ago
        ).aggregate(
            count=Count('id'),
            total_amount=Sum('total_price'),
            avg_amount=Avg('total_price')
        )

        return Response({
            'overview': {
                'total_reservations': total_reservations,
                'active_reservations': active_reservations,
            },
            'by_status': {item['status']: item['count'] for item in status_stats},
            'periods': {
                'today': today_stats,
                'week': week_stats,
                'month': month_stats,
            }
        })


class UserReservationHistoryView(APIView):
    """История бронирований пользователя"""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        reservations = Reservation.objects.filter(
            user=request.user
        ).select_related('product').order_by('-created_at')

        # Фильтрация по статусу
        status_filter = request.query_params.get('status')
        if status_filter:
            reservations = reservations.filter(status=status_filter)

        # Пагинация
        from apps.core.pagination import StandardResultsSetPagination
        from apps.reservations.serializers import ReservationSerializer

        paginator = StandardResultsSetPagination()
        page = paginator.paginate_queryset(reservations, request)

        serializer = ReservationSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)