from rest_framework import serializers


class ErrorSerializer(serializers.Serializer):
    """Сериализатор для ошибок API"""

    error = serializers.CharField()
    code = serializers.CharField()
    details = serializers.DictField(required=False)
    timestamp = serializers.DateTimeField(required=False)


class SuccessSerializer(serializers.Serializer):
    """Сериализатор для успешных ответов"""

    message = serializers.CharField()
    data = serializers.DictField(required=False)


class PaginationSerializer(serializers.Serializer):
    """Сериализатор для пагинации"""

    count = serializers.IntegerField()
    total_pages = serializers.IntegerField()
    current_page = serializers.IntegerField()
    page_size = serializers.IntegerField()
    has_next = serializers.BooleanField()
    has_previous = serializers.BooleanField()


class HealthCheckSerializer(serializers.Serializer):
    """Сериализатор для health check"""

    status = serializers.CharField()
    services = serializers.DictField()
    timestamp = serializers.DateTimeField(required=False)