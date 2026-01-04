"""Memory Service for Long-Term Client Memory Management.

This service handles client identification, memory storage, and dossier generation
for the Long-Term Memory feature. It enables the AI to recognize returning callers
and personalize interactions based on past conversations.
"""

import json
from datetime import datetime, timedelta
from typing import List, Optional

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

# Import models from api-core
# Note: This requires api-core to be in the Python path
try:
    from api_core.database.models import Client, ClientMemory
except ImportError:
    # Fallback for development/testing
    import logging
    logging.warning("Could not import models from api_core, using local imports")
    # In production, ensure api-core is in PYTHONPATH or installed as a package

from cognitive_orch.database import get_session_context
from cognitive_orch.utils.logging import get_logger

logger = get_logger("memory_service")


class MemoryService:
    """Service for managing client memory and recognition.
    
    This service provides methods for:
    - Identifying clients by phone number
    - Retrieving client interaction history (dossier)
    - Storing new memories after calls
    
    The service is designed to be called from the gRPC handlers and post-call workers.
    """

    def __init__(self, session: Optional[AsyncSession] = None):
        """
        Initialize the memory service.
        
        Args:
            session: Optional database session. If not provided, the service will
                    create its own sessions using get_session_context().
        """
        self.session = session
        self._owns_session = session is None

    async def identify_client(
        self,
        firm_id: str,
        phone_number: str,
        email: Optional[str] = None,
        external_crm_id: Optional[str] = None,
    ) -> Client:
        """
        Identify or create a client using multiple identification methods.
        
        Lookup priority:
        1. Phone number (primary, fastest)
        2. Email (if provided and phone not found)
        3. External CRM ID (if provided and neither phone nor email found)
        
        If a client is found by email or CRM ID but has a different phone,
        the phone number will be updated (e.g., client changed phones).
        
        Args:
            firm_id: The firm ID (UUID string)
            phone_number: The caller's phone number (E.164 format recommended)
            email: Optional email address collected during conversation
            external_crm_id: Optional external CRM/system ID for integration
        
        Returns:
            Client: The identified or newly created client
        
        Raises:
            Exception: If database operation fails
        """
        try:
            if self._owns_session:
                async with get_session_context() as session:
                    return await self._identify_client_impl(
                        session, firm_id, phone_number, email, external_crm_id
                    )
            else:
                return await self._identify_client_impl(
                    self.session, firm_id, phone_number, email, external_crm_id
                )
        except Exception as e:
            logger.error(
                f"Error identifying client for firm {firm_id}, phone {phone_number}: {e}",
                exc_info=True,
            )
            raise

    async def _identify_client_impl(
        self,
        session: AsyncSession,
        firm_id: str,
        phone_number: str,
        email: Optional[str],
        external_crm_id: Optional[str],
    ) -> Client:
        """Internal implementation of identify_client with multi-factor lookup."""
        # Normalize phone number
        normalized_phone = self._normalize_phone_number(phone_number)

        # Strategy 1: Try phone number first (fastest, most reliable)
        stmt = select(Client).where(
            Client.firm_id == firm_id, Client.phone_number == normalized_phone
        )
        result = await session.execute(stmt)
        client = result.scalar_one_or_none()

        if client:
            # Found by phone - update last_called_at
            logger.info(f"Recognized client by phone: {client.id} ({normalized_phone})")
            client.last_called_at = datetime.utcnow()
            
            # Optionally update email/crm_id if provided and not set
            if email and not client.email:
                client.email = email
                logger.info(f"Updated client {client.id} with email: {email}")
            if external_crm_id and not client.external_crm_id:
                client.external_crm_id = external_crm_id
                logger.info(f"Updated client {client.id} with CRM ID: {external_crm_id}")
            
            await session.commit()
            await session.refresh(client)
            return client

        # Strategy 2: Try email if provided
        if email:
            stmt = select(Client).where(Client.firm_id == firm_id, Client.email == email)
            result = await session.execute(stmt)
            client = result.scalar_one_or_none()

            if client:
                # Found by email - update phone number (client changed phones!)
                logger.info(
                    f"Recognized client by email: {client.id} ({email}), "
                    f"updating phone from {client.phone_number} to {normalized_phone}"
                )
                client.phone_number = normalized_phone
                client.last_called_at = datetime.utcnow()
                
                if external_crm_id and not client.external_crm_id:
                    client.external_crm_id = external_crm_id
                
                await session.commit()
                await session.refresh(client)
                return client

        # Strategy 3: Try external CRM ID if provided
        if external_crm_id:
            stmt = select(Client).where(
                Client.firm_id == firm_id, Client.external_crm_id == external_crm_id
            )
            result = await session.execute(stmt)
            client = result.scalar_one_or_none()

            if client:
                # Found by CRM ID - update phone and/or email
                logger.info(
                    f"Recognized client by CRM ID: {client.id} ({external_crm_id}), "
                    f"updating phone from {client.phone_number} to {normalized_phone}"
                )
                client.phone_number = normalized_phone
                client.last_called_at = datetime.utcnow()
                
                if email and not client.email:
                    client.email = email
                
                await session.commit()
                await session.refresh(client)
                return client

        # Strategy 4: Create new client (not found by any method)
        logger.info(f"Creating new client for phone {normalized_phone}")
        new_client = Client(
            firm_id=firm_id,
            phone_number=normalized_phone,
            email=email,
            external_crm_id=external_crm_id,
            last_called_at=datetime.utcnow(),
        )
        session.add(new_client)
        await session.commit()
        await session.refresh(new_client)
        logger.info(f"Created new client: {new_client.id}")
        return new_client

    async def get_client_dossier(
        self, client_id: str, max_memories: int = 3
    ) -> Optional[str]:
        """
        Retrieve and format the client's interaction history as a dossier.
        
        This method fetches the most recent memories for a client and formats them
        into a human-readable dossier string with relative timestamps.
        
        Args:
            client_id: The client's UUID
            max_memories: Maximum number of memories to include (default: 3)
        
        Returns:
            str: Formatted dossier text, or None if no memories exist
            
        Example output:
            "- [2 days ago]: Client called about divorce case. Scheduled consultation.
             - [1 week ago]: Initial inquiry about family law services.
             - [2 weeks ago]: Left voicemail asking about child custody."
        
        Raises:
            Exception: If database operation fails
        """
        try:
            if self._owns_session:
                async with get_session_context() as session:
                    return await self._get_client_dossier_impl(session, client_id, max_memories)
            else:
                return await self._get_client_dossier_impl(self.session, client_id, max_memories)
        except Exception as e:
            logger.error(f"Error getting dossier for client {client_id}: {e}", exc_info=True)
            raise

    async def _get_client_dossier_impl(
        self, session: AsyncSession, client_id: str, max_memories: int
    ) -> Optional[str]:
        """Internal implementation of get_client_dossier."""
        # Query for recent memories
        stmt = (
            select(ClientMemory)
            .where(ClientMemory.client_id == client_id)
            .order_by(ClientMemory.created_at.desc())
            .limit(max_memories)
        )
        result = await session.execute(stmt)
        memories = result.scalars().all()

        if not memories:
            logger.debug(f"No memories found for client {client_id}")
            return None

        logger.info(f"Found {len(memories)} memories for client {client_id}")

        # Format memories as dossier
        dossier_lines = []
        now = datetime.utcnow()

        for memory in memories:
            # Calculate relative time
            time_ago = self._format_time_ago(now, memory.created_at)
            # Format line
            line = f"- [{time_ago}]: {memory.summary_text}"
            dossier_lines.append(line)

        dossier_text = "\n".join(dossier_lines)
        return dossier_text

    async def store_memory(
        self,
        client_id: str,
        summary_text: str,
        qdrant_point_id: Optional[str] = None,
    ) -> ClientMemory:
        """
        Store a new memory for a client.
        
        This method is typically called by the post-call worker after generating
        a summary and storing the embedding in Qdrant.
        
        Args:
            client_id: The client's UUID
            summary_text: The summarized interaction text
            qdrant_point_id: Optional Qdrant point ID (reference to vector)
        
        Returns:
            ClientMemory: The newly created memory record
        
        Raises:
            Exception: If database operation fails
        """
        try:
            if self._owns_session:
                async with get_session_context() as session:
                    return await self._store_memory_impl(
                        session, client_id, summary_text, qdrant_point_id
                    )
            else:
                return await self._store_memory_impl(
                    self.session, client_id, summary_text, qdrant_point_id
                )
        except Exception as e:
            logger.error(f"Error storing memory for client {client_id}: {e}", exc_info=True)
            raise

    async def _store_memory_impl(
        self,
        session: AsyncSession,
        client_id: str,
        summary_text: str,
        qdrant_point_id: Optional[str],
    ) -> ClientMemory:
        """Internal implementation of store_memory."""
        # Create new memory
        memory = ClientMemory(
            client_id=client_id,
            summary_text=summary_text,
            qdrant_point_id=qdrant_point_id,
        )
        session.add(memory)
        await session.commit()
        await session.refresh(memory)

        logger.info(f"Stored new memory for client {client_id}: {memory.id}")
        return memory

    async def update_client_name(
        self, client_id: str, first_name: Optional[str] = None, last_name: Optional[str] = None
    ) -> None:
        """
        Update a client's name information.
        
        This can be called when the AI learns the client's name during a conversation.
        
        Args:
            client_id: The client's UUID
            first_name: Optional first name
            last_name: Optional last name
        
        Raises:
            Exception: If database operation fails
        """
        try:
            if self._owns_session:
                async with get_session_context() as session:
                    await self._update_client_name_impl(
                        session, client_id, first_name, last_name
                    )
            else:
                await self._update_client_name_impl(self.session, client_id, first_name, last_name)
        except Exception as e:
            logger.error(f"Error updating name for client {client_id}: {e}", exc_info=True)
            raise

    async def _update_client_name_impl(
        self,
        session: AsyncSession,
        client_id: str,
        first_name: Optional[str],
        last_name: Optional[str],
    ) -> None:
        """Internal implementation of update_client_name."""
        update_data = {}
        if first_name is not None:
            update_data["first_name"] = first_name
        if last_name is not None:
            update_data["last_name"] = last_name

        if not update_data:
            return

        stmt = update(Client).where(Client.id == client_id).values(**update_data)
        await session.execute(stmt)
        await session.commit()

        logger.info(f"Updated name for client {client_id}: {update_data}")

    async def update_client_info(
        self,
        client_id: str,
        email: Optional[str] = None,
        external_crm_id: Optional[str] = None,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
    ) -> None:
        """
        Update a client's information (email, CRM ID, name).
        
        This is a convenience method that can update multiple fields at once.
        Typically called when information is collected during a conversation.
        
        Args:
            client_id: The client's UUID
            email: Optional email address
            external_crm_id: Optional external CRM ID
            first_name: Optional first name
            last_name: Optional last name
        
        Raises:
            Exception: If database operation fails
        """
        try:
            if self._owns_session:
                async with get_session_context() as session:
                    await self._update_client_info_impl(
                        session, client_id, email, external_crm_id, first_name, last_name
                    )
            else:
                await self._update_client_info_impl(
                    self.session, client_id, email, external_crm_id, first_name, last_name
                )
        except Exception as e:
            logger.error(f"Error updating info for client {client_id}: {e}", exc_info=True)
            raise

    async def _update_client_info_impl(
        self,
        session: AsyncSession,
        client_id: str,
        email: Optional[str],
        external_crm_id: Optional[str],
        first_name: Optional[str],
        last_name: Optional[str],
    ) -> None:
        """Internal implementation of update_client_info."""
        update_data = {}
        if email is not None:
            update_data["email"] = email
        if external_crm_id is not None:
            update_data["external_crm_id"] = external_crm_id
        if first_name is not None:
            update_data["first_name"] = first_name
        if last_name is not None:
            update_data["last_name"] = last_name

        if not update_data:
            return

        stmt = update(Client).where(Client.id == client_id).values(**update_data)
        await session.execute(stmt)
        await session.commit()

        logger.info(f"Updated info for client {client_id}: {update_data}")

    @staticmethod
    def _normalize_phone_number(phone_number: str) -> str:
        """
        Normalize phone number for consistent storage.
        
        Removes spaces, dashes, parentheses, etc.
        
        Args:
            phone_number: Raw phone number string
        
        Returns:
            str: Normalized phone number (digits and + only)
        """
        # Keep only digits and leading +
        normalized = ""
        for i, c in enumerate(phone_number):
            if c.isdigit():
                normalized += c
            elif c == "+" and i == 0:
                normalized += c
        return normalized

    @staticmethod
    def _format_time_ago(now: datetime, past: datetime) -> str:
        """
        Format a datetime as a relative time string.
        
        Args:
            now: Current datetime
            past: Past datetime
        
        Returns:
            str: Relative time string (e.g., "2 days ago", "1 week ago")
        """
        delta = now - past

        if delta < timedelta(hours=1):
            minutes = int(delta.total_seconds() / 60)
            return f"{minutes} minutes ago" if minutes != 1 else "1 minute ago"
        elif delta < timedelta(days=1):
            hours = int(delta.total_seconds() / 3600)
            return f"{hours} hours ago" if hours != 1 else "1 hour ago"
        elif delta < timedelta(days=7):
            days = delta.days
            return f"{days} days ago" if days != 1 else "1 day ago"
        elif delta < timedelta(days=30):
            weeks = delta.days // 7
            return f"{weeks} weeks ago" if weeks != 1 else "1 week ago"
        elif delta < timedelta(days=365):
            months = delta.days // 30
            return f"{months} months ago" if months != 1 else "1 month ago"
        else:
            years = delta.days // 365
            return f"{years} years ago" if years != 1 else "1 year ago"

