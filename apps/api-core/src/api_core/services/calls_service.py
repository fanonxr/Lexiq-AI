"""Calls service for business logic."""

from __future__ import annotations

import logging
from typing import List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from api_core.exceptions import AuthorizationError, NotFoundError, ValidationError
from api_core.models.calls import (
    CallCreateRequest,
    CallListResponse,
    CallResponse,
    CallUpdateRequest,
)
from api_core.repositories.calls_repository import CallsRepository

logger = logging.getLogger(__name__)


class CallsService:
    """Service for call operations."""

    def __init__(self, session: AsyncSession):
        self._repo = CallsRepository(session)
        self.session = session

    async def get_call(self, call_id: str, user_id: Optional[str] = None) -> CallResponse:
        """Get a call by ID."""
        if not call_id or not call_id.strip():
            raise ValidationError("call_id is required")

        call = await self._repo.get_by_id(call_id)
        if not call:
            raise NotFoundError(resource="Call", resource_id=call_id)

        # Check authorization if user_id provided
        if user_id and call.user_id != user_id:
            raise AuthorizationError(
                f"User {user_id} does not have access to call {call_id}"
            )

        return CallResponse(
            id=call.id,
            user_id=call.user_id,
            conversation_id=call.conversation_id,
            phone_number=call.phone_number,
            direction=call.direction,
            status=call.status,
            duration_seconds=call.duration_seconds,
            recording_url=call.recording_url,
            transcript=call.transcript,
            summary=call.summary,
            twilio_call_sid=call.twilio_call_sid,
            started_at=call.started_at,
            answered_at=call.answered_at,
            ended_at=call.ended_at,
            created_at=call.created_at,
            updated_at=call.updated_at,
        )

    async def create_call(self, request: CallCreateRequest) -> CallResponse:
        """Create a new call."""
        if not request.user_id or not request.user_id.strip():
            raise ValidationError("user_id is required")
        if not request.phone_number or not request.phone_number.strip():
            raise ValidationError("phone_number is required")
        if request.direction not in ["inbound", "outbound"]:
            raise ValidationError("direction must be 'inbound' or 'outbound'")

        # Check if call already exists by Twilio SID
        if request.twilio_call_sid:
            existing = await self._repo.get_by_twilio_call_sid(request.twilio_call_sid)
            if existing:
                return CallResponse(
                    id=existing.id,
                    user_id=existing.user_id,
                    conversation_id=existing.conversation_id,
                    phone_number=existing.phone_number,
                    direction=existing.direction,
                    status=existing.status,
                    duration_seconds=existing.duration_seconds,
                    recording_url=existing.recording_url,
                    transcript=existing.transcript,
                    summary=existing.summary,
                    twilio_call_sid=existing.twilio_call_sid,
                    started_at=existing.started_at,
                    answered_at=existing.answered_at,
                    ended_at=existing.ended_at,
                    created_at=existing.created_at,
                    updated_at=existing.updated_at,
                )

        call = await self._repo.create(
            user_id=request.user_id,
            conversation_id=request.conversation_id,
            phone_number=request.phone_number,
            direction=request.direction,
            status=request.status,
            twilio_call_sid=request.twilio_call_sid,
        )

        return CallResponse(
            id=call.id,
            user_id=call.user_id,
            conversation_id=call.conversation_id,
            phone_number=call.phone_number,
            direction=call.direction,
            status=call.status,
            duration_seconds=call.duration_seconds,
            recording_url=call.recording_url,
            transcript=call.transcript,
            summary=call.summary,
            twilio_call_sid=call.twilio_call_sid,
            started_at=call.started_at,
            answered_at=call.answered_at,
            ended_at=call.ended_at,
            created_at=call.created_at,
            updated_at=call.updated_at,
        )

    async def update_call(
        self, call_id: str, request: CallUpdateRequest, user_id: Optional[str] = None
    ) -> CallResponse:
        """Update a call."""
        if not call_id or not call_id.strip():
            raise ValidationError("call_id is required")

        call = await self._repo.get_by_id(call_id)
        if not call:
            raise NotFoundError(resource="Call", resource_id=call_id)

        # Check authorization if user_id provided
        if user_id and call.user_id != user_id:
            raise AuthorizationError(
                f"User {user_id} does not have access to call {call_id}"
            )

        # Update fields
        update_data = {}
        if request.status is not None:
            update_data["status"] = request.status
        if request.duration_seconds is not None:
            update_data["duration_seconds"] = request.duration_seconds
        if request.recording_url is not None:
            update_data["recording_url"] = request.recording_url
        if request.transcript is not None:
            update_data["transcript"] = request.transcript
        if request.summary is not None:
            update_data["summary"] = request.summary
        if request.started_at is not None:
            update_data["started_at"] = request.started_at
        if request.answered_at is not None:
            update_data["answered_at"] = request.answered_at
        if request.ended_at is not None:
            update_data["ended_at"] = request.ended_at

        if update_data:
            updated_call = await self._repo.update(call_id, **update_data)
            if not updated_call:
                raise NotFoundError(resource="Call", resource_id=call_id)
            call = updated_call

        return CallResponse(
            id=call.id,
            user_id=call.user_id,
            conversation_id=call.conversation_id,
            phone_number=call.phone_number,
            direction=call.direction,
            status=call.status,
            duration_seconds=call.duration_seconds,
            recording_url=call.recording_url,
            transcript=call.transcript,
            summary=call.summary,
            twilio_call_sid=call.twilio_call_sid,
            started_at=call.started_at,
            answered_at=call.answered_at,
            ended_at=call.ended_at,
            created_at=call.created_at,
            updated_at=call.updated_at,
        )

    async def list_calls(
        self,
        user_id: str,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> CallListResponse:
        """List calls for a user."""
        if not user_id or not user_id.strip():
            raise ValidationError("user_id is required")

        calls = await self._repo.get_by_user_id(user_id, status, skip, limit)
        total = await self._repo.count_by_user_id(user_id, status)

        call_responses = [
            CallResponse(
                id=call.id,
                user_id=call.user_id,
                conversation_id=call.conversation_id,
                phone_number=call.phone_number,
                direction=call.direction,
                status=call.status,
                duration_seconds=call.duration_seconds,
                recording_url=call.recording_url,
                transcript=call.transcript,
                summary=call.summary,
                twilio_call_sid=call.twilio_call_sid,
                started_at=call.started_at,
                answered_at=call.answered_at,
                ended_at=call.ended_at,
                created_at=call.created_at,
                updated_at=call.updated_at,
            )
            for call in calls
        ]

        return CallListResponse(calls=call_responses, total=total)


def get_calls_service(session: AsyncSession) -> CallsService:
    """Factory for CallsService."""
    return CallsService(session=session)

