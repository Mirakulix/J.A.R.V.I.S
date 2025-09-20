# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

J.A.R.V.I.S. is a sophisticated multi-container AI development environment that replicates the Marvel Cinematic Universe's J.A.R.V.I.S. AI assistant. The system combines multiple AI models, orchestration frameworks, and specialized services into a cohesive platform capable of autonomous software development, testing, and deployment.

**Core Architecture:**
1. **12 Specialized Docker Containers** - Microservices architecture with isolated responsibilities
2. **Multi-Agent AI Framework** - AutoGen-based agent orchestration with hierarchical collaboration
3. **Skills System** - 22+ modular AI capabilities in JSON/YAML format
4. **Android Automation** - Containerized Android emulator with AI-powered testing
5. **Claude Code Integration** - Native support for AI-assisted development workflows
6. **Comprehensive Monitoring** - Prometheus metrics, health checks, and log aggregation

## Development Commands

### Primary Development Workflow
```bash
# Full development environment setup (recommended)
make dev

# Quick restart for iterative development
make dev-quick

# Full clean setup (use when containers are corrupted)
make dev-full
```

### Container Management
```bash
# Build specific services
make build-jarvis-core
make build-jarvis-android

# View container status and logs
make status
make logs
make logs-jarvis-core

# Access container shells
make shell-jarvis-core
make android-shell
```

### Database Operations
```bash
# Backup all databases
make db-backup

# The system automatically creates these databases:
# - jarvis-personendb (Personal data)
# - jarvis-organisationdb (Organizational data) 
# - jarvis-medizindb (Medical data with GDPR compliance)
# - jarvis-tradingdb (Financial data)
# - jarvis-vectordb (ChromaDB for embeddings)
# - jarvis-temporarydb (Auto-cleanup temporary data)
```

### Development Tools
```bash
# Run tests across all services
make test

# Code linting and formatting
make lint
make format

# Health monitoring
make health
make monitor  # Opens Prometheus dashboard at localhost:9090
```

### Android Automation
```bash
# Access Android emulator interface
make android-vnc    # Opens VNC at localhost:6080

# Check Android emulator status
make android-status

# Android automation runs on:
# - Port 4723: Appium Server
# - Port 8081: Android Automation API
# - Port 9091: Android Performance Metrics
```

## Architecture Overview

### Multi-Container System Design

**Application Services:**
- `jarvis-frontend` (Port 8080) - Web interface for user interactions
- `jarvis-core` (Port 8000, gRPC 50051) - Central orchestration hub
- `jarvis-connector` - External service integrations (Google, Outlook, 1Password)
- `jarvis-functions` - Scalable function execution (3 replicas with auto-scaling)
- `jarvis-code` - AI-powered code development with Claude Code integration
- `jarvis-test` - Automated testing and validation framework
- `jarvis-monitor` (Port 9090) - Prometheus-based system monitoring
- `jarvis-android` - Android emulator with AI automation capabilities

**Data Layer:**
- PostgreSQL databases for different data domains (persons, organization, medical, trading)
- ChromaDB for vector embeddings and semantic search
- Redis for caching and session management
- Comprehensive backup and migration systems

**Network Architecture:**
- `jarvis-frontend` - Public-facing network for web interface
- `jarvis-internal` - Inter-service communication network
- `jarvis-database` - Isolated database network (internal only)
- `jarvis-monitoring` - Metrics and logging network

### Skills System Architecture

The system includes 22+ predefined AI capabilities organized by complexity:

**Simple Skills:** Email, calendar, weather, file operations, password generation
**Complex Skills:** Multi-agent development, crypto trading, Android automation, smart home integration

Skills are defined in `/skills/` with standardized schemas including:
- Input validation and type checking
- Output specifications and error handling
- Security controls (rate limiting, API key management)
- Category classification and complexity scoring

### Multi-Agent Development Framework

The system uses AutoGen for sophisticated agent collaboration:

**Agent Hierarchy:**
- **Admin** (Level 10): Human oversight and final approval authority
- **Architect** (Level 9): System design and architectural decisions
- **Senior Engineer** (Level 8): Complex implementation and mentoring
- **Engineer** (Level 7): Core development and code implementation
- **Developer** (Level 6): Feature development and integration
- **Junior Developer** (Level 5): Basic coding and bug fixes
- **Tester** (Level 4): Quality assurance and validation
- **Reviewer** (Level 3): Code review and feedback
- **Assistant** (Level 2): Documentation and support tasks
- **Intern** (Level 1): Learning and simple tasks

**Collaboration Features:**
- Negotiation-based conflict resolution
- Knowledge base updates and learning
- Automated testing and validation
- Continuous integration with git workflows

## Environment Configuration

### Required Environment Variables
Environment variables are managed through `/secrets/` files and `.env`:

**Database Passwords:** Set in `.env` and injected as Docker secrets
**API Keys:** Stored in individual files under `/secrets/`
- `claude_code_api_key.txt` - For Claude Code integration
- `onepassword_token.txt` - 1Password service account
- `google_credentials.json` - Google API access
- `github_token.txt` - GitHub integration
- `bitpanda_api_key.txt` - Crypto trading API
- `alpha_vantage_api_key.txt` - Stock market data

### Security Architecture
- **Secrets Management:** File-based secret injection with 600 permissions
- **Network Isolation:** Internal database network with no external access
- **Container Security:** Non-root users, read-only filesystems where applicable
- **GDPR Compliance:** Encrypted medical data with audit logging
- **Rate Limiting:** API protection and abuse prevention

## Development Patterns

### Adding New Services
1. Create Dockerfile in `/docker/Dockerfile.<service-name>`
2. Add service definition to `docker-compose.yml`
3. Configure appropriate networks and dependencies
4. Add health checks and resource limits
5. Update Makefile with service-specific commands

### Skills Development
1. Define skill schema in `/skills/json/` or `/skills/yaml/`
2. Include comprehensive input validation
3. Implement error handling and security controls
4. Add to appropriate complexity category
5. Test with the skills validation framework

### Multi-Agent Workflows
1. Define agent roles and authority levels
2. Implement negotiation protocols for conflicts
3. Add automated testing and validation
4. Integrate with git workflow for code changes
5. Monitor through the observability stack

### Android Automation
The system provides sophisticated Android testing capabilities:
- **Appium Integration:** Full mobile app testing framework
- **AI-Powered Interactions:** OpenAI and Google Vision integration
- **Real-time Monitoring:** Performance metrics and health checks
- **VNC Access:** Visual debugging through web interface
- **Automated Documentation:** Screenshot and video capture

## Monitoring and Observability

The system includes comprehensive monitoring:
- **Prometheus Metrics:** System performance and health indicators
- **Health Checks:** Automated failure detection across all services
- **Log Aggregation:** Centralized logging with structured formats
- **Performance Analytics:** Resource utilization and bottleneck identification
- **Alert Management:** Automated notifications for critical issues

Access monitoring dashboard: `make monitor` (opens localhost:9090)

## Claude Code Integration

This repository is specifically designed to work with Claude Code:
- **Native Support:** Built-in Claude Code service container
- **Git Workflows:** Automated commit and branch management
- **Code Analysis:** Integration with the vector database for semantic search
- **Multi-Agent Collaboration:** Claude Code works alongside other AI agents
- **Security Boundaries:** Safe execution environments with proper isolation

The system leverages Claude Code's capabilities for autonomous development while maintaining enterprise-grade security and monitoring.