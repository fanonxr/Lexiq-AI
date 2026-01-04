# Long-Term Memory Implementation Guide

This guide explains how to use the Long-Term Memory (Client Context) feature in the cognitive-orchestrator service.

## Overview

The Long-Term Memory feature enables the AI to recognize returning callers and personalize interactions based on their past conversations. When a user calls, we:

1. **Identify** them by phone number
2. **Retrieve** their interaction history (dossier)
3. **Inject** that context into the LLM's system prompt
4. **Generate** and store a summary after the call ends

## Architecture

```
┌─────────────┐     ┌──────────────────┐     ┌─────────────┐
│ Voice       │────▶│ Cognitive Orch   │────▶│ PostgreSQL  │
│ Gateway     │     │ (Memory Service) │     │ (Clients)   │
└─────────────┘     └──────────────────┘     └─────────────┘
                             │
                             ▼
                    ┌──────────────────┐
                    │ Prompt Builder   │
                    │ (with dossier)   │
                    └──────────────────┘
                             │
                             ▼
                    ┌──────────────────┐
                    │ LLM (GPT-4)      │
                    │ (personalized)   │
                    └──────────────────┘
                             │
                             ▼ (after call)
                    ┌──────────────────┐
                    │ Post-Call Worker │
                    │ (summarization)  │
                    └──────────────────┘
```

## Database Schema

### Clients Table
Stores caller information indexed by phone number for fast lookup.

```sql
CREATE TABLE clients (
    id UUID PRIMARY KEY,
    firm_id UUID NOT NULL REFERENCES firms(id) ON DELETE CASCADE,
    phone_number VARCHAR(20) NOT NULL,
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    last_called_at TIMESTAMP WITH TIME ZONE NOT NULL,
    UNIQUE (firm_id, phone_number)
);

CREATE INDEX idx_clients_phone ON clients(phone_number);
CREATE INDEX idx_clients_firm_phone ON clients(firm_id, phone_number);
```

### ClientMemory Table
Stores conversation summaries with embeddings for semantic search.

```sql
CREATE TABLE client_memories (
    id UUID PRIMARY KEY,
    client_id UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    summary_text TEXT NOT NULL,
    embedding TEXT,  -- JSON array (future: VECTOR(1536) with pgvector)
    created_at TIMESTAMP WITH TIME ZONE NOT NULL
);

CREATE INDEX idx_client_memories_client_created ON client_memories(client_id, created_at DESC);
```

## Setup

### 1. Database Migration

Run the Alembic migration to create the tables:

```bash
cd apps/api-core
alembic upgrade head
```

### 2. Environment Configuration

Add to your `.env` file in `apps/cognitive-orch/`:

```env
# Database (same credentials as api-core)
DATABASE_URL=postgresql+asyncpg://postgres:password@localhost:5432/lexiq

# Azure OpenAI (for embeddings)
AZURE_API_KEY=your_key_here
AZURE_API_BASE=https://your-resource.openai.azure.com
AZURE_API_VERSION=2024-02-15-preview
```

### 3. Install Dependencies

```bash
cd apps/cognitive-orch
pip install -r requirements.txt
```

The new dependencies added:
- `sqlalchemy==2.0.23` - ORM for database operations
- `asyncpg==0.29.0` - Async PostgreSQL driver

## Usage

### During Call Initiation

```python
from cognitive_orch.services.memory_service import MemoryService
from cognitive_orch.services.prompt_builder import build_system_prompt

# 1. Identify the client
memory_service = MemoryService()
client = await memory_service.identify_client(
    firm_id="firm-uuid",
    phone_number="+15551234567"
)

# 2. Get their interaction history
dossier = await memory_service.get_client_dossier(client.id)

# 3. Build personalized system prompt
firm_persona = "You are a receptionist for Smith & Associates Law Firm..."
system_prompt = build_system_prompt(
    firm_persona=firm_persona,
    client_dossier=dossier,
    include_tool_instructions=True
)

# 4. Use system_prompt in your LLM call
response = await llm_service.generate_response(
    messages=[{"role": "system", "content": system_prompt}, ...],
    ...
)
```

### After Call Completion

```python
from cognitive_orch.services.post_call_worker import generate_memory

# Generate and store memory
transcript = "... full conversation transcript ..."
summary = await generate_memory(
    call_transcript=transcript,
    client_id=client.id,
    include_embedding=True
)

print(f"Generated summary: {summary}")
```

### Updating Client Information

```python
# Update name when learned during conversation
await memory_service.update_client_name(
    client_id=client.id,
    first_name="John",
    last_name="Smith"
)
```

## API Reference

### MemoryService

#### `identify_client(firm_id, phone_number) -> Client`
Identifies or creates a client by phone number.

**Parameters:**
- `firm_id` (str): Firm UUID
- `phone_number` (str): Phone number (E.164 format recommended)

**Returns:** `Client` object

**Example:**
```python
client = await memory_service.identify_client(
    firm_id="abc-123",
    phone_number="+15551234567"
)
print(f"Client ID: {client.id}, Last call: {client.last_called_at}")
```

#### `get_client_dossier(client_id, max_memories=3) -> Optional[str]`
Retrieves formatted interaction history.

**Parameters:**
- `client_id` (str): Client UUID
- `max_memories` (int): Max memories to include (default: 3)

**Returns:** Formatted dossier string or None if no memories

**Example:**
```python
dossier = await memory_service.get_client_dossier(client.id)
# Output:
# - [2 days ago]: Called about divorce case. Scheduled consultation.
# - [1 week ago]: Initial inquiry about family law services.
```

#### `store_memory(client_id, summary_text, embedding=None) -> ClientMemory`
Stores a new memory for a client.

**Parameters:**
- `client_id` (str): Client UUID
- `summary_text` (str): Summary text
- `embedding` (List[float], optional): Embedding vector

**Returns:** Created `ClientMemory` object

#### `update_client_name(client_id, first_name=None, last_name=None) -> None`
Updates a client's name.

**Parameters:**
- `client_id` (str): Client UUID
- `first_name` (str, optional): First name
- `last_name` (str, optional): Last name

### PostCallWorker

#### `generate_memory(call_transcript, client_id, include_embedding=True) -> str`
Generates and stores a memory from a call transcript.

**Parameters:**
- `call_transcript` (str): Full conversation transcript
- `client_id` (str): Client UUID
- `include_embedding` (bool): Generate embeddings (default: True)

**Returns:** Generated summary text

**Example:**
```python
summary = await generate_memory(
    call_transcript="User: Hi, I need help with...\nAI: Of course...",
    client_id="client-uuid"
)
```

### PromptBuilder

#### `build_system_prompt(firm_persona, client_dossier=None, include_tool_instructions=False) -> str`
Builds a complete system prompt with optional client context.

**Parameters:**
- `firm_persona` (str): Firm's system prompt
- `client_dossier` (str, optional): Client history from `get_client_dossier()`
- `include_tool_instructions` (bool): Add tool usage instructions

**Returns:** Complete system prompt

**Example:**
```python
prompt = build_system_prompt(
    firm_persona="You are a helpful receptionist...",
    client_dossier=dossier,
    include_tool_instructions=True
)
```

## Integration Points

### gRPC Handler Integration

In your gRPC conversation handler:

```python
from cognitive_orch.services.memory_service import MemoryService
from cognitive_orch.services.prompt_builder import build_system_prompt

async def handle_conversation(request):
    # Extract call details
    firm_id = request.firm_id
    from_number = request.from_number
    
    # Identify client
    memory_service = MemoryService()
    client = await memory_service.identify_client(firm_id, from_number)
    
    # Get dossier
    dossier = await memory_service.get_client_dossier(client.id)
    
    # Build prompt
    firm_persona = await get_firm_persona(firm_id)  # Your existing logic
    system_prompt = build_system_prompt(firm_persona, dossier)
    
    # Continue with conversation...
    return conversation_response
```

### Post-Call Processing

After a call ends (via webhook, event, or background task):

```python
from cognitive_orch.services.post_call_worker import generate_memory

async def on_call_ended(call_id: str):
    # Get call details
    call = await get_call_details(call_id)
    
    # Get client
    memory_service = MemoryService()
    client = await memory_service.identify_client(
        call.firm_id, 
        call.from_number
    )
    
    # Generate memory
    if call.transcript:
        await generate_memory(
            call_transcript=call.transcript,
            client_id=client.id
        )
```

## Performance Considerations

### Database Queries
- Client lookup: Indexed on `(firm_id, phone_number)` - O(1) lookup
- Dossier retrieval: Indexed on `(client_id, created_at DESC)` - Fast for recent memories
- Limit dossiers to 3 memories to keep prompts concise

### Embedding Generation
- Post-call processing is async - doesn't block call flow
- Uses Azure OpenAI text-embedding-ada-002 (1536 dimensions)
- Cost: ~$0.0001 per 1K tokens

### Memory Management
- Consider archiving old memories (>6 months) to separate table
- Implement memory pruning if client has >50 memories
- Future: Use semantic search for selecting most relevant memories

## Testing

### Unit Tests

```python
import pytest
from cognitive_orch.services.memory_service import MemoryService

@pytest.mark.asyncio
async def test_identify_new_client():
    service = MemoryService()
    client = await service.identify_client("firm-1", "+15551234567")
    assert client.id is not None
    assert client.phone_number == "+15551234567"

@pytest.mark.asyncio
async def test_get_dossier():
    service = MemoryService()
    # Create test client and memories...
    dossier = await service.get_client_dossier(client_id)
    assert "days ago" in dossier
```

### Integration Test

```bash
# Start services
docker-compose up -d postgres redis

# Run migration
cd apps/api-core
alembic upgrade head

# Test end-to-end
cd apps/cognitive-orch
pytest tests/integration/test_memory_flow.py -v
```

## Troubleshooting

### "Could not import models from api_core"

Ensure api-core is in your Python path:

```bash
export PYTHONPATH="/path/to/lexiq-ai/apps/api-core/src:$PYTHONPATH"
```

Or install api-core as editable package:

```bash
cd apps/api-core
pip install -e .
```

### "relation 'clients' does not exist"

Run the database migration:

```bash
cd apps/api-core
alembic upgrade head
```

### Embeddings failing

Check your Azure OpenAI configuration:

```python
from cognitive_orch.config import get_settings
settings = get_settings()
print(f"Azure API Base: {settings.llm.azure_api_base}")
print(f"Azure API Key: {'✓' if settings.llm.azure_api_key else '✗'}")
```

## Future Enhancements

### Phase 2: Semantic Search
- Install pgvector extension for PostgreSQL
- Store embeddings as `VECTOR(1536)` instead of JSON
- Use vector similarity search to find relevant memories
- Support longer conversation histories (10+ interactions)

### Phase 3: Memory Types
- Distinguish between call summaries, actions, preferences
- Different retention policies per type
- Support manual notes from firm staff

### Phase 4: Memory Sharing
- Allow firms to mark memories as "shareable" across staff
- Support memory tagging and categorization
- Implement memory privacy controls

## Support

For issues or questions:
1. Check logs: `docker-compose logs cognitive-orch`
2. Review implementation plan: `docs/converstaion-memory/long-memory-plan.md`
3. Contact the backend team

## References

- [SQLAlchemy Async Documentation](https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html)
- [LiteLLM Embeddings](https://docs.litellm.ai/docs/embedding/supported_embedding)
- [PostgreSQL pgvector](https://github.com/pgvector/pgvector)

