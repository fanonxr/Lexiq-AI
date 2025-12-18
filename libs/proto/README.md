# Protocol Buffers

gRPC service definitions and message schemas for inter-service communication.

## Structure

Protocol buffer definitions for:
- Voice Gateway ↔ Cognitive Orchestrator communication (`cognitive_orch.proto`)
- Other inter-service gRPC services (to be added)

## Status

✅ **Active** - Proto definitions are being created and maintained.

## Files

- `cognitive_orch.proto` - Cognitive Orchestrator gRPC service definitions

## Usage

Proto files are compiled to language-specific code:
- Python: Generated in `_pb2.py` and `_pb2_grpc.py` files
- Go: Generated in `.pb.go` files (when needed)

## Compilation

### Using Makefile (Recommended)

```bash
# Compile all proto files
make proto-compile
```

### Using Script Directly

```bash
# Compile proto files using the compilation script
./scripts/compile_protos.sh
```

### Manual Compilation

```bash
# Python
python -m grpc_tools.protoc \
    --proto_path=libs/proto \
    --python_out=apps/cognitive-orch/src/cognitive_orch/grpc/proto \
    --grpc_python_out=apps/cognitive-orch/src/cognitive_orch/grpc/proto \
    libs/proto/cognitive_orch.proto

# Go (when needed)
protoc --go_out=. --go-grpc_out=. libs/proto/*.proto
```

## Output Locations

- **Python**: `apps/cognitive-orch/src/cognitive_orch/grpc/proto/`
  - `cognitive_orch_pb2.py` - Message classes
  - `cognitive_orch_pb2_grpc.py` - Service stubs

## Dependencies

- `grpcio` - gRPC Python runtime
- `grpcio-tools` - Protocol Buffer compiler for Python

These are included in `apps/cognitive-orch/requirements.txt`.

