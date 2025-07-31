from django.conf import settings


class DatabaseRouter:
    """
    Маршрутизатор для разделения основной и аналитической баз данных
    """

    # Модели, которые должны храниться в аналитической базе
    ANALYTICS_MODELS = {
        'analytics',  # все модели из приложения analytics
    }

    # Конкретные модели для аналитической БД
    ANALYTICS_MODEL_NAMES = {
        'realtimemetric',
        'conversionevent',
        'dailyanalytics',
        'productview',
        'searchquery',
        'useractionlog',
    }

    def db_for_read(self, model, **hints):
        """Определяет базу данных для чтения"""
        if self._is_analytics_model(model):
            return 'analytics'
        return 'default'

    def db_for_write(self, model, **hints):
        """Определяет базу данных для записи"""
        if self._is_analytics_model(model):
            return 'analytics'
        return 'default'

    def allow_relation(self, obj1, obj2, **hints):
        """Разрешает отношения между объектами из одной базы"""
        db_set = {'default', 'analytics'}
        if obj1._state.db in db_set and obj2._state.db in db_set:
            return True
        return None

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        """Определяет, в какой базе создавать таблицы"""
        if db == 'analytics':
            # В аналитической базе создаем только аналитические модели
            return (
                    app_label in self.ANALYTICS_MODELS or
                    (model_name and model_name.lower() in self.ANALYTICS_MODEL_NAMES) or
                    self._has_analytics_routing_key(hints.get('model'))
            )
        elif db == 'default':
            # В основной базе создаем все, кроме аналитических
            return not (
                    app_label in self.ANALYTICS_MODELS or
                    (model_name and model_name.lower() in self.ANALYTICS_MODEL_NAMES) or
                    self._has_analytics_routing_key(hints.get('model'))
            )
        return False

    def _is_analytics_model(self, model):
        """Проверяет, является ли модель аналитической"""
        if not model:
            return False

        app_label = model._meta.app_label
        model_name = model._meta.model_name.lower()

        # Проверяем по приложению
        if app_label in self.ANALYTICS_MODELS:
            return True

        # Проверяем по имени модели
        if model_name in self.ANALYTICS_MODEL_NAMES:
            return True

        # Проверяем по routing_key в Meta
        return self._has_analytics_routing_key(model)

    def _has_analytics_routing_key(self, model):
        """Проверяет наличие routing_key='analytics' в модели"""
        if not model:
            return False

        meta = getattr(model, '_meta', None)
        if not meta:
            return False

        return getattr(meta, 'routing_key', None) == 'analytics'