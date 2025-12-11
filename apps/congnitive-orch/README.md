# Cognitive Orchestrator Service

**Python FastAPI service - The Brain of LexiqAI**

## Overview

The Cognitive Orchestrator service handles:
- Conversation state management
- RAG (Retrieval-Augmented Generation) - Vector search in PostgreSQL
- LLM routing (Azure OpenAI GPT-4o vs Llama 3 based on complexity)
- Context persistence in Redis
- Tool execution and function calling

## Technology Stack

- **Framework:** FastAPI
- **Language:** Python 3.11+
- **Vector Store:** PostgreSQL with pgvector extension
- **Cache:** Redis for conversation state
- **LLM:** Azure OpenAI (GPT-4o), Llama 3
- **Communication:** gRPC (from Voice Gateway)

## Status

🚧 **In Development** - This service will be implemented in Phase 3.

## Documentation

See [System Design](/docs/design/system-design.md) for architecture details.

