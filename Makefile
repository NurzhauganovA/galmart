.PHONY: help build up down restart logs shell test lint format clean backup deploy

# Переменные
COMPOSE_FILE = docker-compose.yml
PROJECT_NAME = galmart
PYTHON_VERSION = 3.11

# Цвета для вывода
GREEN = \033[32m
RED = \033[31m
YELLOW = \033[33m
BLUE = \033[34m
NC = \033[0m # No Color

# По умолчанию показываем help
help: ## Показать все доступные команды
	@echo "$(GREEN)Galmart Project Management$(NC)"
	@echo "$(BLUE)=========================$(NC)"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "$(YELLOW)%-20s$(NC) %s\n", $$1, $$2}'

# === Управление контейнерами ===

build: ## Собрать все Docker образы
	@echo "$(GREEN)Сборка Docker образов...$(NC)"
	docker-compose build --no-cache

up: ## Запустить все сервисы
	@echo "$(GREEN)Запуск всех сервисов...$(NC)"
	docker-compose up -d
	@echo "$(GREEN)Сервисы запущены. Проверьте статус: make status$(NC)"

down: ## Остановить все сервисы
	@echo "$(YELLOW)Остановка всех сервисов...$(NC)"
	docker-compose down

restart: ## Перезапустить все сервисы
	@echo "$(YELLOW)Перезапуск сервисов...$(NC)"
	docker-compose restart

status: ## Показать статус сервисов
	@echo "$(BLUE)Статус сервисов:$(NC)"
	docker-compose ps

logs: ## Показать логи всех сервисов
	docker-compose logs -f --tail=100

logs-web: ## Показать логи веб-приложения
	docker-compose logs -f --tail=100 web

logs-celery: ## Показать логи Celery worker
	docker-compose logs -f --tail=100 celery_worker

logs-db: ## Показать логи базы данных
	docker-compose logs -f --tail=100 postgres_main

# === Работа с приложением ===

shell: ## Запустить Django shell
	docker-compose exec web python manage.py shell

shell-db: ## Подключиться к основной базе данных
	docker-compose exec postgres_main psql -U postgres -d galmart_main

shell-analytics: ## Подключиться к аналитической базе данных
	docker-compose exec postgres_analytics psql -U postgres -d galmart_analytics

shell-redis: ## Подключиться к Redis
	docker-compose exec redis redis-cli

migrate: ## Выполнить миграции
	@echo "$(GREEN)Выполнение миграций...$(NC)"
	docker-compose exec web python manage.py migrate
	docker-compose exec web python manage.py migrate --database=analytics

makemigrations: ## Создать новые миграции
	@echo "$(GREEN)Создание миграций...$(NC)"
	docker-compose exec web python manage.py makemigrations

collectstatic: ## Собрать статические файлы
	@echo "$(GREEN)Сбор статических файлов...$(NC)"
	docker-compose exec web python manage.py collectstatic --noinput

superuser: ## Создать суперпользователя
	docker-compose exec web python manage.py createsuperuser

loaddata: ## Загрузить тестовые данные
	@echo "$(GREEN)Загрузка тестовых данных...$(NC)"
	docker-compose exec web python manage.py loaddata fixtures/test_data.json

# === Тестирование ===

test: ## Запустить все тесты
	@echo "$(GREEN)Запуск тестов...$(NC)"
	docker-compose exec web python -m pytest

test-unit: ## Запустить только unit тесты
	@echo "$(GREEN)Запуск unit тестов...$(NC)"
	docker-compose exec web python -m pytest -m "unit"

test-integration: ## Запустить интеграционные тесты
	@echo "$(GREEN)Запуск интеграционных тестов...$(NC)"
	docker-compose exec web python -m pytest -m "integration"

test-coverage: ## Запустить тесты с покрытием
	@echo "$(GREEN)Запуск тестов с покрытием...$(NC)"
	docker-compose exec web python -m pytest --cov=apps --cov-report=html --cov-report=term

test-performance: ## Запустить нагрузочные тесты
	@echo "$(GREEN)Запуск нагрузочных тестов...$(NC)"
	./scripts/performance_test.sh

# === Качество кода ===

lint: ## Проверить код с помощью линтеров
	@echo "$(GREEN)Проверка кода...$(NC)"
	docker-compose exec web flake8 apps/
	docker-compose exec web mypy apps/
	docker-compose exec web bandit -r apps/

format: ## Форматировать код
	@echo "$(GREEN)Форматирование кода...$(NC)"
	docker-compose exec web black apps/
	docker-compose exec web isort apps/

check-security: ## Проверка безопасности
	@echo "$(GREEN)Проверка безопасности...$(NC)"
	docker-compose exec web python manage.py check --deploy
	docker-compose exec web safety check

# === Управление данными ===

backup: ## Создать резервную копию
	@echo "$(GREEN)Создание резервной копии...$(NC)"
	./scripts/backup.sh backup

restore: ## Восстановить из резервной копии
	@if [ -z "$(DATE)" ]; then \
		echo "$(RED)Укажите дату бэкапа: make restore DATE=20231201_120000$(NC)"; \
		exit 1; \
	fi
	@echo "$(YELLOW)Восстановление из бэкапа $(DATE)...$(NC)"
	./scripts/backup.sh restore $(DATE)

flush-db: ## Очистить базу данных
	@echo "$(RED)ВНИМАНИЕ: Это удалит все данные!$(NC)"
	@read -p "Вы уверены? (y/N): " confirm && [ "$$confirm" = "y" ]
	docker-compose exec web python manage.py flush --noinput

reset-db: ## Пересоздать базу данных
	@echo "$(RED)ВНИМАНИЕ: Это пересоздаст базу данных!$(NC)"
	@read -p "Вы уверены? (y/N): " confirm && [ "$$confirm" = "y" ]
	docker-compose down
	docker volume rm galmart_postgres_main_data galmart_postgres_analytics_data || true
	docker-compose up -d postgres_main postgres_analytics
	sleep 10
	make migrate
	make loaddata

# === Мониторинг и отладка ===

health: ## Проверить здоровье сервисов
	@echo "$(GREEN)Проверка здоровья сервисов...$(NC)"
	./scripts/deploy.sh health

monitor: ## Открыть интерфейсы мониторинга
	@echo "$(GREEN)Интерфейсы мониторинга:$(NC)"
	@echo "$(BLUE)Grafana:$(NC)     http://localhost:3000"
	@echo "$(BLUE)Prometheus:$(NC)  http://localhost:9090"
	@echo "$(BLUE)Flower:$(NC)      http://localhost:5555"
	@echo "$(BLUE)Kafka UI:$(NC)    http://localhost:8080"

ps: ## Показать запущенные процессы
	docker-compose ps

top: ## Показать использование ресурсов
	docker stats

exec-web: ## Подключиться к контейнеру веб-приложения
	docker-compose exec web bash

exec-db: ## Подключиться к контейнеру базы данных
	docker-compose exec postgres_main bash

# === Разработка ===

dev-setup: ## Настроить окружение для разработки
	@echo "$(GREEN)Настройка окружения для разработки...$(NC)"
	python -m venv venv
	./venv/bin/pip install -r requirements/development.txt
	./venv/bin/pre-commit install

dev-run: ## Запустить в режиме разработки
	@echo "$(GREEN)Запуск в режиме разработки...$(NC)"
	docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d

install-hooks: ## Установить pre-commit хуки
	docker-compose exec web pre-commit install

run-hooks: ## Запустить pre-commit хуки
	docker-compose exec web pre-commit run --all-files

# === Производство ===

deploy: ## Развернуть в production
	@echo "$(GREEN)Развертывание в production...$(NC)"
	./scripts/deploy.sh deploy

deploy-staging: ## Развернуть на staging
	@echo "$(GREEN)Развертывание на staging...$(NC)"
	COMPOSE_FILE=docker-compose.staging.yml ./scripts/deploy.sh deploy

# === Очистка ===

clean: ## Очистить неиспользуемые Docker ресурсы
	@echo "$(YELLOW)Очистка Docker ресурсов...$(NC)"
	docker system prune -f
	docker volume prune -f

clean-all: ## Полная очистка (осторожно!)
	@echo "$(RED)ВНИМАНИЕ: Это удалит ВСЕ данные и образы!$(NC)"
	@read -p "Вы уверены? (y/N): " confirm && [ "$$confirm" = "y" ]
	docker-compose down -v --rmi all
	docker system prune -af
	docker volume prune -f

# === Утилиты ===

init: ## Первоначальная настройка проекта
	@echo "$(GREEN)Инициализация проекта...$(NC)"
	cp .env.example .env
	@echo "$(YELLOW)Отредактируйте файл .env перед запуском$(NC)"
	make build
	make up
	sleep 30
	make migrate
	make superuser
	make loaddata
	@echo "$(GREEN)Проект готов к работе!$(NC)"

update: ## Обновить зависимости
	@echo "$(GREEN)Обновление зависимостей...$(NC)"
	docker-compose build --no-cache
	make migrate
	make collectstatic

scale-workers: ## Масштабировать Celery worker'ы
	@if [ -z "$(NUM)" ]; then \
		echo "$(RED)Укажите количество worker'ов: make scale-workers NUM=3$(NC)"; \
		exit 1; \
	fi
	docker-compose up -d --scale celery_worker=$(NUM)

kafka-topics: ## Показать Kafka топики
	docker-compose exec kafka kafka-topics --bootstrap-server localhost:9092 --list

kafka-consumer: ## Запустить Kafka consumer
	docker-compose exec web python manage.py kafka_consumer

# === Документация ===

docs: ## Сгенерировать документацию
	@echo "$(GREEN)Генерация документации...$(NC)"
	docker-compose exec web sphinx-build -b html docs/ docs/_build/html/

docs-serve: ## Запустить сервер с документацией
	@echo "$(GREEN)Запуск сервера документации...$(NC)"
	cd docs/_build/html && python -m http.server 8080

api-docs: ## Открыть API документацию
	@echo "$(GREEN)API документация доступна по адресу:$(NC)"
	@echo "$(BLUE)http://localhost:8000/api/schema/swagger-ui/$(NC)"

schema: ## Сгенерировать OpenAPI схему
	docker-compose exec web python manage.py spectacular --file schema.yml

# === Специальные команды ===

fix-permissions: ## Исправить права доступа к файлам
	@echo "$(GREEN)Исправление прав доступа...$(NC)"
	sudo chown -R $USER:$USER .
	chmod +x scripts/*.sh

create-app: ## Создать новое Django приложение
	@if [ -z "$(NAME)" ]; then \
		echo "$(RED)Укажите имя приложения: make create-app NAME=myapp$(NC)"; \
		exit 1; \
	fi
	docker-compose exec web python manage.py startapp $(NAME) apps/$(NAME)
	@echo "$(GREEN)Приложение $(NAME) создано в apps/$(NAME)$(NC)"

celery-purge: ## Очистить очереди Celery
	docker-compose exec celery_worker celery -A galmart purge -f

celery-inspect: ## Показать информацию о Celery worker'ах
	docker-compose exec celery_worker celery -A galmart inspect active
	docker-compose exec celery_worker celery -A galmart inspect stats

# === Информация ===

urls: ## Показать все доступные URL
	@echo "$(GREEN)Основные URL:$(NC)"
	@echo "$(BLUE)Приложение:$(NC)      http://localhost"
	@echo "$(BLUE)API:$(NC)             http://localhost/api/"
	@echo "$(BLUE)Admin:$(NC)           http://localhost/admin/"
	@echo "$(BLUE)API Docs:$(NC)        http://localhost/api/schema/swagger-ui/"
	@echo "$(BLUE)Grafana:$(NC)         http://localhost:3000"
	@echo "$(BLUE)Prometheus:$(NC)      http://localhost:9090"
	@echo "$(BLUE)Flower:$(NC)          http://localhost:5555"
	@echo "$(BLUE)Kafka UI:$(NC)        http://localhost:8080"

version: ## Показать версии компонентов
	@echo "$(GREEN)Версии компонентов:$(NC)"
	@echo "$(BLUE)Python:$(NC)   $(PYTHON_VERSION)"
	@echo "$(BLUE)Django:$(NC)   $(docker-compose exec web python -c 'import django; print(django.get_version())')"
	@echo "$(BLUE)PostgreSQL:$(NC) $(docker-compose exec postgres_main psql --version | head -1)"
	@echo "$(BLUE)Redis:$(NC)    $(docker-compose exec redis redis-server --version)"

env-check: ## Проверить переменные окружения
	@echo "$(GREEN)Проверка переменных окружения:$(NC)"
	@if [ ! -f .env ]; then \
		echo "$(RED)Файл .env не найден! Скопируйте .env.example в .env$(NC)"; \
		exit 1; \
	fi
	@echo "$(GREEN)✓ Файл .env найден$(NC)"
	@grep -q "SECRET_KEY" .env && echo "$(GREEN)✓ SECRET_KEY установлен$(NC)" || echo "$(RED)✗ SECRET_KEY не установлен$(NC)"
	@grep -q "DATABASE_URL" .env && echo "$(GREEN)✓ DATABASE_URL установлен$(NC)" || echo "$(RED)✗ DATABASE_URL не установлен$(NC)"

# === Быстрые команды ===

quick-start: build up migrate loaddata ## Быстрый старт (build + up + migrate + loaddata)
	@echo "$(GREEN)Быстрый старт завершен!$(NC)"
	make urls

quick-restart: down up ## Быстрый перезапуск
	@echo "$(GREEN)Перезапуск завершен!$(NC)"

quick-clean: down clean ## Быстрая очистка
	@echo "$(GREEN)Очистка завершена!$(NC)"

# === Алиасы ===

start: up ## Алиас для up
stop: down ## Алиас для down
build-up: build up ## Сборка и запуск
log: logs ## Алиас для logs
db: shell-db ## Алиас для shell-db
redis: shell-redis ## Алиас для shell-redis

# Проверка, что make выполняется с правильными правами
check-docker:
	@if ! docker info >/dev/null 2>&1; then \
		echo "$(RED)Ошибка: Docker недоступен. Убедитесь, что Docker запущен и у вас есть права доступа.$(NC)"; \
		exit 1; \
	fi

# Все команды требуют проверки Docker
%: check-docker

# Показать справку по умолчанию
.DEFAULT_GOAL := help