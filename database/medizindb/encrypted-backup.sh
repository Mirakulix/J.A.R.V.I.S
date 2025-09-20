#!/bin/bash
# Encrypted backup for medical data (GDPR compliance)
set -e

BACKUP_DIR="/opt/backup"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/medical_backup_$TIMESTAMP.sql.gpg"

mkdir -p "$BACKUP_DIR"

echo "Creating encrypted medical backup..."
pg_dump -h localhost -U "$POSTGRES_USER" "$POSTGRES_DB" | \
    gpg --cipher-algo AES256 --compress-algo 1 --symmetric \
    --output "$BACKUP_FILE"

echo "Encrypted backup completed: $BACKUP_FILE"
