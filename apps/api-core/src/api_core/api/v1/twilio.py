"""Twilio webhook endpoints for call handling."""

from __future__ import annotations

import logging
import os
from typing import Dict

from fastapi import APIRouter, Form, Header, Request, status
from fastapi.responses import Response
from sqlalchemy import select

try:
    from twilio.request_validator import RequestValidator
except ImportError:
    # Fallback: Try alternative import path (for older Twilio SDK versions)
    try:
        from twilio.util import RequestValidator
    except ImportError:
        # If RequestValidator is not available, we'll log an error
        # The validation function will handle this gracefully
        RequestValidator = None
        # Note: logger is defined below, so we'll log the warning in the validation function

from api_core.database.models import User
from api_core.database.session import get_session_context
from api_core.models.calls import CallCreateRequest
from api_core.services.calls_service import get_calls_service
from api_core.services.firms_service import get_firms_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/twilio", tags=["twilio"])


def validate_twilio_request(
    request: Request,
    twilio_signature: str | None,
    form_data: Dict[str, str],
) -> bool:
    """
    Validate that the incoming request is from Twilio.
    
    Uses Twilio's signature validation to ensure the request is authentic.
    This prevents unauthorized webhook calls.
    
    According to Twilio documentation:
    - The signature is calculated using HMAC-SHA1
    - Uses the auth token, full URL (including query params), and all form parameters
    - The signature is in the X-Twilio-Signature header
    
    Reference: https://www.twilio.com/docs/usage/webhooks/webhooks-security
    
    Args:
        request: FastAPI Request object
        twilio_signature: X-Twilio-Signature header value
        form_data: All form parameters from the request
        
    Returns:
        True if signature is valid, False otherwise
    """
    auth_token = os.getenv("TWILIO_AUTH_TOKEN")
    
    if not auth_token:
        logger.warning("TWILIO_AUTH_TOKEN not configured. Skipping signature validation.")
        # In production, you should fail here. For development, we'll allow it.
        # TODO: Make this stricter in production
        return True
    
    if not twilio_signature:
        logger.warning("Missing X-Twilio-Signature header. Request may not be from Twilio.")
        return False
    
    if RequestValidator is None:
        logger.error(
            "Twilio RequestValidator not available. "
            "Please ensure twilio package is installed. "
            "Signature validation cannot be performed."
        )
        return False
    
    try:
        # Get the full URL that Twilio called
        # This must be the exact URL including scheme, host, path, and query parameters
        # FastAPI's request.url includes all of this
        url = str(request.url)
        
        # Create validator with auth token
        validator = RequestValidator(auth_token)
        
        # Validate the request
        # Twilio sends form-encoded data (application/x-www-form-urlencoded)
        # The validator needs:
        # 1. The full URL (as Twilio called it)
        # 2. All form parameters (as a dict)
        # 3. The signature from X-Twilio-Signature header
        is_valid = validator.validate(url, form_data, twilio_signature)
        
        if not is_valid:
            logger.warning(
                f"Twilio signature validation failed. "
                f"URL: {url}, Signature: {twilio_signature[:20]}... "
                f"Form params: {list(form_data.keys())}"
            )
        else:
            logger.debug("Twilio signature validation passed")
        
        return is_valid
    except Exception as e:
        logger.error(f"Error validating Twilio signature: {e}", exc_info=True)
        return False


@router.post("/webhook", status_code=status.HTTP_200_OK)
async def handle_twilio_webhook(
    request: Request,
    CallSid: str = Form(...),
    From: str = Form(...),  # Caller's number
    To: str = Form(...),  # Firm's number (the number being called)
    CallStatus: str = Form(...),
    x_twilio_signature: str | None = Header(default=None, alias="X-Twilio-Signature"),
):
    """
    Handle Twilio webhook for incoming calls.
    
    This endpoint is called by Twilio when a call is initiated.
    It validates the request signature, looks up the firm by the "To" phone number,
    and returns TwiML to start the Media Stream.
    
    Args:
        request: FastAPI Request object (for signature validation)
        CallSid: Twilio Call SID
        From: Caller's phone number (E.164 format)
        To: Firm's phone number (E.164 format)
        CallStatus: Call status (ringing, in-progress, etc.)
        x_twilio_signature: X-Twilio-Signature header for request validation
    """
    try:
        # Get all form data for signature validation
        # Twilio sends all parameters, and we need ALL of them for validation
        # Important: Twilio may add new parameters without notice, so we must include all
        form_data = await request.form()
        form_dict = {key: value for key, value in form_data.items()}
        
        # Validate Twilio signature
        # Note: In development, you might want to skip this for testing
        # In production, this should always be enabled
        # Set TWILIO_VALIDATE_SIGNATURES=false only for local development/testing
        validate_signatures = os.getenv("TWILIO_VALIDATE_SIGNATURES", "true").lower() == "true"
        
        if validate_signatures:
            is_valid = validate_twilio_request(request, x_twilio_signature, form_dict)
            if not is_valid:
                logger.error(
                    f"Invalid Twilio signature. Rejecting webhook. "
                    f"CallSid: {CallSid}, From: {From}, To: {To}"
                )
                # Return error TwiML - don't process the call
                # Use 403 to indicate authentication/authorization failure
                return Response(
                    content='<?xml version="1.0" encoding="UTF-8"?><Response><Say>Invalid request signature.</Say><Hangup/></Response>',
                    media_type="application/xml",
                    status_code=status.HTTP_403_FORBIDDEN,
                )
        else:
            logger.warning(
                "Twilio signature validation is disabled. "
                "This should only be used in development/testing. "
                "Enable validation in production!"
            )
        
        async with get_session_context() as session:
            # Look up firm by phone number
            firms_service = get_firms_service(session)
            firm = await firms_service.get_firm_by_phone_number(To)

            if not firm:
                logger.warning(f"No firm found for phone number: {To}")
                # Return TwiML to reject call
                return Response(
                    content='<?xml version="1.0" encoding="UTF-8"?><Response><Reject/></Response>',
                    media_type="application/xml",
                )

            # Get primary user for the firm (first user, or admin)
            # For now, we'll use the first user. In the future, we might
            # have a firm admin or default user.
            user_result = await session.execute(
                select(User).where(User.firm_id == firm.id).limit(1)
            )
            user = user_result.scalar_one_or_none()

            if not user:
                logger.warning(f"No user found for firm: {firm.id}")
                return Response(
                    content='<?xml version="1.0" encoding="UTF-8"?><Response><Reject/></Response>',
                    media_type="application/xml",
                )

            # Check if user has active subscription (blocks calls if subscription is canceled/inactive)
            from api_core.services.billing_service import get_billing_service
            
            billing_service = get_billing_service(session)
            can_make_calls, reason = await billing_service.can_user_make_calls(user.id)
            
            if not can_make_calls:
                logger.warning(
                    f"Call blocked for user {user.id} (firm: {firm.id}). Reason: {reason}. "
                    f"CallSid: {CallSid}, From: {From}"
                )
                # Return TwiML with a message explaining the call cannot be completed
                # and then hang up
                return Response(
                    content='<?xml version="1.0" encoding="UTF-8"?>'
                           '<Response>'
                           '<Say voice="alice">We apologize, but your subscription is not active. '
                           'Please contact support to reactivate your account. Goodbye.</Say>'
                           '<Hangup/>'
                           '</Response>',
                    media_type="application/xml",
                )

            # Create call record in database
            calls_service = get_calls_service(session)
            call_request = CallCreateRequest(
                user_id=user.id,
                phone_number=From,  # Caller's number
                direction="inbound",
                status=CallStatus,
                twilio_call_sid=CallSid,
            )
            call = await calls_service.create_call(call_request)

            # Get voice gateway URL from environment variable
            # Default to localhost for development
            voice_gateway_url = os.getenv(
                "VOICE_GATEWAY_URL", "wss://localhost:8080/streams/twilio"
            )

            # Return TwiML to start Media Stream
            # Pass firm_id, user_id, and call_id as custom parameters
            twiml = f'''<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Start>
        <Stream url="{voice_gateway_url}" track="both_tracks">
            <Parameter name="firm_id" value="{firm.id}"/>
            <Parameter name="user_id" value="{user.id}"/>
            <Parameter name="call_id" value="{call.id}"/>
        </Stream>
    </Start>
    <Say voice="alice">Hello, how can I help you today?</Say>
</Response>'''

            return Response(content=twiml, media_type="application/xml")

    except Exception as e:
        logger.error(f"Error handling Twilio webhook: {e}", exc_info=True)
        # Return error TwiML
        return Response(
            content='<?xml version="1.0" encoding="UTF-8"?><Response><Say>Sorry, we are experiencing technical difficulties.</Say><Hangup/></Response>',
            media_type="application/xml",
        )

