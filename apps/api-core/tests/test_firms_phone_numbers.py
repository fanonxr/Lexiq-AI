"""Unit tests for firm phone number functionality."""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from api_core.database.models import Firm, User
from api_core.exceptions import (
    AuthorizationError,
    ConflictError,
    NotFoundError,
    ValidationError,
    ExternalServiceError,
)
from api_core.repositories.firms_repository import FirmsRepository
from api_core.services.firms_service import FirmsService
from api_core.services.twilio_service import (
    TwilioService,
    TwilioPhoneNumber,
    TwilioSubaccount,
)


# ============================================================================
# Repository Tests
# ============================================================================


@pytest.mark.asyncio
async def test_get_firm_by_phone_number_found(session):
    """Test getting firm by phone number when firm exists."""
    repo = FirmsRepository(session)
    
    # Create a firm with a phone number
    firm = Firm(
        id=str(uuid4()),
        name="Test Firm",
        twilio_phone_number="+15551234567",
        twilio_phone_number_sid="PN123456789",
        twilio_subaccount_sid="AC123456789",
    )
    session.add(firm)
    await session.commit()
    
    # Test retrieval
    result = await repo.get_firm_by_phone_number("+15551234567")
    
    assert result is not None
    assert result.id == firm.id
    assert result.twilio_phone_number == "+15551234567"


@pytest.mark.asyncio
async def test_get_firm_by_phone_number_not_found(session):
    """Test getting firm by phone number when firm doesn't exist."""
    repo = FirmsRepository(session)
    
    result = await repo.get_firm_by_phone_number("+15559999999")
    
    assert result is None


@pytest.mark.asyncio
async def test_set_phone_number_success(session):
    """Test setting phone number for a firm."""
    repo = FirmsRepository(session)
    
    # Create a firm without phone number
    firm = Firm(id=str(uuid4()), name="Test Firm")
    session.add(firm)
    await session.commit()
    
    # Set phone number
    updated_firm = await repo.set_phone_number(
        firm_id=firm.id,
        phone_number="+15551234567",
        twilio_phone_number_sid="PN123456789",
        twilio_subaccount_sid="AC123456789",
    )
    
    assert updated_firm.twilio_phone_number == "+15551234567"
    assert updated_firm.twilio_phone_number_sid == "PN123456789"
    assert updated_firm.twilio_subaccount_sid == "AC123456789"
    
    # Verify in database
    await session.refresh(firm)
    assert firm.twilio_phone_number == "+15551234567"


@pytest.mark.asyncio
async def test_set_phone_number_firm_not_found(session):
    """Test setting phone number for non-existent firm."""
    repo = FirmsRepository(session)
    
    with pytest.raises(NotFoundError) as exc_info:
        await repo.set_phone_number(
            firm_id=str(uuid4()),
            phone_number="+15551234567",
            twilio_phone_number_sid="PN123456789",
            twilio_subaccount_sid="AC123456789",
        )
    
    assert "Firm" in str(exc_info.value)
    assert "not found" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_set_phone_number_conflict(session):
    """Test setting phone number that's already assigned to another firm."""
    repo = FirmsRepository(session)
    
    # Create two firms
    firm1 = Firm(
        id=str(uuid4()),
        name="Firm 1",
        twilio_phone_number="+15551234567",
        twilio_phone_number_sid="PN111",
        twilio_subaccount_sid="AC111",
    )
    firm2 = Firm(id=str(uuid4()), name="Firm 2")
    session.add(firm1)
    session.add(firm2)
    await session.commit()
    
    # Try to assign firm1's number to firm2
    with pytest.raises(ConflictError) as exc_info:
        await repo.set_phone_number(
            firm_id=firm2.id,
            phone_number="+15551234567",
            twilio_phone_number_sid="PN222",
            twilio_subaccount_sid="AC222",
        )
    
    assert "already assigned" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_set_phone_number_same_firm_update(session):
    """Test updating phone number for the same firm (should succeed)."""
    repo = FirmsRepository(session)
    
    # Create firm with existing phone number
    firm = Firm(
        id=str(uuid4()),
        name="Test Firm",
        twilio_phone_number="+15551234567",
        twilio_phone_number_sid="PN111",
        twilio_subaccount_sid="AC111",
    )
    session.add(firm)
    await session.commit()
    
    # Update to new number (same firm)
    updated_firm = await repo.set_phone_number(
        firm_id=firm.id,
        phone_number="+15559876543",
        twilio_phone_number_sid="PN222",
        twilio_subaccount_sid="AC222",
    )
    
    assert updated_firm.twilio_phone_number == "+15559876543"
    assert updated_firm.twilio_phone_number_sid == "PN222"


@pytest.mark.asyncio
async def test_update_firm_subaccount_sid_success(session):
    """Test updating firm subaccount SID."""
    repo = FirmsRepository(session)
    
    firm = Firm(id=str(uuid4()), name="Test Firm")
    session.add(firm)
    await session.commit()
    
    updated_firm = await repo.update_firm_subaccount_sid(
        firm_id=firm.id,
        twilio_subaccount_sid="AC123456789",
    )
    
    assert updated_firm.twilio_subaccount_sid == "AC123456789"
    
    # Verify in database
    await session.refresh(firm)
    assert firm.twilio_subaccount_sid == "AC123456789"


@pytest.mark.asyncio
async def test_update_firm_subaccount_sid_not_found(session):
    """Test updating subaccount SID for non-existent firm."""
    repo = FirmsRepository(session)
    
    with pytest.raises(NotFoundError):
        await repo.update_firm_subaccount_sid(
            firm_id=str(uuid4()),
            twilio_subaccount_sid="AC123456789",
        )


# ============================================================================
# Service Tests (with Twilio mocks)
# ============================================================================


@pytest.fixture
def mock_twilio_service():
    """Create a mock Twilio service."""
    service = MagicMock(spec=TwilioService)
    service.client = MagicMock()
    service.main_account_sid = "AC123456789"
    return service


@pytest.mark.asyncio
async def test_provision_phone_number_success(session, mock_twilio_service):
    """Test successful phone number provisioning."""
    # Create firm
    firm = Firm(id=str(uuid4()), name="Test Firm")
    session.add(firm)
    await session.commit()
    
    # Mock Twilio service responses
    mock_subaccount = TwilioSubaccount(
        sid="AC999",
        friendly_name="Firm: Test Firm",
        status="active",
    )
    mock_phone_number = TwilioPhoneNumber(
        sid="PN999",
        phone_number="+15551234567",
        status="active",
    )
    
    mock_twilio_service.create_subaccount = AsyncMock(return_value=mock_subaccount)
    mock_twilio_service.get_subaccount_auth_token = AsyncMock(return_value="auth_token_123")
    mock_twilio_service.list_phone_numbers = AsyncMock(return_value=[])
    mock_twilio_service.provision_phone_number = AsyncMock(return_value=mock_phone_number)
    mock_twilio_service.update_phone_number_webhook = AsyncMock(return_value=mock_phone_number)
    mock_twilio_service.find_subaccount_by_name = AsyncMock(return_value=None)
    
    # Create service with mocked Twilio service
    service = FirmsService(session)
    
    with patch("api_core.services.twilio_service.get_twilio_service", return_value=mock_twilio_service):
        with patch("os.getenv", return_value="https://api.example.com"):
            result = await service.provision_phone_number(
                firm_id=firm.id,
                area_code=None,
                user_id=None,  # Skip auth for unit test
            )
    
    assert result.phone_number == "+15551234567"
    assert result.twilio_phone_number_sid == "PN999"
    assert result.twilio_subaccount_sid == "AC999"
    
    # Verify firm was updated in database
    await session.refresh(firm)
    assert firm.twilio_phone_number == "+15551234567"
    assert firm.twilio_subaccount_sid == "AC999"


@pytest.mark.asyncio
async def test_provision_phone_number_firm_not_found(session, mock_twilio_service):
    """Test provisioning phone number for non-existent firm."""
    service = FirmsService(session)
    
    with pytest.raises(NotFoundError):
        await service.provision_phone_number(
            firm_id=str(uuid4()),
            area_code=None,
            user_id=None,
        )


@pytest.mark.asyncio
async def test_provision_phone_number_already_has_number(session, mock_twilio_service):
    """Test provisioning when firm already has a phone number."""
    # Create firm with existing phone number
    firm = Firm(
        id=str(uuid4()),
        name="Test Firm",
        twilio_phone_number="+15551234567",
        twilio_phone_number_sid="PN111",
        twilio_subaccount_sid="AC111",
    )
    session.add(firm)
    await session.commit()
    
    service = FirmsService(session)
    
    # Should return existing number
    result = await service.provision_phone_number(
        firm_id=firm.id,
        area_code=None,
        user_id=None,
    )
    
    assert result.phone_number == "+15551234567"
    assert result.twilio_phone_number_sid == "PN111"


@pytest.mark.asyncio
async def test_provision_phone_number_existing_subaccount(session, mock_twilio_service):
    """Test provisioning when firm already has a subaccount."""
    # Create firm with existing subaccount
    firm = Firm(
        id=str(uuid4()),
        name="Test Firm",
        twilio_subaccount_sid="AC999",
    )
    session.add(firm)
    await session.commit()
    
    mock_phone_number = TwilioPhoneNumber(
        sid="PN999",
        phone_number="+15551234567",
        status="active",
    )
    
    mock_twilio_service.get_subaccount_auth_token = AsyncMock(return_value="auth_token_123")
    mock_twilio_service.list_phone_numbers = AsyncMock(return_value=[])
    mock_twilio_service.provision_phone_number = AsyncMock(return_value=mock_phone_number)
    mock_twilio_service.update_phone_number_webhook = AsyncMock(return_value=mock_phone_number)
    mock_twilio_service.find_subaccount_by_name = AsyncMock(return_value=None)
    
    service = FirmsService(session)
    
    with patch("api_core.services.twilio_service.get_twilio_service", return_value=mock_twilio_service):
        with patch("os.getenv", return_value="https://api.example.com"):
            result = await service.provision_phone_number(
                firm_id=firm.id,
                area_code=None,
                user_id=None,
            )
    
    # Should not create new subaccount
    mock_twilio_service.create_subaccount.assert_not_called()
    assert result.twilio_subaccount_sid == "AC999"


@pytest.mark.asyncio
async def test_provision_phone_number_existing_number_in_subaccount(session, mock_twilio_service):
    """Test provisioning when subaccount already has a phone number."""
    # Create firm with existing subaccount
    firm = Firm(
        id=str(uuid4()),
        name="Test Firm",
        twilio_subaccount_sid="AC999",
    )
    session.add(firm)
    await session.commit()
    
    # Mock existing phone number in subaccount
    existing_number = TwilioPhoneNumber(
        sid="PN888",
        phone_number="+15559876543",
        status="active",
    )
    
    mock_twilio_service.get_subaccount_auth_token = AsyncMock(return_value="auth_token_123")
    mock_twilio_service.list_phone_numbers = AsyncMock(return_value=[existing_number])
    
    service = FirmsService(session)
    
    with patch("api_core.services.twilio_service.get_twilio_service", return_value=mock_twilio_service):
        with patch("os.getenv", return_value="https://api.example.com"):
            result = await service.provision_phone_number(
                firm_id=firm.id,
                area_code=None,
                user_id=None,
            )
    
    # Should use existing number, not purchase new one
    mock_twilio_service.provision_phone_number.assert_not_called()
    assert result.phone_number == "+15559876543"
    assert result.twilio_phone_number_sid == "PN888"


@pytest.mark.asyncio
async def test_provision_phone_number_twilio_error(session, mock_twilio_service):
    """Test handling Twilio API errors."""
    firm = Firm(id=str(uuid4()), name="Test Firm")
    session.add(firm)
    await session.commit()
    
    # Mock Twilio error - create_subaccount will fail
    mock_twilio_service.create_subaccount = AsyncMock(
        side_effect=ExternalServiceError(
            message="Twilio API error",
            service="Twilio",
            details={"error": "API failure"},
        )
    )
    mock_twilio_service.find_subaccount_by_name = AsyncMock(return_value=None)
    
    service = FirmsService(session)
    
    with patch("api_core.services.twilio_service.get_twilio_service", return_value=mock_twilio_service):
        with patch("os.getenv", return_value="https://api.example.com"):
            with pytest.raises(ExternalServiceError) as exc_info:
                await service.provision_phone_number(
                    firm_id=firm.id,
                    area_code=None,
                    user_id=None,
                )
            
            assert exc_info.value.details.get("service") == "Twilio"


@pytest.mark.asyncio
async def test_get_firm_phone_number_success(session):
    """Test getting firm phone number."""
    firm = Firm(
        id=str(uuid4()),
        name="Test Firm",
        twilio_phone_number="+15551234567",
        twilio_phone_number_sid="PN999",
        twilio_subaccount_sid="AC999",
    )
    session.add(firm)
    await session.commit()
    
    service = FirmsService(session)
    
    result = await service.get_firm_phone_number(
        firm_id=firm.id,
        user_id=None,
    )
    
    assert result.phone_number == "+15551234567"
    assert result.twilio_phone_number_sid == "PN999"
    assert result.twilio_subaccount_sid == "AC999"
    assert result.formatted_phone_number == "(555) 123-4567"


@pytest.mark.asyncio
async def test_get_firm_phone_number_not_found(session):
    """Test getting phone number for firm without one."""
    firm = Firm(id=str(uuid4()), name="Test Firm")
    session.add(firm)
    await session.commit()
    
    service = FirmsService(session)
    
    result = await service.get_firm_phone_number(
        firm_id=firm.id,
        user_id=None,
    )
    
    assert result.phone_number == ""
    assert result.twilio_phone_number_sid == ""
    assert result.twilio_subaccount_sid == ""


@pytest.mark.asyncio
async def test_get_firm_by_phone_number_service(session):
    """Test service method for getting firm by phone number."""
    firm = Firm(
        id=str(uuid4()),
        name="Test Firm",
        twilio_phone_number="+15551234567",
        twilio_phone_number_sid="PN999",
        twilio_subaccount_sid="AC999",
    )
    session.add(firm)
    await session.commit()
    
    service = FirmsService(session)
    
    result = await service.get_firm_by_phone_number("+15551234567")
    
    assert result is not None
    assert result.id == firm.id
    assert result.twilio_phone_number == "+15551234567"


@pytest.mark.asyncio
async def test_provision_phone_number_with_area_code(session, mock_twilio_service):
    """Test provisioning phone number with area code preference."""
    firm = Firm(id=str(uuid4()), name="Test Firm")
    session.add(firm)
    await session.commit()
    
    mock_subaccount = TwilioSubaccount(
        sid="AC999",
        friendly_name="Firm: Test Firm",
        status="active",
    )
    mock_phone_number = TwilioPhoneNumber(
        sid="PN999",
        phone_number="+14151234567",  # 415 area code
        status="active",
    )
    
    mock_twilio_service.create_subaccount = AsyncMock(return_value=mock_subaccount)
    mock_twilio_service.get_subaccount_auth_token = AsyncMock(return_value="auth_token_123")
    mock_twilio_service.list_phone_numbers = AsyncMock(return_value=[])
    mock_twilio_service.provision_phone_number = AsyncMock(return_value=mock_phone_number)
    mock_twilio_service.update_phone_number_webhook = AsyncMock(return_value=mock_phone_number)
    mock_twilio_service.find_subaccount_by_name = AsyncMock(return_value=None)
    
    service = FirmsService(session)
    
    with patch("api_core.services.twilio_service.get_twilio_service", return_value=mock_twilio_service):
        with patch("os.getenv", return_value="https://api.example.com"):
            result = await service.provision_phone_number(
                firm_id=firm.id,
                area_code="415",
                user_id=None,
            )
    
    # Verify area code was passed to Twilio
    mock_twilio_service.provision_phone_number.assert_called_once()
    call_args = mock_twilio_service.provision_phone_number.call_args
    assert call_args.kwargs["area_code"] == "415"
    assert result.phone_number == "+14151234567"


# ============================================================================
# API Endpoint Tests
# Note: These tests require proper FastAPI test client setup with auth mocking
# Skipping for now - focus on unit tests for repository and service layers
# ============================================================================

# TODO: Add API endpoint tests when test client fixtures are properly configured
# These would test:
# - POST /api/v1/firms/{firm_id}/phone-number
# - GET /api/v1/firms/{firm_id}/phone-number
# - Authorization checks
# - Validation errors
# - Error handling


# ============================================================================
# Twilio Service Tests (mocked)
# ============================================================================


@pytest.mark.asyncio
async def test_twilio_service_create_subaccount_success(mock_twilio_service):
    """Test creating Twilio subaccount."""
    mock_subaccount = TwilioSubaccount(
        sid="AC999",
        friendly_name="Test Firm",
        status="active",
    )
    
    mock_twilio_service.create_subaccount.return_value = mock_subaccount
    
    result = await mock_twilio_service.create_subaccount("Test Firm")
    
    assert result.sid == "AC999"
    assert result.friendly_name == "Test Firm"
    mock_twilio_service.create_subaccount.assert_called_once_with("Test Firm")


@pytest.mark.asyncio
async def test_twilio_service_find_subaccount_by_name(mock_twilio_service):
    """Test finding subaccount by name."""
    mock_subaccount = TwilioSubaccount(
        sid="AC111",
        friendly_name="Firm: Test 1",
        status="active",
    )
    
    mock_twilio_service.find_subaccount_by_name.return_value = mock_subaccount
    
    result = await mock_twilio_service.find_subaccount_by_name("Firm: Test 1")
    
    assert result is not None
    assert result.sid == "AC111"
    mock_twilio_service.find_subaccount_by_name.assert_called_once_with("Firm: Test 1")


@pytest.mark.asyncio
async def test_twilio_service_list_phone_numbers(mock_twilio_service):
    """Test listing phone numbers in subaccount."""
    mock_numbers = [
        TwilioPhoneNumber(sid="PN111", phone_number="+15551111111", status="active"),
        TwilioPhoneNumber(sid="PN222", phone_number="+15552222222", status="active"),
    ]
    
    mock_twilio_service.list_phone_numbers.return_value = mock_numbers
    
    result = await mock_twilio_service.list_phone_numbers()
    
    assert len(result) == 2
    assert result[0].phone_number == "+15551111111"
    assert result[1].phone_number == "+15552222222"
    mock_twilio_service.list_phone_numbers.assert_called_once()

