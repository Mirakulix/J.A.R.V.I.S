#!/bin/bash
set -e

BACKUP_DIR="/opt/backup"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/backup_$TIMESTAMP.sql"

mkdir -p "$BACKUP_DIR"

echo "Creating backup: $BACKUP_FILE"
pg_dump -h localhost -U "$POSTGRES_USER" "$POSTGRES_DB" > "$BACKUP_FILE"

# Keep only last 7 backups
find "$BACKUP_DIR" -name "backup_*.sql" -mtime +7 -delete

echo "Backup completed: $BACKUP_FILE"
