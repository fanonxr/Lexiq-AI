# LexiqAI

**Enterprise-grade voice orchestration platform for the legal industry**

LexiqAI is a SaaS platform that enables law firms to deploy AI assistants that can answer calls, manage schedules, book appointments, and integrate with legal CRMs and calendars.

## 🏗️ Architecture

LexiqAI is built as an **Event-Driven Microservices** platform on **Microsoft Azure**, with strict separation between:
- **Voice Edge** (high-concurrency audio processing)
- **Cognitive Core** (LLM reasoning and RAG)

### Core Services

- **Voice Gateway** (Go) - Handles Twilio WebSocket connections and audio streaming
- **Cognitive Orchestrator** (Python/FastAPI) - Manages conversation state, RAG, and LLM routing
- **API Core** (Python/FastAPI) - User authentication, billing, and dashboard APIs
- **Integration Worker** (Python) - Async sync with Clio CRM and calendars
- **Web Frontend** (Next.js 14) - Unified marketing site and SaaS dashboard

## 🚀 Quick Start

### Prerequisites

- Node.js 18+ and npm/yarn/pnpm
- Docker and Docker Compose
- Azure CLI (for infrastructure)
- Terraform 1.5+ (for infrastructure)
- Go 1.21+ (for voice-gateway)
- Python 3.11+ (for Python services)

### Local Development Setup

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd lexiq-ai
   ```

2. **Start local dependencies**
   ```bash
   make docker-up
   ```
   This starts PostgreSQL (with pgvector) and Redis in Docker containers.

3. **Set up environment variables**
   ```bash
   cp apps/web-frontend/.env.example apps/web-frontend/.env.local
   # Edit .env.local with your configuration
   ```

4. **Start the frontend**
   ```bash
   cd apps/web-frontend
   npm install
   npm run dev
   ```

5. **Access the application**
   - Frontend: http://localhost:3000
   - PostgreSQL: localhost:5432
   - Redis: localhost:6379

For detailed setup instructions, see [Foundation Documentation](/docs/foundation/).

## 📁 Project Structure

```
/lexiq-ai
├── apps/                    # Deployable microservices
│   ├── web-frontend/        # Next.js 14 (Marketing + App)
│   ├── voice-gateway/       # Go (Twilio WebSockets)
│   ├── cognitive-orch/      # Python FastAPI (The Brain + RAG)
│   ├── api-core/            # Python FastAPI (Auth, Users, Billing)
│   └── integration-worker/  # Python (Celery/Temporal for Sync)
├── libs/                    # Shared code
│   ├── database/            # SQLAlchemy Models & Alembic Migrations
│   ├── proto/               # gRPC definitions
│   └── py-common/           # Shared Azure Auth, Logging
├── infra/                   # Infrastructure as Code
│   └── terraform/           # Terraform configurations
├── tools/                   # Development scripts
├── docker/                  # Base Dockerfiles
└── docs/                    # Documentation
    ├── design/              # System design documents
    └── foundation/          # Foundation phase documentation
```

## 🛠️ Development

### Common Commands

```bash
# Start local services (PostgreSQL, Redis)
make docker-up

# Stop local services
make docker-down

# View logs
make docker-logs

# Run tests
make test

# Format code
make format

# Lint code
make lint
```

See [Makefile](./Makefile) for all available commands.

## 📚 Documentation

- [System Design](/docs/design/system-design.md) - Complete architecture overview
- [Foundation Phase Plan](/docs/foundation/phase-1-plan.md) - Detailed implementation plan
- [Local Development Guide](/docs/foundation/local-development.md) - Local setup instructions
- [Azure Setup Guide](/docs/foundation/azure-setup.md) - Azure infrastructure setup

## 🔒 Security & Compliance

- **Identity:** Microsoft Entra External ID (Azure AD B2C)
- **Network:** Private VNet with isolated subnets
- **Data:** Encryption at rest (AES-256) and in transit (TLS 1.2+)
- **Secrets:** Zero-trust architecture with Azure Managed Identities

## 🏢 Infrastructure

Infrastructure is managed entirely through **Terraform** (Infrastructure as Code). All Azure resources are provisioned and managed via Terraform to prevent configuration drift.

- **Cloud Provider:** Microsoft Azure
- **Compute:** Azure Container Apps
- **Database:** Azure Database for PostgreSQL (with pgvector)
- **Cache:** Azure Cache for Redis
- **Identity:** Azure Managed Identities

## 📋 Implementation Status

- [x] **Phase 1: Foundation** - Infrastructure and local development environment
- [ ] **Phase 2: Core Voice & Auth** - Frontend auth, Voice Gateway, basic echo
- [ ] **Phase 3: Intelligence & RAG** - Orchestrator, pgvector, LLM integration
- [ ] **Phase 4: Integrations & Release** - Calendar sync, dashboard, security audit

## 🤝 Contributing

See [CONTRIBUTING.md](./CONTRIBUTING.md) for development workflow and contribution guidelines.

## 📄 License

[Add license information]

## 🔗 Links

- [System Design Document](/docs/design/system-design.md)
- [Foundation Plan](/docs/foundation/phase-1-plan.md)

---

**Built with ❤️ for the legal industry**

