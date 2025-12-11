# Shared Libraries

This directory contains shared code used across multiple services in the LexiqAI monorepo.

## Structure

- **`database/`** - SQLAlchemy models and Alembic migrations
  - Shared database models for all services
  - Alembic migration scripts
  - Database connection utilities

- **`proto/`** - Protocol Buffer definitions
  - gRPC service definitions
  - Message schemas for inter-service communication
  - Generated code (excluded from version control)

- **`py-common/`** - Python shared utilities
  - Azure authentication helpers
  - Logging configuration
  - Common utilities and helpers
  - Credential factory for environment detection

## Usage

Each service imports from these shared libraries as needed. See individual service documentation for usage examples.

