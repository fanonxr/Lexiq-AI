# Orchestrator gRPC Client

This package contains the gRPC client for communicating with the Cognitive Orchestrator service.

## Proto Compilation

Before using the Orchestrator client, you must compile the Protocol Buffer definitions:

```bash
# From the project root
make proto-compile-go
```

This will generate Go code from `libs/proto/cognitive_orch.proto` into `internal/orchestrator/proto/`.

## Prerequisites

- `protoc` - Protocol Buffer compiler
- `protoc-gen-go` - Go plugin for protoc
- `protoc-gen-go-grpc` - gRPC Go plugin for protoc

Install with:
```bash
go install google.golang.org/protobuf/cmd/protoc-gen-go@latest
go install google.golang.org/grpc/cmd/protoc-gen-go-grpc@latest
```

## Usage

```go
import "github.com/lexiqai/voice-gateway/internal/orchestrator"

// Create client
client, err := orchestrator.NewOrchestratorClient(cfg)
if err != nil {
    log.Fatal(err)
}
defer client.Close()

// Stream text to Orchestrator
responseChan, err := client.ProcessTextStream(ctx, conversationID, text, userID, firmID)
if err != nil {
    log.Fatal(err)
}

// Process responses
for response := range responseChan {
    if response.TextChunk != "" {
        // Handle text chunk
    }
    if response.IsDone {
        break
    }
}
```

