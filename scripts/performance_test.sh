#!/bin/bash

set -e

# Конфигурация
BASE_URL="http://localhost"
CONCURRENT_USERS=50
TEST_DURATION="5m"
RAMP_UP_TIME="30s"

log_info() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

# Проверка зависимостей
check_dependencies() {
    if ! command -v ab &> /dev/null; then
        log_info "Установка Apache Bench..."
        sudo apt-get update && sudo apt-get install -y apache2-utils
    fi

    if ! command -v wrk &> /dev/null; then
        log_info "Установка wrk..."
        sudo apt-get install -y wrk
    fi
}

# Тест API эндпоинтов
test_api_endpoints() {
    log_info "Тестирование API эндпоинтов..."

    endpoints=(
        "/api/products/"
        "/api/products/search/?q=test"
        "/api/reservations/"
        "/health/"
    )

    for endpoint in "${endpoints[@]}"; do
        log_info "Тестирование $endpoint..."

        ab -n 1000 -c 10 -H "Accept: application/json" \
           "$BASE_URL$endpoint" > "performance_test_$(basename $endpoint).txt"

        log_info "Результаты сохранены в performance_test_$(basename $endpoint).txt"
    done
}

# Стресс тест с wrk
stress_test() {
    log_info "Выполнение стресс теста..."

    wrk -t12 -c400 -d30s \
        -H "Accept: application/json" \
        --script=scripts/wrk_script.lua \
        "$BASE_URL/api/products/"
}

# Тест создания бронирований
test_reservations() {
    log_info "Тестирование создания бронирований..."

    # Создаем временного пользователя для тестов
    cat > test_reservation.json << 'EOF'
{
    "product_id": 1,
    "quantity": 1,
    "customer_info": {"test": true}
}
EOF

    # Получаем токен авторизации (нужно настроить)
    TOKEN="your_test_token"

    ab -n 100 -c 5 \
       -H "Content-Type: application/json" \
       -H "Authorization: Token $TOKEN" \
       -p test_reservation.json \
       "$BASE_URL/api/reservations/"

    rm test_reservation.json
}

# Мониторинг ресурсов во время тестов
monitor_resources() {
    log_info "Мониторинг системных ресурсов..."

    # Запускаем мониторинг в фоне
    (
        while true; do
            echo "$(date): CPU: $(top -bn1 | grep 'Cpu(s)' | awk '{print $2}'), MEM: $(free | grep Mem | awk '{printf "%.2f%%", $3/$2 * 100.0}')"
            sleep 5
        done
    ) > system_resources.log &

    MONITOR_PID=$!

    # Выполняем тесты
    test_api_endpoints
    stress_test

    # Останавливаем мониторинг
    kill $MONITOR_PID

    log_info "Лог ресурсов сохранен в system_resources.log"
}

# Анализ результатов
analyze_results() {
    log_info "Анализ результатов тестирования..."

    # Создаем отчет
    cat > performance_report.md << 'EOF'
# Performance Test Report

## Test Configuration
- Base URL: BASE_URL_PLACEHOLDER
- Test Duration: TEST_DURATION_PLACEHOLDER
- Concurrent Users: CONCURRENT_USERS_PLACEHOLDER

## Results Summary

### API Endpoints Performance

EOF

    # Заполняем плейсхолдеры
    sed -i "s/BASE_URL_PLACEHOLDER/$BASE_URL/g" performance_report.md
    sed -i "s/TEST_DURATION_PLACEHOLDER/$TEST_DURATION/g" performance_report.md
    sed -i "s/CONCURRENT_USERS_PLACEHOLDER/$CONCURRENT_USERS/g" performance_report.md

    log_info "Отчет сохранен в performance_report.md"
}

# Основная функция
main() {
    log_info "Начало нагрузочного тестирования..."

    check_dependencies
    monitor_resources
    analyze_results

    log_info "Нагрузочное тестирование завершено"
}

case "${1:-test}" in
    "test")
        main
        ;;
    "api")
        test_api_endpoints
        ;;
    "stress")
        stress_test
        ;;
    "reservations")
        test_reservations
        ;;
    *)
        echo "Использование: $0 {test|api|stress|reservations}"
        exit 1
        ;;
esac