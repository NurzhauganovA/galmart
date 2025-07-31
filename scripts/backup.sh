#!/bin/bash

set -e

BACKUP_DIR="/backups"
DATE=$(date +%Y%m%d_%H%M%S)

# Создание директории для бэкапов
mkdir -p $BACKUP_DIR

log_info() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

# Бэкап основной базы данных
backup_main_db() {
    log_info "Создание бэкапа основной базы данных..."

    docker-compose exec -T postgres_main pg_dump \
        -U postgres \
        -d galmart_main \
        --verbose \
        --clean \
        --no-owner \
        --no-privileges \
        | gzip > "$BACKUP_DIR/galmart_main_$DATE.sql.gz"

    log_info "Бэкап основной БД создан: galmart_main_$DATE.sql.gz"
}

# Бэкап аналитической базы данных
backup_analytics_db() {
    log_info "Создание бэкапа аналитической базы данных..."

    docker-compose exec -T postgres_analytics pg_dump \
        -U postgres \
        -d galmart_analytics \
        --verbose \
        --clean \
        --no-owner \
        --no-privileges \
        | gzip > "$BACKUP_DIR/galmart_analytics_$DATE.sql.gz"

    log_info "Бэкап аналитической БД создан: galmart_analytics_$DATE.sql.gz"
}

# Бэкап медиа файлов
backup_media() {
    log_info "Создание бэкапа медиа файлов..."

    tar -czf "$BACKUP_DIR/media_$DATE.tar.gz" media/

    log_info "Бэкап медиа создан: media_$DATE.tar.gz"
}

# Очистка старых бэкапов (старше 30 дней)
cleanup_old_backups() {
    log_info "Очистка старых бэкапов..."

    find $BACKUP_DIR -name "*.gz" -mtime +30 -delete

    log_info "Старые бэкапы удалены"
}

# Основная функция
main() {
    log_info "Начало резервного копирования..."

    backup_main_db
    backup_analytics_db
    backup_media
    cleanup_old_backups

    log_info "Резервное копирование завершено"
    log_info "Бэкапы сохранены в: $BACKUP_DIR"
}

case "${1:-backup}" in
    "backup")
        main
        ;;
    "restore")
        if [[ -z "$2" ]]; then
            echo "Использование: $0 restore <дата_бэкапа>"
            echo "Пример: $0 restore 20231201_120000"
            exit 1
        fi

        BACKUP_DATE="$2"
        log_info "Восстановление из бэкапа $BACKUP_DATE..."

        # Восстановление основной БД
        if [[ -f "$BACKUP_DIR/galmart_main_$BACKUP_DATE.sql.gz" ]]; then
            log_info "Восстановление основной БД..."
            gunzip -c "$BACKUP_DIR/galmart_main_$BACKUP_DATE.sql.gz" | \
                docker-compose exec -T postgres_main psql -U postgres -d galmart_main
        fi

        # Восстановление аналитической БД
        if [[ -f "$BACKUP_DIR/galmart_analytics_$BACKUP_DATE.sql.gz" ]]; then
            log_info "Восстановление аналитической БД..."
            gunzip -c "$BACKUP_DIR/galmart_analytics_$BACKUP_DATE.sql.gz" | \
                docker-compose exec -T postgres_analytics psql -U postgres -d galmart_analytics
        fi

        # Восстановление медиа
        if [[ -f "$BACKUP_DIR/media_$BACKUP_DATE.tar.gz" ]]; then
            log_info "Восстановление медиа файлов..."
            tar -xzf "$BACKUP_DIR/media_$BACKUP_DATE.tar.gz"
        fi

        log_info "Восстановление завершено"
        ;;
    *)
        echo "Использование: $0 {backup|restore}"
        exit 1
        ;;
esac