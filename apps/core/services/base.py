from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from django.db import transaction
from django.core.cache import cache
import logging

logger = logging.getLogger(__name__)


class BaseService(ABC):
    """Базовый класс для сервисов"""

    def __init__(self):
        self.logger = logger

    @abstractmethod
    def validate_data(self, data: Dict[str, Any]) -> bool:
        """Валидация входных данных"""
        pass