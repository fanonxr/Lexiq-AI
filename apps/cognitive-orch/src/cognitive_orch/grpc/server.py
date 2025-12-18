"""gRPC server setup and lifecycle management."""

from __future__ import annotations

import logging
from typing import Optional

import grpc
from grpc import aio

from cognitive_orch.config import get_settings
from cognitive_orch.utils.logging import get_logger

logger = get_logger("grpc.server")
settings = get_settings()


class GRPCServer:
    """gRPC server for Cognitive Orchestrator service.
    
    Handles server lifecycle (start/stop) and integrates with FastAPI application.
    """

    def __init__(self, port: Optional[int] = None, redis_pool=None):
        """Initialize gRPC server.
        
        Args:
            port: Port to listen on. If None, uses GRPC_PORT from settings.
            redis_pool: Optional Redis connection pool for state management.
        """
        self.port = port or settings.grpc.port
        self.redis_pool = redis_pool
        self.server: Optional[aio.Server] = None
        self._servicer = None

    async def start(self) -> None:
        """Start the gRPC server.
        
        Creates and configures the async gRPC server, registers the servicer,
        and starts listening on the configured port.
        
        Raises:
            RuntimeError: If server fails to start.
        """
        if not settings.grpc.enabled:
            logger.info("gRPC server is disabled (GRPC_ENABLED=false)")
            return

        try:
            # Log the port being used for debugging
            logger.info(f"gRPC server configuration: enabled={settings.grpc.enabled}, port={self.port}, max_workers={settings.grpc.max_workers}")
            logger.info(f"Starting gRPC server on port {self.port}...")
            
            # Create async gRPC server
            self.server = aio.server()
            
            # Import servicer here to avoid circular imports
            from cognitive_orch.grpc.handlers import CognitiveOrchestratorServicer
            
            # Create servicer instance with Redis pool
            self._servicer = CognitiveOrchestratorServicer(redis_pool=self.redis_pool)
            
            # Register servicer with server
            from cognitive_orch.grpc.proto import cognitive_orch_pb2_grpc
            
            cognitive_orch_pb2_grpc.add_CognitiveOrchestratorServicer_to_server(
                self._servicer,
                self.server
            )
            
            # Configure server options
            # Note: Server options can be set via environment variables or here
            # For now, we use defaults - can be enhanced later if needed
            
            # Add insecure port (for now - can add TLS later)
            listen_addr = f'[::]:{self.port}'
            self.server.add_insecure_port(listen_addr)
            
            # Start server
            await self.server.start()
            
            logger.info(f"✓ gRPC server started successfully on port {self.port}")
            
        except Exception as e:
            logger.error(f"Failed to start gRPC server: {e}", exc_info=True)
            raise RuntimeError(f"gRPC server startup failed: {e}") from e

    async def stop(self, grace_period: int = 5) -> None:
        """Stop the gRPC server gracefully.
        
        Waits for ongoing requests to complete before shutting down.
        
        Args:
            grace_period: Maximum seconds to wait for ongoing requests to complete.
        """
        if not self.server:
            return
        
        try:
            logger.info(f"Stopping gRPC server (grace period: {grace_period}s)...")
            
            # Stop accepting new requests
            await self.server.stop(grace_period)
            
            # Wait for server to fully stop
            await self.server.wait_for_termination(timeout=grace_period)
            
            logger.info("✓ gRPC server stopped successfully")
            
        except Exception as e:
            logger.error(f"Error stopping gRPC server: {e}", exc_info=True)
        finally:
            self.server = None
            self._servicer = None

    async def wait_for_termination(self, timeout: Optional[float] = None) -> None:
        """Wait for the server to terminate.
        
        Args:
            timeout: Maximum seconds to wait. If None, waits indefinitely.
        """
        if self.server:
            await self.server.wait_for_termination(timeout=timeout)

