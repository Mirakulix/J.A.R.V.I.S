#!/bin/bash
set -e

echo "Starting JARVIS Database initialization..."

# Switch to postgres user for initialization and execution
if [ "$(id -u)" = '0' ]; then
    # Create postgres user if it doesn't exist
    if ! id postgres &>/dev/null; then
        adduser -D -s /bin/sh postgres
    fi
    
    # Change ownership of data directory
    mkdir -p "$PGDATA"
    chown -R postgres:postgres "$PGDATA"
    chmod 0700 "$PGDATA"
    
    # Initialize database if needed as postgres user
    if [ ! -s "$PGDATA/PG_VERSION" ]; then
        echo "Initializing database..."
        su-exec postgres initdb -D "$PGDATA" --auth-host=md5 --auth-local=trust
    fi
    
    # Start PostgreSQL as postgres user
    exec su-exec postgres postgres
else
    # Already running as postgres user
    if [ ! -s "$PGDATA/PG_VERSION" ]; then
        echo "Initializing database..."
        initdb -D "$PGDATA" --auth-host=md5 --auth-local=trust
    fi
    exec postgres
fi
