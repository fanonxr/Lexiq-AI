"""Agent configuration endpoints."""

import logging
import os
from typing import Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from api_core.auth.dependencies import get_current_active_user
from api_core.auth.token_validator import TokenValidationResult
from api_core.database.session import get_session_context
from api_core.exceptions import ValidationError
from api_core.services.agent_service import AgentService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/agent", tags=["agent"])


# Request/Response Models
class AgentConfigResponse(BaseModel):
    """Agent configuration response."""
    
    config: dict = Field(..., description="Agent configuration")


class UpdateAgentConfigRequest(BaseModel):
    """Request to update agent configuration."""
    
    config: dict = Field(..., description="Partial agent configuration to update")


class VoiceOption(BaseModel):
    """Voice option model."""
    
    id: str = Field(..., description="Voice ID")
    name: str = Field(..., description="Voice name")
    icon: str = Field(..., description="Icon identifier")
    description: str = Field(..., description="Voice description")
    previewUrl: Optional[str] = Field(None, description="Preview audio URL")


class VoiceOptionsResponse(BaseModel):
    """Voice options response."""
    
    voices: list[VoiceOption] = Field(..., description="List of available voice options")


class TestCallRequest(BaseModel):
    """Test call request."""
    
    phoneNumber: str = Field(..., description="Phone number to call")


class TestCallResponse(BaseModel):
    """Test call response."""
    
    callId: str = Field(..., description="Call ID")
    status: str = Field(..., description="Call status")
    message: Optional[str] = Field(None, description="Status message")


class ImproveScriptRequest(BaseModel):
    """Request to improve a script."""
    
    script: str = Field(..., description="Current script text")
    scriptType: str = Field(..., description="Script type: greeting, closing, or transfer")


class ImproveScriptResponse(BaseModel):
    """Improved script response."""
    
    improvedScript: str = Field(..., description="Improved script text")


# Default voice options (can be moved to database or config later)
DEFAULT_VOICES = [
    VoiceOption(
        id="1",
        name="Professional",
        icon="user",
        description="Clear and professional tone",
        previewUrl="/audio/voice-professional.mp3",
    ),
    VoiceOption(
        id="2",
        name="Friendly",
        icon="mic",
        description="Warm and approachable",
        previewUrl="/audio/voice-friendly.mp3",
    ),
    VoiceOption(
        id="3",
        name="Assistant",
        icon="user",
        description="Neutral and helpful",
        previewUrl="/audio/voice-assistant.mp3",
    ),
    VoiceOption(
        id="4",
        name="Executive",
        icon="user",
        description="Confident and authoritative",
        previewUrl="/audio/voice-executive.mp3",
    ),
]


@router.get("/config", response_model=AgentConfigResponse, status_code=status.HTTP_200_OK)
async def get_agent_config(
    current_user: TokenValidationResult = Depends(get_current_active_user),
):
    """
    Get current agent configuration.
    
    Returns the agent configuration for the authenticated user.
    If no configuration exists, returns default values.
    """
    try:
        async with get_session_context() as session:
            agent_service = AgentService(session)
            
            # Get firm_id from user if available
            firm_id = None
            if hasattr(current_user, "firm_id") and current_user.firm_id:
                firm_id = current_user.firm_id
            
            config = await agent_service.get_config(current_user.user_id, firm_id)
            config_dict = agent_service._config_to_dict(config)
            
            return AgentConfigResponse(config=config_dict)
            
    except Exception as e:
        logger.error(f"Error getting agent config: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve agent configuration",
        ) from e


@router.put("/config", response_model=AgentConfigResponse, status_code=status.HTTP_200_OK)
async def update_agent_config(
    request: UpdateAgentConfigRequest,
    current_user: TokenValidationResult = Depends(get_current_active_user),
):
    """
    Update agent configuration.
    
    Updates the agent configuration for the authenticated user.
    Only provided fields will be updated.
    """
    try:
        async with get_session_context() as session:
            agent_service = AgentService(session)
            
            # Get firm_id from user if available
            firm_id = None
            if hasattr(current_user, "firm_id") and current_user.firm_id:
                firm_id = current_user.firm_id
            
            # Extract config fields from request
            config_data = request.config
            
            # Update configuration
            config = await agent_service.update_config(
                user_id=current_user.user_id,
                firm_id=firm_id,
                voice_id=config_data.get("voiceId"),
                greeting_script=config_data.get("greetingScript"),
                closing_script=config_data.get("closingScript"),
                transfer_script=config_data.get("transferScript"),
                auto_respond=config_data.get("autoRespond"),
                record_calls=config_data.get("recordCalls"),
                auto_transcribe=config_data.get("autoTranscribe"),
                enable_voicemail=config_data.get("enableVoicemail"),
            )
            
            config_dict = agent_service._config_to_dict(config)
            
            return AgentConfigResponse(config=config_dict)
            
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
    except Exception as e:
        logger.error(f"Error updating agent config: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update agent configuration",
        ) from e


@router.get("/voices", response_model=VoiceOptionsResponse, status_code=status.HTTP_200_OK)
async def get_voice_options(
    current_user: TokenValidationResult = Depends(get_current_active_user),
):
    """
    Get available voice options.
    
    Returns a list of available voice options for the agent.
    """
    try:
        # For now, return default voices
        # In the future, this could be fetched from a database or external service
        return VoiceOptionsResponse(voices=DEFAULT_VOICES)
        
    except Exception as e:
        logger.error(f"Error getting voice options: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve voice options",
        ) from e


@router.post("/test-call", response_model=TestCallResponse, status_code=status.HTTP_200_OK)
async def initiate_test_call(
    request: TestCallRequest,
    current_user: TokenValidationResult = Depends(get_current_active_user),
):
    """
    Initiate a test call.
    
    This is a placeholder endpoint for when the Voice Gateway is integrated.
    For now, it returns a mock response.
    """
    try:
        # Validate phone number format (basic validation)
        phone_number = request.phoneNumber.strip()
        if not phone_number:
            raise ValidationError("Phone number is required")
        
        # TODO: When Voice Gateway is integrated, call it here
        # For now, return a placeholder response
        logger.info(f"Test call requested to {phone_number} by user {current_user.user_id}")
        
        return TestCallResponse(
            callId="placeholder-call-id",
            status="initiated",
            message="Test call functionality will be available when Voice Gateway is integrated",
        )
        
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
    except Exception as e:
        logger.error(f"Error initiating test call: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to initiate test call",
        ) from e


@router.post("/improve-script", response_model=ImproveScriptResponse, status_code=status.HTTP_200_OK)
async def improve_script(
    request: ImproveScriptRequest,
    current_user: TokenValidationResult = Depends(get_current_active_user),
):
    """
    Improve a script using AI.
    
    Uses the Cognitive Orchestrator to improve the given script.
    """
    try:
        # Validate script type
        valid_types = ["greeting", "closing", "transfer"]
        if request.scriptType not in valid_types:
            raise ValidationError(f"scriptType must be one of: {', '.join(valid_types)}")
        
        if not request.script or not request.script.strip():
            raise ValidationError("Script text is required")
        
        # Get Cognitive Orchestrator URL from config or environment
        cognitive_orch_url = os.getenv(
            "COGNITIVE_ORCH_URL",
            "http://cognitive-orch:8001"
        )
        
        # Build prompt for script improvement
        script_type_prompts = {
            "greeting": "Improve this greeting script to be more professional, warm, and engaging while maintaining clarity:",
            "closing": "Improve this closing script to be more professional and leave a positive impression:",
            "transfer": "Improve this transfer script to be more professional and reassuring:",
        }
        
        prompt = f"{script_type_prompts.get(request.scriptType, 'Improve this script:')}\n\n{request.script}"
        
        # Call Cognitive Orchestrator
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                chat_response = await client.post(
                    f"{cognitive_orch_url}/api/v1/orchestrator/chat",
                    json={
                        "message": prompt,
                        "user_id": current_user.user_id,
                        "firm_id": None,  # Can be enhanced to get from user
                        "tools_enabled": False,
                        "temperature": 0.7,  # Slightly higher for creative improvement
                    },
                )
                
                if chat_response.status_code != 200:
                    logger.error(
                        f"Cognitive Orchestrator returned error: {chat_response.status_code} - {chat_response.text}"
                    )
                    raise HTTPException(
                        status_code=status.HTTP_502_BAD_GATEWAY,
                        detail="Cognitive Orchestrator returned an error",
                    )
                
                response_data = chat_response.json()
                improved_script = response_data.get("response", request.script)
                
                return ImproveScriptResponse(improvedScript=improved_script)
                
            except httpx.TimeoutException:
                raise HTTPException(
                    status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                    detail="Cognitive Orchestrator request timed out",
                )
            except httpx.RequestError as e:
                logger.error(f"Error calling Cognitive Orchestrator: {e}", exc_info=True)
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail="Failed to connect to Cognitive Orchestrator",
                ) from e
        
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error improving script: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to improve script",
        ) from e

