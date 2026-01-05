# Integration Worker Service

**Python background worker for CRM and calendar synchronization**

## Overview

The Integration Worker service handles:
- **Calendar Synchronization:** Automatic bidirectional sync with Outlook and Google Calendar
- **Scheduled Background Jobs:** Token refresh, periodic sync, data cleanup
- **Webhook Processing:** Real-time updates from external services
- **CRM Integration:** Sync contacts and cases with legal CRMs (Clio) - Future Phase 4

## Technology Stack

- **Language:** Python 3.11+
- **Task Queue:** Celery 5.3+ (Decision finalized)
- **Message Broker:** Redis 5.0+ (Already in stack)
- **Database:** PostgreSQL (shared with api-core)
- **Integrations:** Microsoft Graph API, Google Calendar API, Clio API (future)

## Status

📋 **Planning Complete** - Implementation ready to begin

## Documentation

- **[Implementation Plan](/docs/integration-worker/impl-plan.md)** - Comprehensive implementation guide
- **[System Design](/docs/design/system-design.md)** - Overall architecture
- **[Outlook Calendar Integration](/docs/connection/OUTLOOK_CALENDAR_INTEGRATION.md)** - Existing calendar integration

## Key Features

### Automatic Calendar Sync
- Scheduled sync every 15 minutes via Celery Beat
- Manual sync trigger via API endpoint
- Real-time updates via Microsoft Graph webhooks
- Token auto-refresh before expiration

### Background Task Processing
- Celery worker for async task execution
- Retry logic with exponential backoff
- Error handling and logging
- Task monitoring and metrics

### Calendar Integration Migration
- Move sync logic from api-core to integration-worker
- Keep OAuth flow in api-core (user-facing)
- Background processing in integration-worker

## Project Structure

```
apps/integration-worker/
├── src/integration_worker/
│   ├── celery_app.py         # Celery application and config
│   ├── config.py              # Configuration management
│   ├── tasks/                 # Celery tasks
│   │   ├── calendar_sync.py
│   │   ├── token_refresh.py
│   │   └── webhook_processing.py
│   ├── services/              # Business logic
│   │   ├── outlook_service.py
│   │   ├── google_service.py
│   │   └── sync_service.py
│   ├── clients/               # External API clients
│   │   ├── api_core_client.py
│   │   ├── graph_client.py
│   │   └── google_client.py
│   └── workers/               # Webhook handlers
│       └── webhook_server.py
└── tests/                     # Test suite
```

## Quick Start

(Will be added during implementation)

## Next Steps

See [Implementation Plan](/docs/integration-worker/impl-plan.md) for detailed roadmap:

1. **Phase 1:** Foundation & Setup (Week 1)
2. **Phase 2:** Calendar Sync Migration (Week 2)
3. **Phase 3:** Scheduled Background Jobs (Week 3)
4. **Phase 4:** Webhook Subscriptions (Week 4)
5. **Phase 5:** Google Calendar Integration (Week 5-6)
6. **Phase 6:** Production Deployment (Week 7)

