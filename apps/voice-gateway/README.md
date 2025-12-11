# Voice Gateway Service

**Go service for handling Twilio WebSocket connections and audio streaming**

## Overview

The Voice Gateway service handles:
- WebSocket connections from Twilio
- Audio stream buffering and processing
- STT (Speech-to-Text) vendor API management
- TTS (Text-to-Speech) vendor API management
- Streaming parsed text events to Cognitive Orchestrator via gRPC

## Technology Stack

- **Language:** Go 1.21+
- **Protocol:** WebSocket (Twilio), gRPC (to Orchestrator)
- **Dependencies:** Twilio SDK, gRPC

## Status

🚧 **In Development** - This service will be implemented in Phase 2.

## Documentation

See [System Design](/docs/design/system-design.md) for architecture details.

