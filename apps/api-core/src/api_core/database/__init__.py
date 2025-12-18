"""Database connection and session management."""

from api_core.database.connection import (
    check_connection,
    close_engine,
    create_engine,
    get_engine,
)
from api_core.database.models import (
    Base,
    Appointment,
    Call,
    Conversation,
    ConversationMessage,
    Firm,
    FirmPersona,
    Invoice,
    KnowledgeBaseFile,
    Lead,
    Notification,
    Plan,
    Subscription,
    UsageRecord,
    User,
)
from api_core.database.session import (
    close_db,
    get_session,
    get_session_context,
    get_session_factory,
    init_db,
)

__all__ = [
    # Models
    "Base",
    "User",
    "Firm",
    "FirmPersona",
    "Plan",
    "Subscription",
    "Invoice",
    "UsageRecord",
    "KnowledgeBaseFile",
    "Appointment",
    "Lead",
    "Notification",
    "Conversation",
    "ConversationMessage",
    "Call",
    # Connection
    "get_engine",
    "create_engine",
    "close_engine",
    "check_connection",
    # Session
    "get_session",
    "get_session_context",
    "get_session_factory",
    "init_db",
    "close_db",
]
