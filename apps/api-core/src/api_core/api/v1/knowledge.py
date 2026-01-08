"""Knowledge base endpoints for file upload and management."""

import logging
import os
import uuid
from datetime import datetime
from typing import Any, Dict
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Request, UploadFile, status

from api_core.auth.dependencies import get_current_active_user
from api_core.auth.internal_service import InternalAuthDep
from api_core.auth.token_validator import TokenValidationResult
from api_core.database.session import get_session_context
from api_core.exceptions import NotFoundError, ValidationError
from api_core.models.knowledge import (
    FileStatusResponse,
    FileUploadResponse,
    FileStatusUpdateRequest,
    KnowledgeBaseFileListResponse,
    KnowledgeBaseFileResponse,
    QdrantInfoUpdateRequest,
)
from pydantic import BaseModel, Field
from api_core.services.knowledge_service import get_knowledge_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/knowledge", tags=["knowledge"])


class KnowledgeBaseQueryRequest(BaseModel):
    """Request model for knowledge base query."""
    
    query: str = Field(..., description="Query/question to ask the knowledge base")


def _kb_file_to_response(kb_file) -> KnowledgeBaseFileResponse:
    """Convert KnowledgeBaseFile model to response model."""
    return KnowledgeBaseFileResponse(
        id=kb_file.id,
        user_id=kb_file.user_id,
        firm_id=kb_file.firm_id,
        filename=kb_file.filename,
        file_type=kb_file.file_type,
        file_size=kb_file.file_size,
        storage_path=kb_file.storage_path,
        status=kb_file.status,
        error_message=kb_file.error_message,
        qdrant_collection=kb_file.qdrant_collection,
        qdrant_point_ids=kb_file.qdrant_point_ids,
        indexed_at=kb_file.indexed_at,
        created_at=kb_file.created_at,
        updated_at=kb_file.updated_at,
    )


@router.post(
    "/upload",
    response_model=FileUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload Knowledge Base File",
    description="Upload a file to the knowledge base for RAG indexing.",
)
async def upload_file(
    request: Request,
    file: UploadFile = File(..., description="File to upload"),
    firm_id: Optional[str] = Form(None, description="Optional firm ID"),
    current_user: TokenValidationResult = Depends(get_current_active_user),
):
    """
    Upload a file to the knowledge base.

    The file will be stored in Azure Blob Storage and a record will be created
    in the database. The file will be queued for processing and indexing.

    Supported file types: PDF, DOCX, TXT, MD
    Maximum file size: 100MB (configurable)
    """
    try:
        # Read file data
        file_data = await file.read()
        if not file_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File is empty",
            )

        # Get file type from extension
        filename = file.filename or "unknown"
        file_extension = filename.split(".")[-1].lower() if "." in filename else ""

        async with get_session_context() as session:
            knowledge_service = get_knowledge_service(session)

            # Upload file
            kb_file = await knowledge_service.upload_file(
                user_id=current_user.user_id,
                firm_id=firm_id,
                filename=filename,
                file_data=file_data,
                file_type=file_extension,
            )

            # Trigger ingestion job via RabbitMQ
            try:
                publisher = getattr(request.app.state, "ingestion_publisher", None)
                if not publisher:
                    raise RuntimeError("RabbitMQ publisher not initialized")

                message: Dict[str, Any] = {
                    "file_id": kb_file.id,
                    "user_id": kb_file.user_id,
                    "firm_id": kb_file.firm_id,
                    "blob_path": kb_file.storage_path,
                    "filename": kb_file.filename,
                    "file_type": kb_file.file_type,
                    "created_at": datetime.utcnow().isoformat(),
                }
                await publisher.publish(message)
            except Exception as e:
                logger.error(f"Failed to publish ingestion job for file {kb_file.id}: {e}", exc_info=True)
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="File uploaded but failed to queue ingestion job",
                ) from e

            return FileUploadResponse(
                file=_kb_file_to_response(kb_file),
                message="File uploaded successfully and queued for processing",
            )

    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
    except Exception as e:
        logger.error(f"Error uploading file: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while uploading the file",
        ) from e


@router.get(
    "/files",
    response_model=KnowledgeBaseFileListResponse,
    status_code=status.HTTP_200_OK,
    summary="List Knowledge Base Files",
    description="Get a list of knowledge base files for the current user.",
)
async def list_files(
    firm_id: Optional[str] = Query(None, description="Filter by firm ID"),
    status_filter: Optional[str] = Query(
        None, alias="status", description="Filter by status (pending, processing, indexed, failed)"
    ),
    current_user: TokenValidationResult = Depends(get_current_active_user),
):
    """
    List knowledge base files.

    Returns all files uploaded by the current user, optionally filtered by
    firm ID and/or status.
    """
    try:
        async with get_session_context() as session:
            knowledge_service = get_knowledge_service(session)

            files = await knowledge_service.list_files(
                user_id=current_user.user_id,
                firm_id=firm_id,
                status=status_filter,
            )

            file_responses = [_kb_file_to_response(f) for f in files]

            return KnowledgeBaseFileListResponse(
                files=file_responses,
                total=len(file_responses),
            )

    except Exception as e:
        logger.error(f"Error listing files: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while listing files",
        ) from e


@router.get(
    "/files/{file_id}",
    response_model=KnowledgeBaseFileResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Knowledge Base File",
    description="Get details of a specific knowledge base file.",
)
async def get_file(
    file_id: str,
    current_user: TokenValidationResult = Depends(get_current_active_user),
):
    """
    Get a knowledge base file by ID.

    Returns file details including status and processing information.
    """
    try:
        async with get_session_context() as session:
            knowledge_service = get_knowledge_service(session)

            kb_file = await knowledge_service.get_file_by_id(file_id, current_user.user_id)

            return _kb_file_to_response(kb_file)

    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e
    except Exception as e:
        logger.error(f"Error getting file: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while retrieving the file",
        ) from e


@router.get(
    "/files/{file_id}/status",
    response_model=FileStatusResponse,
    status_code=status.HTTP_200_OK,
    summary="Get File Status",
    description="Get the processing status of a knowledge base file.",
)
async def get_file_status(
    file_id: str,
    current_user: TokenValidationResult = Depends(get_current_active_user),
):
    """
    Get the processing status of a knowledge base file.

    Returns the current status (pending, processing, indexed, failed) and
    any error messages if processing failed.
    """
    try:
        async with get_session_context() as session:
            knowledge_service = get_knowledge_service(session)

            kb_file = await knowledge_service.get_file_by_id(file_id, current_user.user_id)

            return FileStatusResponse(
                id=kb_file.id,
                status=kb_file.status,
                error_message=kb_file.error_message,
                indexed_at=kb_file.indexed_at,
            )

    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e
    except Exception as e:
        logger.error(f"Error getting file status: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while retrieving file status",
        ) from e


@router.put(
    "/files/{file_id}/status",
    response_model=KnowledgeBaseFileResponse,
    status_code=status.HTTP_200_OK,
    summary="Update File Status (Internal)",
    description="Internal endpoint used by ingestion service to update file processing status.",
)
async def update_file_status_internal(
    file_id: str,
    update: FileStatusUpdateRequest,
    _: None = InternalAuthDep,
):
    """
    Update the processing status of a knowledge base file.

    **Authentication**: Internal API key only (via InternalAuthDep)
    **Used by**: Document Ingestion service
    **Note**: This endpoint is not accessible to users. It requires the X-Internal-API-Key header.
    """
    try:
        async with get_session_context() as session:
            knowledge_service = get_knowledge_service(session)
            kb_file = await knowledge_service.update_file_status(
                file_id=file_id,
                status=update.status,
                error_message=update.error_message,
            )
            return _kb_file_to_response(kb_file)
    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e
    except Exception as e:
        logger.error(f"Error updating file status: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while updating file status",
        ) from e


@router.put(
    "/files/{file_id}/qdrant-info",
    response_model=KnowledgeBaseFileResponse,
    status_code=status.HTTP_200_OK,
    summary="Update Qdrant Info (Internal)",
    description="Internal endpoint used by ingestion service to store Qdrant collection and point IDs.",
)
async def update_qdrant_info_internal(
    file_id: str,
    update: QdrantInfoUpdateRequest,
    _: None = InternalAuthDep,
):
    """
    Update Qdrant collection and point IDs for a knowledge base file.

    **Authentication**: Internal API key only (via InternalAuthDep)
    **Used by**: Document Ingestion service
    **Note**: This endpoint is not accessible to users. It requires the X-Internal-API-Key header.
    """
    try:
        async with get_session_context() as session:
            knowledge_service = get_knowledge_service(session)
            kb_file = await knowledge_service.update_qdrant_info(
                file_id=file_id,
                collection_name=update.collection_name,
                point_ids=update.point_ids,
            )
            return _kb_file_to_response(kb_file)
    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e
    except Exception as e:
        logger.error(f"Error updating Qdrant info: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while updating Qdrant info",
        ) from e


@router.delete(
    "/files/{file_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete Knowledge Base File",
    description="Delete a knowledge base file and remove it from storage.",
)
async def delete_file(
    file_id: str,
    current_user: TokenValidationResult = Depends(get_current_active_user),
):
    """
    Delete a knowledge base file.

    Removes the file from both Azure Blob Storage and the database.
    Also removes associated vectors from Qdrant (if indexed).
    """
    try:
        async with get_session_context() as session:
            knowledge_service = get_knowledge_service(session)

            await knowledge_service.delete_file(file_id, current_user.user_id)

            return None  # 204 No Content

    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e
    except Exception as e:
        logger.error(f"Error deleting file: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while deleting the file",
        ) from e


@router.post(
    "/files/{file_id}/reindex",
    response_model=FileStatusResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Re-index File",
    description="Trigger re-indexing of a knowledge base file.",
)
async def reindex_file(
    request: Request,
    file_id: str,
    current_user: TokenValidationResult = Depends(get_current_active_user),
):
    """
    Re-index a knowledge base file.

    Resets the file status to 'pending' and triggers re-processing.
    This is useful if indexing failed or if the file was updated.
    """
    try:
        async with get_session_context() as session:
            knowledge_service = get_knowledge_service(session)

            # Verify file exists and user has access
            kb_file = await knowledge_service.get_file_by_id(file_id, current_user.user_id)

            # Reset status to pending
            updated_file = await knowledge_service.update_file_status(file_id, "pending")

            # Trigger ingestion job via RabbitMQ
            try:
                publisher = getattr(request.app.state, "ingestion_publisher", None)
                if not publisher:
                    raise RuntimeError("RabbitMQ publisher not initialized")

                message: Dict[str, Any] = {
                    "file_id": updated_file.id,
                    "user_id": updated_file.user_id,
                    "firm_id": updated_file.firm_id,
                    "blob_path": updated_file.storage_path,
                    "filename": updated_file.filename,
                    "file_type": updated_file.file_type,
                    "created_at": datetime.utcnow().isoformat(),
                }
                await publisher.publish(message)
            except Exception as e:
                logger.error(f"Failed to publish reindex job for file {file_id}: {e}", exc_info=True)
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Failed to queue reindex job",
                ) from e

            return FileStatusResponse(
                id=updated_file.id,
                status=updated_file.status,
                error_message=updated_file.error_message,
                indexed_at=updated_file.indexed_at,
            )

    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e
    except Exception as e:
        logger.error(f"Error re-indexing file: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while re-indexing the file",
        ) from e


@router.post(
    "/query",
    status_code=status.HTTP_200_OK,
    summary="Query Knowledge Base",
    description="Query the knowledge base using RAG (Retrieval-Augmented Generation).",
)
async def query_knowledge_base(
    request: Request,
    payload: KnowledgeBaseQueryRequest,
    firm_id: Optional[str] = Query(None, description="Optional firm ID for scoped queries"),
    current_user: TokenValidationResult = Depends(get_current_active_user),
):
    """
    Query the knowledge base using RAG.
    
    This endpoint routes the query to the Cognitive Orchestrator service which:
    1. Performs vector search in Qdrant to find relevant documents
    2. Uses the retrieved context to generate an answer via LLM
    3. Returns the answer along with source references
    
    Args:
        query: The user's question/query
        firm_id: Optional firm ID to scope the search to firm-specific documents
        current_user: Current authenticated user
        
    Returns:
        Response with answer, sources, and chat message format
    """
    try:
        from api_core.clients.cognitive_orch_client import CognitiveOrchClient
        
        # Use firm_id from user if available
        user_firm_id = firm_id
        if not user_firm_id:
            # Try to get firm_id from user's profile
            # For now, we'll pass None and let the orchestrator handle it
            pass
        
        # Call Cognitive Orchestrator chat endpoint
        client = CognitiveOrchClient()
        chat_data = await client.chat(
            message=payload.query,
            user_id=current_user.user_id,
            firm_id=user_firm_id,
            tools_enabled=False,  # Disable tools for simple RAG queries
            temperature=0.2,
        )
        
        # Transform Cognitive Orchestrator response to frontend format
        # Frontend expects: { answer: str, sources: string[], message: ChatMessage }
        # Orchestrator returns: { conversation_id: str, response: str, tool_results: list, iterations: int }
        
        # Extract sources from tool_results if available
        sources: list[str] = []
        if chat_data.get("tool_results"):
            for tool_result in chat_data["tool_results"]:
                if isinstance(tool_result, dict):
                    # Look for source references in tool results
                    if "sources" in tool_result:
                        sources.extend(tool_result["sources"])
                    elif "source" in tool_result:
                        sources.append(tool_result["source"])
        
        # Create chat message format
        from datetime import datetime
        message = {
            "id": str(uuid.uuid4()),
            "role": "assistant",
            "content": chat_data.get("response", ""),
            "timestamp": datetime.utcnow().isoformat(),
        }
        
        return {
            "answer": chat_data.get("response", ""),
            "sources": sources,
            "message": message,
        }
            
    except Exception as e:
        # InternalAPIClient raises httpx exceptions, catch them here
        import httpx
        if isinstance(e, httpx.TimeoutException):
            raise HTTPException(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                detail="Cognitive Orchestrator request timed out",
            ) from e
        elif isinstance(e, httpx.HTTPStatusError):
            logger.error(
                f"Cognitive Orchestrator returned error: {e.response.status_code} - {e.response.text}"
            )
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Cognitive Orchestrator returned error: {e.response.text}",
            ) from e
        elif isinstance(e, httpx.RequestError):
            logger.error(f"Error calling Cognitive Orchestrator: {e}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Failed to connect to Cognitive Orchestrator",
            ) from e
        # Re-raise if it's not an httpx exception
        raise
    except Exception as e:
        logger.error(f"Error querying knowledge base: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while querying the knowledge base",
        ) from e

