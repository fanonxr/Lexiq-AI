## gRPC (Placeholder)

Proto definitions for Voice Gateway ↔ Cognitive Orchestrator are not present yet (`libs/proto` is still a placeholder).

When protos are added, the gRPC handlers should call the same core logic used by the HTTP chat endpoint:
- `POST /api/v1/orchestrator/chat` (stateful tool loop + Redis)

Recommended next step (once protos exist):
- Implement `grpc/server.py` + `grpc/handlers.py` using `grpc.aio`
- In the handler, map incoming requests to the same “chat service” logic used by HTTP


