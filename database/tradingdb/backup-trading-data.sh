#!/bin/bash
# JARVIS Trading Database - Backup Script with encryption
set -e

BACKUP_DIR="/opt/backup"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/trading_backup_$TIMESTAMP.sql"
ENCRYPTED_FILE="$BACKUP_FILE.gpg"

mkdir -p "$BACKUP_DIR"

echo "🔄 Starting trading database backup..."

# Create backup with compression
echo "📦 Creating database backup..."
pg_dump -h localhost -U "$POSTGRES_USER" "$POSTGRES_DB" | gzip > "$BACKUP_FILE.gz"

# Encrypt the backup for security
echo "🔒 Encrypting backup..."
gpg --cipher-algo AES256 --compress-algo 1 --symmetric \
    --output "$ENCRYPTED_FILE" "$BACKUP_FILE.gz"

# Remove unencrypted backup
rm -f "$BACKUP_FILE.gz"

# Backup specific tables with extra attention to sensitive data
echo "💰 Creating separate backup for sensitive trading data..."
pg_dump -h localhost -U "$POSTGRES_USER" "$POSTGRES_DB" \
    --table=portfolio_holdings \
    --table=trading_history \
    --table=api_keys_encrypted | \
    gzip | \
    gpg --cipher-algo AES256 --compress-algo 1 --symmetric \
    --output "$BACKUP_DIR/sensitive_trading_$TIMESTAMP.sql.gpg"

# Keep only last 30 encrypted backups
echo "🧹 Cleaning old backups..."
find "$BACKUP_DIR" -name "trading_backup_*.sql.gpg" -mtime +30 -delete
find "$BACKUP_DIR" -name "sensitive_trading_*.sql.gpg" -mtime +30 -delete

# Verify backup integrity
echo "✅ Verifying backup integrity..."
if gpg --list-packets "$ENCRYPTED_FILE" > /dev/null 2>&1; then
    echo "✅ Backup verification successful"
    
    # Log backup details
    BACKUP_SIZE=$(du -h "$ENCRYPTED_FILE" | cut -f1)
    echo "📊 Backup completed: $ENCRYPTED_FILE (Size: $BACKUP_SIZE)"
    
    # Optional: Upload to cloud storage (commented for security)
    # echo "☁️  Uploading to secure cloud storage..."
    # # aws s3 cp "$ENCRYPTED_FILE" s3://jarvis-trading-backups/
    
else
    echo "❌ Backup verification failed!"
    exit 1
fi

echo "🎉 Trading database backup completed successfully!"
echo "📁 Backup location: $ENCRYPTED_FILE"