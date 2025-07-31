#!/bin/bash

set -e

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Функции для логирования
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Проверка переменных окружения
check_environment() {
    log_info "Проверка переменных окружения..."

    required_vars=(
        "DATABASE_URL"
        "ANALYTICS_DATABASE_URL"
        "REDIS_URL"
        "SECRET_KEY"
        "KAFKA_BOOTSTRAP_SERVERS"
    )

    for var in "${required_vars[@]}"; do
        if [[ -z "${!var}" ]]; then
            log_error "Переменная окружения $var не установлена!"
            exit 1
        fi
    done

    log_info "Все необходимые переменные окружения установлены"
}

# Проверка зависимостей
check_dependencies() {
    log_info "Проверка зависимостей..."

    # Проверяем Docker
    if ! command -v docker &> /dev/null; then
        log_error "Docker не установлен!"
        exit 1
    fi

    # Проверяем Docker Compose
    if ! command -v docker-compose &> /dev/null; then
        log_error "Docker Compose не установлен!"
        exit 1
    fi

    log_info "Все зависимости установлены"
}

# Создание директорий
create_directories() {
    log_info "Создание необходимых директорий..."

    directories=(
        "logs"
        "staticfiles"
        "media"
        "monitoring/grafana/dashboards"
        "nginx"
    )

    for dir in "${directories[@]}"; do
        mkdir -p "$dir"
        log_info "Создана директория: $dir"
    done
}

# Настройка Nginx
setup_nginx() {
    log_info "Настройка Nginx..."

    cat > nginx/nginx.conf << 'EOF'
worker_processes auto;

events {
    worker_connections 1024;
    use epoll;
}

http {
    include /etc/nginx/mime.types;
    default_type application/octet-stream;

    # Логирование
    log_format main '$remote_addr - $remote_user [$time_local] "$request" '
                   '$status $body_bytes_sent "$http_referer" '
                   '"$http_user_agent" "$http_x_forwarded_for"';

    access_log /var/log/nginx/access.log main;
    error_log /var/log/nginx/error.log warn;

    # Основные настройки
    sendfile on;
    tcp_nopush on;
    tcp_nodelay on;
    keepalive_timeout 65;
    types_hash_max_size 2048;

    # Gzip сжатие
    gzip on;
    gzip_vary on;
    gzip_proxied any;
    gzip_comp_level 6;
    gzip_types
        text/plain
        text/css
        text/xml
        text/javascript
        application/json
        application/javascript
        application/xml+rss
        application/atom+xml
        image/svg+xml;

    # Rate limiting
    limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
    limit_req_zone $binary_remote_addr zone=general:10m rate=1r/s;

    upstream galmart_backend {
        server web:8000;
        keepalive 32;
    }

    server {
        listen 80;
        server_name _;
        client_max_body_size 20M;

        # API endpoints
        location /api/ {
            limit_req zone=api burst=20 nodelay;
            proxy_pass http://galmart_backend;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            proxy_connect_timeout 30s;
            proxy_send_timeout 30s;
            proxy_read_timeout 30s;
        }

        # Admin panel
        location /admin/ {
            limit_req zone=general burst=5 nodelay;
            proxy_pass http://galmart_backend;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }

        # Static files
        location /static/ {
            alias /app/staticfiles/;
            expires 1y;
            add_header Cache-Control "public, immutable";
        }

        # Media files
        location /media/ {
            alias /app/media/;
            expires 1m;
        }

        # Health check
        location /health/ {
            proxy_pass http://galmart_backend;
            access_log off;
        }

        # Metrics для Prometheus
        location /metrics {
            proxy_pass http://galmart_backend;
            allow 172.16.0.0/12;  # Docker networks
            deny all;
        }

        # Основное приложение
        location / {
            proxy_pass http://galmart_backend;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }
    }
}
EOF

    log_info "Nginx настроен"
}

# Настройка мониторинга
setup_monitoring() {
    log_info "Настройка мониторинга..."

    # Создаем dashboard для Grafana
    cat > monitoring/grafana/dashboards/galmart-dashboard.json << 'EOF'
{
  "dashboard": {
    "id": null,
    "title": "Galmart Monitoring",
    "tags": ["galmart"],
    "timezone": "browser",
    "panels": [
      {
        "id": 1,
        "title": "Request Rate",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(django_http_requests_total[5m])",
            "legendFormat": "{{method}} {{handler}}"
          }
        ],
        "yAxes": [
          {
            "label": "requests/sec"
          }
        ]
      },
      {
        "id": 2,
        "title": "Response Time",
        "type": "graph",
        "targets": [
          {
            "expr": "histogram_quantile(0.95, rate(django_http_request_duration_seconds_bucket[5m]))",
            "legendFormat": "95th percentile"
          }
        ]
      },
      {
        "id": 3,
        "title": "Active Reservations",
        "type": "singlestat",
        "targets": [
          {
            "expr": "galmart_active_reservations_total"
          }
        ]
      },
      {
        "id": 4,
        "title": "Database Connections",
        "type": "graph",
        "targets": [
          {
            "expr": "django_db_connections_total"
          }
        ]
      }
    ],
    "time": {
      "from": "now-1h",
      "to": "now"
    },
    "refresh": "5s"
  }
}
EOF

    log_info "Мониторинг настроен"
}

# Инициализация базы данных
init_database() {
    log_info "Инициализация базы данных..."

    # Ждем, пока базы данных будут готовы
    log_info "Ожидание готовности базы данных..."
    docker-compose exec -T web python manage.py wait_for_db

    # Выполняем миграции
    log_info "Выполнение миграций для основной БД..."
    docker-compose exec -T web python manage.py migrate

    log_info "Выполнение миграций для аналитической БД..."
    docker-compose exec -T web python manage.py migrate --database=analytics

    # Создаем суперпользователя, если не существует
    log_info "Создание суперпользователя..."
    docker-compose exec -T web python manage.py shell << 'EOF'
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(is_superuser=True).exists():
    User.objects.create_superuser('admin', 'admin@galmart.com', 'admin123')
    print('Суперпользователь создан: admin/admin123')
else:
    print('Суперпользователь уже существует')
EOF

    # Загружаем фикстуры с тестовыми данными
    log_info "Загрузка тестовых данных..."
    docker-compose exec -T web python manage.py loaddata fixtures/test_data.json

    log_info "База данных инициализирована"
}

# Сборка и запуск контейнеров
build_and_start() {
    log_info "Сборка и запуск контейнеров..."

    # Останавливаем существующие контейнеры
    docker-compose down

    # Собираем образы
    log_info "Сборка образов..."
    docker-compose build --no-cache

    # Запускаем инфраструктуру
    log_info "Запуск инфраструктуры..."
    docker-compose up -d postgres_main postgres_analytics redis zookeeper kafka

    # Ждем готовности инфраструктуры
    log_info "Ожидание готовности инфраструктуры..."
    sleep 30

    # Запускаем приложение
    log_info "Запуск приложения..."
    docker-compose up -d

    log_info "Контейнеры запущены"
}

# Проверка здоровья сервисов
health_check() {
    log_info "Проверка здоровья сервисов..."

    services=(
        "http://localhost:8000/health/"
        "http://localhost:3000"  # Grafana
        "http://localhost:9090"  # Prometheus
        "http://localhost:5555"  # Flower
    )

    for service in "${services[@]}"; do
        log_info "Проверка $service..."
        if curl -f -s "$service" > /dev/null; then
            log_info "✓ $service работает"
        else
            log_warn "✗ $service недоступен"
        fi
    done
}

# Основная функция развертывания
main() {
    log_info "Начало развертывания Galmart..."

    check_dependencies
    check_environment
    create_directories
    setup_nginx
    setup_monitoring
    build_and_start
    init_database
    health_check

    log_info "Развертывание завершено успешно!"
    log_info ""
    log_info "Сервисы доступны по адресам:"
    log_info "• Приложение:     http://localhost"
    log_info "• API:            http://localhost/api/"
    log_info "• Admin панель:   http://localhost/admin/"
    log_info "• Grafana:        http://localhost:3000 (admin/admin123)"
    log_info "• Prometheus:     http://localhost:9090"
    log_info "• Flower:         http://localhost:5555"
    log_info "• Kafka UI:       http://localhost:8080"
    log_info ""
    log_info "Для просмотра логов: docker-compose logs -f"
    log_info "Для остановки: docker-compose down"
}

# Обработка параметров командной строки
case "${1:-deploy}" in
    "deploy")
        main
        ;;
    "stop")
        log_info "Остановка всех сервисов..."
        docker-compose down
        ;;
    "restart")
        log_info "Перезапуск сервисов..."
        docker-compose restart
        ;;
    "logs")
        docker-compose logs -f "${2:-}"
        ;;
    "health")
        health_check
        ;;
    *)
        echo "Использование: $0 {deploy|stop|restart|logs|health}"
        exit 1
        ;;
esac