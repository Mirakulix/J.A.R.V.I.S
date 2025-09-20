# JARVIS Multi-Container Development Makefile
# Automatically detects system commands and uses appropriate versions

# Color codes for output
RED := \033[0;31m
GREEN := \033[0;32m
YELLOW := \033[1;33m
BLUE := \033[0;34m
NC := \033[0m # No Color

# Detect Docker Compose command
DOCKER_COMPOSE := $(shell which docker-compose 2>/dev/null)
ifndef DOCKER_COMPOSE
	DOCKER_COMPOSE := docker compose
endif

# Detect Python command
PYTHON := $(shell which python3 2>/dev/null)
ifndef PYTHON
	PYTHON := python
endif

# Detect system architecture for Docker buildx
ARCH := $(shell uname -m)
ifeq ($(ARCH),arm64)
	PLATFORM := --platform linux/arm64
else ifeq ($(ARCH),aarch64)
	PLATFORM := --platform linux/arm64
else
	PLATFORM := --platform linux/amd64
endif

# Default target
.PHONY: dev
dev: banner setup build up

# Development environment setup and start
.PHONY: banner
banner:
	@echo "$(BLUE)"
	@echo "     ██╗     █████╗     ██████╗      ██╗   ██╗    ██╗    ███████╗"
	@echo "     ██║    ██╔══██╗    ██╔══██╗     ██║   ██║    ██║    ██╔════╝"
	@echo "     ██║    ███████║    ██████╔╝     ██║   ██║    ██║    ███████╗"
	@echo "██   ██║    ██╔══██║    ██╔══██╗     ╚██╗ ██╔╝    ██║    ╚════██║"
	@echo "╚█████╔╝ ██ ██║  ██║ ██ ██║  ██║  ██  ╚████╔╝  ██ ██║ ██ ███████║"
	@echo " ╚════╝  ╚═ ╚═╝  ╚═╝ ╚═ ╚═╝  ╚═╝  ╚═   ╚═══╝   ╚═ ╚═╝ ╚═ ╚══════╝"
	@echo "$(NC)"
	@echo "$(GREEN)🤖 JARVIS Multi-Container Development Environment$(NC)"
	@echo "$(YELLOW)Using Docker Compose: $(DOCKER_COMPOSE)$(NC)"
	@echo "$(YELLOW)Using Python: $(PYTHON)$(NC)"
	@echo "$(YELLOW)Platform: $(PLATFORM)$(NC)"
	@echo ""

# Setup directories and permissions
.PHONY: setup
setup:
	@echo "$(GREEN)📁 Setting up directories and permissions...$(NC)"
	@chmod +x scripts/setup-jarvis.sh
	@mkdir -p secrets logs backups nginx/ssl
	@mkdir -p database/{personendb,organisationdb,medizindb,temporarydb,vectordb,tradingdb}/{init,migrations,backup}
	@mkdir -p docker/android-config scripts/android-automation
	@chmod +x docker/android-healthcheck.sh docker/android-config/adb-setup.sh
	@chmod +x docker/android-automation-server.py docker/android-monitor.py
	@touch secrets/.gitkeep logs/.gitkeep backups/.gitkeep
	@echo "$(GREEN)✅ Directory setup completed$(NC)"

# Build all containers
.PHONY: build
build:
	@echo "$(GREEN)🔨 Building Docker containers...$(NC)"
	@$(DOCKER_COMPOSE) build --parallel

# Build specific service
.PHONY: build-%
build-%:
	@echo "$(GREEN)🔨 Building $* container...$(NC)"
	@$(DOCKER_COMPOSE) build $*

# Start all services
.PHONY: up
up:
	@echo "$(GREEN)🚀 Starting JARVIS containers...$(NC)"
	@$(DOCKER_COMPOSE) up -d
	@echo "$(GREEN)✅ All services started!$(NC)"
	@echo ""
	@echo "$(BLUE)🌐 Access Points:$(NC)"
	@echo "$(YELLOW)Frontend:           http://localhost$(NC)"
	@echo "$(YELLOW)Core API:           http://localhost:8000$(NC)"
	@echo "$(YELLOW)Android VNC:        http://localhost:6080$(NC)"
	@echo "$(YELLOW)Android API:        http://localhost:8081$(NC)"
	@echo "$(YELLOW)Monitoring:         http://localhost:9090$(NC)"
	@echo "$(YELLOW)Android Metrics:    http://localhost:9091$(NC)"

# Start specific service
.PHONY: up-%
up-%:
	@echo "$(GREEN)🚀 Starting $* service...$(NC)"
	@$(DOCKER_COMPOSE) up -d $*

# Stop all services
.PHONY: down
down:
	@echo "$(YELLOW)🛑 Stopping JARVIS containers...$(NC)"
	@$(DOCKER_COMPOSE) down

# Stop and remove all containers, networks, and volumes
.PHONY: clean
clean:
	@echo "$(RED)🧹 Cleaning up containers, networks, and volumes...$(NC)"
	@$(DOCKER_COMPOSE) down -v --remove-orphans
	@docker system prune -f

# Restart all services
.PHONY: restart
restart: down up

# View logs for all services
.PHONY: logs
logs:
	@$(DOCKER_COMPOSE) logs -f

# View logs for specific service
.PHONY: logs-%
logs-%:
	@$(DOCKER_COMPOSE) logs -f $*

# Show status of all services
.PHONY: status
status:
	@echo "$(BLUE)📊 JARVIS Container Status:$(NC)"
	@$(DOCKER_COMPOSE) ps

# Health check for all services
.PHONY: health
health:
	@echo "$(BLUE)🏥 Health Check Status:$(NC)"
	@docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | grep jarvis

# Execute shell in specific container
.PHONY: shell-%
shell-%:
	@echo "$(GREEN)🐚 Opening shell in $* container...$(NC)"
	@$(DOCKER_COMPOSE) exec $* /bin/bash

# Android emulator specific commands
.PHONY: android-shell
android-shell:
	@echo "$(GREEN)🤖 Opening shell in Android container...$(NC)"
	@$(DOCKER_COMPOSE) exec jarvis-android /bin/bash

.PHONY: android-vnc
android-vnc:
	@echo "$(GREEN)🖥️  Opening Android VNC in browser...$(NC)"
	@$(PYTHON) -c "import webbrowser; webbrowser.open('http://localhost:6080')"

.PHONY: android-status
android-status:
	@echo "$(BLUE)📱 Android Emulator Status:$(NC)"
	@$(DOCKER_COMPOSE) exec jarvis-android adb devices

# Database operations
.PHONY: db-backup
db-backup:
	@echo "$(GREEN)💾 Creating database backups...$(NC)"
	@$(DOCKER_COMPOSE) exec jarvis-personendb pg_dump -U jarvis_persons personendb > backups/personendb_$(shell date +%Y%m%d_%H%M%S).sql
	@$(DOCKER_COMPOSE) exec jarvis-organisationdb pg_dump -U jarvis_org organisationdb > backups/organisationdb_$(shell date +%Y%m%d_%H%M%S).sql
	@$(DOCKER_COMPOSE) exec jarvis-medizindb pg_dump -U jarvis_medical medizindb > backups/medizindb_$(shell date +%Y%m%d_%H%M%S).sql
	@$(DOCKER_COMPOSE) exec jarvis-tradingdb pg_dump -U jarvis_trading tradingdb > backups/tradingdb_$(shell date +%Y%m%d_%H%M%S).sql
	@echo "$(GREEN)✅ Database backups completed$(NC)"

# Development tools
.PHONY: test
test:
	@echo "$(GREEN)🧪 Running tests...$(NC)"
	@$(DOCKER_COMPOSE) exec jarvis-test $(PYTHON) -m pytest -v

.PHONY: lint
lint:
	@echo "$(GREEN)🔍 Running code linting...$(NC)"
	@$(PYTHON) -m black --check .
	@$(PYTHON) -m flake8 .

.PHONY: format
format:
	@echo "$(GREEN)✨ Formatting code...$(NC)"
	@$(PYTHON) -m black .

# Monitoring and debugging
.PHONY: monitor
monitor:
	@echo "$(GREEN)📊 Opening monitoring dashboard...$(NC)"
	@$(PYTHON) -c "import webbrowser; webbrowser.open('http://localhost:9090')"

.PHONY: debug
debug:
	@echo "$(BLUE)🐛 Debug Information:$(NC)"
	@echo "$(YELLOW)Docker version:$(NC)"
	@docker --version
	@echo "$(YELLOW)Docker Compose version:$(NC)"
	@$(DOCKER_COMPOSE) --version
	@echo "$(YELLOW)Python version:$(NC)"
	@$(PYTHON) --version
	@echo "$(YELLOW)System info:$(NC)"
	@uname -a
	@echo "$(YELLOW)Available memory:$(NC)"
	@free -h 2>/dev/null || echo "Memory info not available"

# Installation and setup
.PHONY: install
install:
	@echo "$(GREEN)📦 Installing JARVIS...$(NC)"
	@./scripts/setup-jarvis.sh

# Full development cycle
.PHONY: dev-full
dev-full: clean setup install build up

# Quick development restart
.PHONY: dev-quick
dev-quick: down build up

# Production deployment
.PHONY: prod
prod:
	@echo "$(GREEN)🚀 Starting JARVIS in production mode...$(NC)"
	@$(DOCKER_COMPOSE) -f docker-compose.yml -f docker-compose.prod.yml up -d

# Show environment info
.PHONY: env
env:
	@echo "$(BLUE)🌍 Environment Information:$(NC)"
	@echo "$(YELLOW)Docker Compose Command: $(DOCKER_COMPOSE)$(NC)"
	@echo "$(YELLOW)Python Command: $(PYTHON)$(NC)"
	@echo "$(YELLOW)Platform: $(PLATFORM)$(NC)"
	@echo "$(YELLOW)Architecture: $(ARCH)$(NC)"
	@echo "$(YELLOW)Working Directory: $(PWD)$(NC)"

# Help
.PHONY: help
help:
	@echo "$(BLUE)JARVIS Development Makefile$(NC)"
	@echo ""
	@echo "$(GREEN)Main Commands:$(NC)"
	@echo "  $(YELLOW)make dev$(NC)          - Setup and start development environment (default)"
	@echo "  $(YELLOW)make dev-full$(NC)     - Full clean setup and start"
	@echo "  $(YELLOW)make dev-quick$(NC)    - Quick restart for development"
	@echo ""
	@echo "$(GREEN)Container Management:$(NC)"
	@echo "  $(YELLOW)make build$(NC)        - Build all containers"
	@echo "  $(YELLOW)make build-SERVICE$(NC) - Build specific service"
	@echo "  $(YELLOW)make up$(NC)           - Start all services"
	@echo "  $(YELLOW)make up-SERVICE$(NC)   - Start specific service"
	@echo "  $(YELLOW)make down$(NC)         - Stop all services"
	@echo "  $(YELLOW)make restart$(NC)      - Restart all services"
	@echo "  $(YELLOW)make clean$(NC)        - Clean up everything"
	@echo ""
	@echo "$(GREEN)Monitoring & Debugging:$(NC)"
	@echo "  $(YELLOW)make status$(NC)       - Show container status"
	@echo "  $(YELLOW)make health$(NC)       - Health check"
	@echo "  $(YELLOW)make logs$(NC)         - View all logs"
	@echo "  $(YELLOW)make logs-SERVICE$(NC) - View specific service logs"
	@echo "  $(YELLOW)make shell-SERVICE$(NC) - Open shell in container"
	@echo "  $(YELLOW)make monitor$(NC)      - Open monitoring dashboard"
	@echo "  $(YELLOW)make debug$(NC)        - Show debug information"
	@echo ""
	@echo "$(GREEN)Android Specific:$(NC)"
	@echo "  $(YELLOW)make android-shell$(NC) - Open Android container shell"
	@echo "  $(YELLOW)make android-vnc$(NC)   - Open Android VNC interface"
	@echo "  $(YELLOW)make android-status$(NC) - Check Android emulator status"
	@echo ""
	@echo "$(GREEN)Database Operations:$(NC)"
	@echo "  $(YELLOW)make db-backup$(NC)    - Backup all databases"
	@echo ""
	@echo "$(GREEN)Development Tools:$(NC)"
	@echo "  $(YELLOW)make test$(NC)         - Run tests"
	@echo "  $(YELLOW)make lint$(NC)         - Run code linting"
	@echo "  $(YELLOW)make format$(NC)       - Format code"
	@echo ""
	@echo "$(GREEN)System:$(NC)"
	@echo "  $(YELLOW)make install$(NC)      - Run installation script"
	@echo "  $(YELLOW)make env$(NC)          - Show environment info"
	@echo "  $(YELLOW)make help$(NC)         - Show this help"

# Default target if no target is specified
.DEFAULT_GOAL := dev