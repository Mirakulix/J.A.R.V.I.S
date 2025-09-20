#!/bin/bash
# JARVIS Multi-Container Setup Script

set -e

echo "🤖 Setting up JARVIS Multi-Container Environment..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    print_error "Docker is not installed. Please install Docker first."
    exit 1
fi

# Check if Docker Compose is installed (either docker-compose or docker compose)
DOCKER_COMPOSE=""
if command -v docker-compose &> /dev/null; then
    DOCKER_COMPOSE="docker-compose"
elif docker compose version &> /dev/null; then
    DOCKER_COMPOSE="docker compose"
else
    print_error "Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi

print_status "Using Docker Compose: $DOCKER_COMPOSE"

# Create necessary directories
print_status "Creating directory structure..."
mkdir -p secrets
mkdir -p logs
mkdir -p backups
mkdir -p nginx/ssl
mkdir -p database/{personendb,organisationdb,medizindb,temporarydb,vectordb,tradingdb}/{init,migrations,backup}

# Create secrets directory structure
print_status "Setting up secrets directory..."
touch secrets/onepassword_token.txt
touch secrets/claude_code_api_key.txt
touch secrets/postgres_persons_password.txt
touch secrets/postgres_org_password.txt
touch secrets/postgres_medical_password.txt
touch secrets/postgres_trading_password.txt
touch secrets/medical_encryption_key.txt
touch secrets/bitpanda_api_key.txt
touch secrets/alpha_vantage_api_key.txt
touch secrets/google_credentials.json
touch secrets/outlook_client_id.txt
touch secrets/outlook_client_secret.txt
touch secrets/github_token.txt

# Set appropriate permissions for secrets
chmod 600 secrets/*
chmod 700 secrets

# Copy environment file
if [ ! -f .env ]; then
    print_status "Creating .env file from template..."
    cp .env.example .env
    print_warning "Please edit .env file with your configuration values"
fi

# Generate secure passwords for databases
print_status "Generating secure database passwords..."
if [ ! -s secrets/postgres_persons_password.txt ]; then
    openssl rand -base64 32 > secrets/postgres_persons_password.txt
fi
if [ ! -s secrets/postgres_org_password.txt ]; then
    openssl rand -base64 32 > secrets/postgres_org_password.txt
fi
if [ ! -s secrets/postgres_medical_password.txt ]; then
    openssl rand -base64 32 > secrets/postgres_medical_password.txt
fi
if [ ! -s secrets/postgres_trading_password.txt ]; then
    openssl rand -base64 32 > secrets/postgres_trading_password.txt
fi
if [ ! -s secrets/medical_encryption_key.txt ]; then
    openssl rand -base64 64 > secrets/medical_encryption_key.txt
fi

# Create Docker networks - Let Docker Compose handle this
# print_status "Creating Docker networks..."
# docker network create jarvis-frontend 2>/dev/null || true
# docker network create jarvis-internal 2>/dev/null || true
# docker network create jarvis-database 2>/dev/null || true
# docker network create jarvis-monitoring 2>/dev/null || true

# Build all Docker images
print_status "Building Docker images..."
$DOCKER_COMPOSE build --parallel

# Create and start containers
print_status "Starting JARVIS containers..."
$DOCKER_COMPOSE up -d

# Wait for databases to be ready
print_status "Waiting for databases to be ready..."
sleep 30

# Run database migrations
print_status "Database migrations skipped - Using direct database initialization..."
# Note: Database users and schemas are created via Docker init scripts
echo "  ℹ️  Database schemas are initialized through Docker entrypoint scripts"

# Health check
print_status "Performing health checks..."
sleep 10

# Check if all services are running
if $DOCKER_COMPOSE ps | grep -q "Up"; then
    print_status "✅ JARVIS Multi-Container setup completed successfully!"
    echo ""
    echo "🌐 Frontend: http://localhost"
    echo "📊 Core API: http://localhost:8000"
    echo "📈 Monitoring: http://localhost:9090"
    echo ""
    print_warning "Important: Please configure your API keys in the secrets/ directory"
    print_warning "Edit the .env file with your specific configuration"
    echo ""
    print_status "To view logs: $DOCKER_COMPOSE logs -f"
    print_status "To stop services: $DOCKER_COMPOSE down"
    print_status "To restart services: $DOCKER_COMPOSE restart"
else
    print_error "Some services failed to start. Check logs with: $DOCKER_COMPOSE logs"
    exit 1
fi

# Display container status
echo ""
print_status "Container Status:"
$DOCKER_COMPOSE ps