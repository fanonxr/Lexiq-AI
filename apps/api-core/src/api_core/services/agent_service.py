"""Agent configuration service."""

import logging
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from api_core.database.models import AgentConfig, User
from api_core.exceptions import NotFoundError, ValidationError
from api_core.repositories.agent_repository import AgentRepository

logger = logging.getLogger(__name__)


class AgentService:
    """Service for agent configuration operations."""

    def __init__(self, session: AsyncSession):
        """Initialize agent service."""
        self.repository = AgentRepository(session)
        self.session = session

    async def get_config(self, user_id: str, firm_id: Optional[str] = None) -> AgentConfig:
        """
        Get agent configuration for a user.
        
        Priority: firm-specific config > user-specific config > default config
        
        Args:
            user_id: User ID
            firm_id: Optional firm ID
            
        Returns:
            AgentConfig instance (creates default if none exists)
        """
        # Try to get existing config
        config = await self.repository.get_by_user_id(user_id, firm_id)
        
        if config:
            return config
        
        # Create default config if none exists
        logger.info(f"Creating default agent config for user {user_id}, firm {firm_id}")
        return await self.repository.create_or_update(
            user_id=user_id,
            firm_id=firm_id
        )

    async def update_config(
        self,
        user_id: str,
        firm_id: Optional[str] = None,
        voice_id: Optional[str] = None,
        greeting_script: Optional[str] = None,
        closing_script: Optional[str] = None,
        transfer_script: Optional[str] = None,
        auto_respond: Optional[bool] = None,
        record_calls: Optional[bool] = None,
        auto_transcribe: Optional[bool] = None,
        enable_voicemail: Optional[bool] = None,
    ) -> AgentConfig:
        """
        Update agent configuration.
        
        Args:
            user_id: User ID
            firm_id: Optional firm ID
            voice_id: Optional voice ID
            greeting_script: Optional greeting script
            closing_script: Optional closing script
            transfer_script: Optional transfer script
            auto_respond: Optional auto-respond setting
            record_calls: Optional record calls setting
            auto_transcribe: Optional auto-transcribe setting
            enable_voicemail: Optional enable voicemail setting
            
        Returns:
            Updated AgentConfig instance
        """
        # Build update dict (only include non-None values)
        update_data = {}
        if voice_id is not None:
            update_data["voice_id"] = voice_id
        if greeting_script is not None:
            update_data["greeting_script"] = greeting_script
        if closing_script is not None:
            update_data["closing_script"] = closing_script
        if transfer_script is not None:
            update_data["transfer_script"] = transfer_script
        if auto_respond is not None:
            update_data["auto_respond"] = auto_respond
        if record_calls is not None:
            update_data["record_calls"] = record_calls
        if auto_transcribe is not None:
            update_data["auto_transcribe"] = auto_transcribe
        if enable_voicemail is not None:
            update_data["enable_voicemail"] = enable_voicemail
        
        if not update_data:
            # No updates provided, just return existing config
            return await self.get_config(user_id, firm_id)
        
        # Create or update config
        return await self.repository.create_or_update(
            user_id=user_id,
            firm_id=firm_id,
            **update_data
        )

    def _config_to_dict(self, config: AgentConfig) -> dict:
        """Convert AgentConfig model to dictionary for API response."""
        return {
            "voiceId": config.voice_id,
            "greetingScript": config.greeting_script,
            "closingScript": config.closing_script,
            "transferScript": config.transfer_script,
            "autoRespond": config.auto_respond,
            "recordCalls": config.record_calls,
            "autoTranscribe": config.auto_transcribe,
            "enableVoicemail": config.enable_voicemail,
        }

