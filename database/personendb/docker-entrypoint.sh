#!/bin/bash
set -e

echo "Starting JARVIS Database initialization..."

# Initialize database if needed
if [ ! -s "$PGDATA/PG_VERSION" ]; then
    echo "Initializing database..."
    initdb -D "$PGDATA" --auth-host=md5 --auth-local=trust
fi

# Start PostgreSQL
exec postgres
