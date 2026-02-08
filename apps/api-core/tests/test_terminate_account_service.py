"""Tests for TerminateAccountService (Phase 2–4: DB + Blob + Qdrant + Calendar + Redis)."""

import pytest
from unittest.mock import AsyncMock, patch

from sqlalchemy.ext.asyncio import AsyncSession

from api_core.database.models import CalendarIntegration, Conversation, Firm, User
from api_core.exceptions import NotFoundError
from api_core.services.terminate_account_service import TerminateAccountService


@pytest.mark.asyncio
async def test_terminate_account_raises_if_user_not_found(session: AsyncSession):
    """terminate_account raises NotFoundError when user does not exist."""
    service = TerminateAccountService(session)
    with pytest.raises(NotFoundError) as exc_info:
        await service.terminate_account("non-existent-user-id")
    assert exc_info.value.details.get("resource") == "User"


@pytest.mark.asyncio
async def test_terminate_account_deletes_user_and_orphan_firm(
    session: AsyncSession,
):
    """terminate_account deletes user and orphan firm (only user in firm)."""
    # Create firm and user
    firm = Firm(name="Test Firm")
    session.add(firm)
    await session.flush()
    user = User(
        email="delete-me@example.com",
        name="Delete Me",
        firm_id=firm.id,
    )
    session.add(user)
    await session.flush()
    user_id = user.id
    firm_id = firm.id
    await session.commit()

    # Mock Blob and Qdrant so we only test DB path
    with patch(
        "api_core.services.terminate_account_service.get_storage_service"
    ) as mock_storage:
        mock_storage.return_value.delete_file = AsyncMock()
        with patch(
            "api_core.services.terminate_account_service.qdrant_delete_points"
        ), patch(
            "api_core.services.terminate_account_service.qdrant_delete_collection"
        ), patch(
            "api_core.services.terminate_account_service.delete_conversation_keys",
            new_callable=AsyncMock,
        ):
            service = TerminateAccountService(session)
            await service.terminate_account(user_id)
            await session.commit()

    # User and firm should be gone
    from sqlalchemy import select

    u = await session.execute(select(User).where(User.id == user_id))
    assert u.scalar_one_or_none() is None
    f = await session.execute(select(Firm).where(Firm.id == firm_id))
    assert f.scalar_one_or_none() is None


@pytest.mark.asyncio
async def test_terminate_account_deletes_only_user_when_firm_has_other_users(
    session: AsyncSession,
):
    """terminate_account deletes only the user when firm has other users."""
    firm = Firm(name="Shared Firm")
    session.add(firm)
    await session.flush()
    user1 = User(email="user1@example.com", name="User One", firm_id=firm.id)
    user2 = User(email="user2@example.com", name="User Two", firm_id=firm.id)
    session.add_all([user1, user2])
    await session.flush()
    user1_id = user1.id
    firm_id = firm.id
    await session.commit()

    with patch(
        "api_core.services.terminate_account_service.get_storage_service"
    ) as mock_storage:
        mock_storage.return_value.delete_file = AsyncMock()
        with patch(
            "api_core.services.terminate_account_service.qdrant_delete_points"
        ), patch(
            "api_core.services.terminate_account_service.qdrant_delete_collection"
        ), patch(
            "api_core.services.terminate_account_service.delete_conversation_keys",
            new_callable=AsyncMock,
        ):
            service = TerminateAccountService(session)
            await service.terminate_account(user1_id)
            await session.commit()

    from sqlalchemy import select

    u1 = await session.execute(select(User).where(User.id == user1_id))
    assert u1.scalar_one_or_none() is None
    u2 = await session.execute(select(User).where(User.id == user2.id))
    assert u2.scalar_one_or_none() is not None
    f = await session.execute(select(Firm).where(Firm.id == firm_id))
    assert f.scalar_one_or_none() is not None


@pytest.mark.asyncio
async def test_terminate_account_revokes_calendar_webhooks(
    session: AsyncSession,
):
    """terminate_account calls delete_outlook_webhook_subscription for user's Outlook integrations."""
    firm = Firm(name="Firm")
    session.add(firm)
    await session.flush()
    user = User(
        email="cal@example.com",
        name="Cal User",
        firm_id=firm.id,
    )
    session.add(user)
    await session.flush()
    user_id = user.id
    integration = CalendarIntegration(
        user_id=user_id,
        integration_type="outlook",
        webhook_subscription_id="graph-sub-123",
        is_active=True,
    )
    session.add(integration)
    await session.commit()

    with patch(
        "api_core.services.terminate_account_service.get_storage_service"
    ) as mock_storage:
        mock_storage.return_value.delete_file = AsyncMock()
        with patch(
            "api_core.services.terminate_account_service.qdrant_delete_points"
        ), patch(
            "api_core.services.terminate_account_service.qdrant_delete_collection"
        ), patch(
            "api_core.services.terminate_account_service.delete_conversation_keys",
            new_callable=AsyncMock,
        ):
            service = TerminateAccountService(session)
            mock_calendar = AsyncMock()
            mock_calendar.delete_outlook_webhook_subscription = AsyncMock()
            service._calendar_service = mock_calendar
            await service.terminate_account(user_id)
            await session.commit()

    mock_calendar.delete_outlook_webhook_subscription.assert_called_once()
    call_arg = mock_calendar.delete_outlook_webhook_subscription.call_args[0][0]
    assert call_arg.user_id == user_id
    assert call_arg.webhook_subscription_id == "graph-sub-123"


@pytest.mark.asyncio
async def test_terminate_account_deletes_redis_conversation_keys(
    session: AsyncSession,
):
    """terminate_account calls delete_conversation_keys with user's conversation IDs."""
    firm = Firm(name="Firm")
    session.add(firm)
    await session.flush()
    user = User(
        email="redis@example.com",
        name="Redis User",
        firm_id=firm.id,
    )
    session.add(user)
    await session.flush()
    user_id = user.id
    conv = Conversation(user_id=user_id, firm_id=firm.id, status="active")
    session.add(conv)
    await session.flush()
    conv_id = conv.id
    await session.commit()

    mock_delete_keys = AsyncMock()
    with patch(
        "api_core.services.terminate_account_service.get_storage_service"
    ) as mock_storage:
        mock_storage.return_value.delete_file = AsyncMock()
        with patch(
            "api_core.services.terminate_account_service.qdrant_delete_points"
        ), patch(
            "api_core.services.terminate_account_service.qdrant_delete_collection"
        ), patch(
            "api_core.services.terminate_account_service.delete_conversation_keys",
            mock_delete_keys,
        ):
            service = TerminateAccountService(session)
            await service.terminate_account(user_id)
            await session.commit()

    mock_delete_keys.assert_called_once()
    call_ids = mock_delete_keys.call_args[0][0]
    assert call_ids == [conv_id]


@pytest.mark.asyncio
async def test_terminate_account_calls_redis_cleanup_with_empty_list_when_no_conversations(
    session: AsyncSession,
):
    """terminate_account calls delete_conversation_keys with [] when user has no conversations."""
    firm = Firm(name="Firm")
    session.add(firm)
    await session.flush()
    user = User(
        email="noconv@example.com",
        name="No Conv",
        firm_id=firm.id,
    )
    session.add(user)
    await session.flush()
    user_id = user.id
    await session.commit()

    mock_delete_keys = AsyncMock()
    with patch(
        "api_core.services.terminate_account_service.get_storage_service"
    ) as mock_storage:
        mock_storage.return_value.delete_file = AsyncMock()
        with patch(
            "api_core.services.terminate_account_service.qdrant_delete_points"
        ), patch(
            "api_core.services.terminate_account_service.qdrant_delete_collection"
        ), patch(
            "api_core.services.terminate_account_service.delete_conversation_keys",
            mock_delete_keys,
        ):
            service = TerminateAccountService(session)
            await service.terminate_account(user_id)
            await session.commit()

    mock_delete_keys.assert_called_once_with([])
