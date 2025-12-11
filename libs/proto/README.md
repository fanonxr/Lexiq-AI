# Protocol Buffers

gRPC service definitions and message schemas for inter-service communication.

## Structure

Protocol buffer definitions for:
- Voice Gateway ↔ Cognitive Orchestrator communication
- Other inter-service gRPC services

## Status

🚧 **In Development** - Proto definitions will be created in Phase 2.

## Usage

Proto files are compiled to language-specific code:
- Python: Generated in `_pb2.py` files
- Go: Generated in `.pb.go` files

## Compilation

```bash
# Python
python -m grpc_tools.protoc -I. --python_out=. --grpc_python_out=. *.proto

# Go
protoc --go_out=. --go-grpc_out=. *.proto
```

