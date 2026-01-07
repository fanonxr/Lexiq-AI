"""SQLAlchemy database models."""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Base class for all database models."""

    pass


class User(Base):
    """User database model."""

    __tablename__ = "users"

    # Primary key
    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        index=True,
    )

    # Authentication fields
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # User profile fields
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    given_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    family_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Azure AD B2C integration
    azure_ad_object_id: Mapped[Optional[str]] = mapped_column(
        String(36), unique=True, index=True, nullable=True
    )
    azure_ad_tenant_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)

    # Google OAuth integration
    google_id: Mapped[Optional[str]] = mapped_column(
        String(255), unique=True, index=True, nullable=True
    )
    google_email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)

    # Account status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
    # Account lockout (for failed login attempts)
    failed_login_attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    locked_until: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Email verification
    email_verification_token: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    email_verified_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Password reset
    password_reset_token: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    password_reset_expires_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )
    last_login_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Additional metadata
    metadata_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON string for extra data

    # Firm relationship (multi-tenant support)
    firm_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("firms.id", ondelete="SET NULL"), nullable=True, index=True
    )

    # Relationships (defined after related models)
    firm: Mapped[Optional["Firm"]] = relationship("Firm", back_populates="users")
    subscriptions: Mapped[list["Subscription"]] = relationship(
        "Subscription", back_populates="user", cascade="all, delete-orphan"
    )
    invoices: Mapped[list["Invoice"]] = relationship(
        "Invoice", back_populates="user", cascade="all, delete-orphan"
    )
    usage_records: Mapped[list["UsageRecord"]] = relationship(
        "UsageRecord", back_populates="user", cascade="all, delete-orphan"
    )
    knowledge_base_files: Mapped[list["KnowledgeBaseFile"]] = relationship(
        "KnowledgeBaseFile", back_populates="user", cascade="all, delete-orphan"
    )
    conversations: Mapped[list["Conversation"]] = relationship(
        "Conversation", back_populates="user", cascade="all, delete-orphan"
    )
    calls: Mapped[list["Call"]] = relationship(
        "Call", back_populates="user", cascade="all, delete-orphan"
    )
    agent_configs: Mapped[list["AgentConfig"]] = relationship(
        "AgentConfig", back_populates="user", cascade="all, delete-orphan"
    )
    calendar_integrations: Mapped[list["CalendarIntegration"]] = relationship(
        "CalendarIntegration", back_populates="user", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        """String representation of User."""
        return f"<User(id={self.id}, email={self.email}, name={self.name})>"


class Plan(Base):
    """Subscription plan database model."""

    __tablename__ = "plans"

    # Primary key
    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        index=True,
    )

    # Plan details
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True, index=True)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Pricing
    price_monthly: Mapped[Optional[Numeric]] = mapped_column(Numeric(10, 2), nullable=True)
    price_yearly: Mapped[Optional[Numeric]] = mapped_column(Numeric(10, 2), nullable=True)
    currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)

    # Features and limits
    features_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    max_calls_per_month: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    max_users: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    max_storage_gb: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Plan status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_public: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    # Relationships
    subscriptions: Mapped[list["Subscription"]] = relationship(
        "Subscription", back_populates="plan", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        """String representation of Plan."""
        return f"<Plan(id={self.id}, name={self.name})>"


class Subscription(Base):
    """User subscription database model."""

    __tablename__ = "subscriptions"

    # Primary key
    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        index=True,
    )

    # Foreign keys
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    plan_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("plans.id", ondelete="RESTRICT"), nullable=False, index=True
    )

    # Subscription status (active, canceled, past_due, trialing, etc.)
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        default="active",
    )

    # Billing cycle (monthly or yearly)
    billing_cycle: Mapped[str] = mapped_column(String(20), nullable=False, default="monthly")
    current_period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    current_period_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    # Payment provider integration (stripe, azure_billing, etc.)
    payment_provider: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    payment_provider_subscription_id: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True, index=True
    )
    payment_method_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Cancellation
    canceled_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    cancel_at_period_end: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Trial
    trial_start: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    trial_end: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    # Additional metadata
    metadata_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="subscriptions")
    plan: Mapped["Plan"] = relationship("Plan", back_populates="subscriptions")
    invoices: Mapped[list["Invoice"]] = relationship(
        "Invoice", back_populates="subscription", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        """String representation of Subscription."""
        return f"<Subscription(id={self.id}, user_id={self.user_id}, status={self.status})>"


class Invoice(Base):
    """Billing invoice database model."""

    __tablename__ = "invoices"

    # Primary key
    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        index=True,
    )

    # Foreign keys
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    subscription_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("subscriptions.id", ondelete="SET NULL"), nullable=True, index=True
    )

    # Invoice details
    invoice_number: Mapped[str] = mapped_column(
        String(100), unique=True, nullable=False, index=True
    )
    amount: Mapped[Numeric] = mapped_column(Numeric(10, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)
    tax_amount: Mapped[Optional[Numeric]] = mapped_column(Numeric(10, 2), nullable=True)

    # Invoice status (draft, open, paid, void, uncollectible)
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        default="draft",
    )

    # Payment
    paid_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    due_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    # Payment provider integration
    payment_provider: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    payment_provider_invoice_id: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True, index=True
    )
    payment_provider_payment_intent_id: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True
    )

    # Invoice items (stored as JSON)
    items_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="invoices")
    subscription: Mapped[Optional["Subscription"]] = relationship(
        "Subscription", back_populates="invoices"
    )

    def __repr__(self) -> str:
        """String representation of Invoice."""
        return f"<Invoice(id={self.id}, invoice_number={self.invoice_number}, status={self.status})>"


class UsageRecord(Base):
    """Feature usage tracking database model."""

    __tablename__ = "usage_records"

    # Primary key
    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        index=True,
    )

    # Foreign key
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Usage details (calls, storage, api_requests, etc.)
    feature: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    unit: Mapped[str] = mapped_column(String(50), nullable=False, default="count")

    # Time period
    period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    period_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    # Metadata
    metadata_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="usage_records")

    def __repr__(self) -> str:
        """String representation of UsageRecord."""
        return f"<UsageRecord(id={self.id}, user_id={self.user_id}, feature={self.feature})>"


class KnowledgeBaseFile(Base):
    """Knowledge base file model for RAG document storage."""

    __tablename__ = "knowledge_base_files"

    # Primary key
    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        index=True,
    )

    # Foreign keys
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    firm_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True, index=True)

    # File metadata
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_type: Mapped[str] = mapped_column(String(50), nullable=False)  # pdf, docx, txt, etc.
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)  # bytes
    storage_path: Mapped[str] = mapped_column(String(500), nullable=False)  # Blob Storage path

    # Processing status
    status: Mapped[str] = mapped_column(
        String(50),
        default="pending",
        nullable=False,
        index=True,
    )  # pending, processing, indexed, failed
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Qdrant integration
    qdrant_collection: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    qdrant_point_ids: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True
    )  # JSON array of point IDs

    # Timestamps
    indexed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="knowledge_base_files")

    def __repr__(self) -> str:
        """String representation of KnowledgeBaseFile."""
        return f"<KnowledgeBaseFile(id={self.id}, filename={self.filename}, status={self.status})>"


class Appointment(Base):
    """LexiqAI-native appointment booking model (MVP).

    This is intentionally minimal for Phase 5 tool execution:
    - Internal booking via Cognitive Orchestrator
    - Idempotent creation via idempotency_key
    """

    __tablename__ = "appointments"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        index=True,
    )

    # Tenant scope
    firm_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True, index=True)

    # Optional link to an authenticated user (future)
    created_by_user_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )

    # Timing
    start_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    end_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    timezone: Mapped[str] = mapped_column(String(64), nullable=False)
    duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False)

    # Details
    title: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="booked", index=True)

    # Contact info (LexiqAI-native)
    contact_full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    contact_email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    contact_phone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # Idempotency
    idempotency_key: Mapped[str] = mapped_column(String(128), nullable=False, unique=True, index=True)

    # Calendar integration source tracking
    source_calendar_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("calendar_integrations.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    source_event_id: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True, index=True
    )  # Outlook/Google event ID

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # Relationships
    source_calendar: Mapped[Optional["CalendarIntegration"]] = relationship(
        "CalendarIntegration"
    )

    def __repr__(self) -> str:
        return f"<Appointment(id={self.id}, firm_id={self.firm_id}, start_at={self.start_at})>"


class Lead(Base):
    """LexiqAI-native lead/intake record (MVP).

    Created via Cognitive Orchestrator tools with confirmation + idempotency.
    """

    __tablename__ = "leads"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        index=True,
    )

    # Tenant scope
    firm_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True, index=True)

    # Optional link to authenticated user (future)
    created_by_user_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )

    # Contact / intake
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    matter_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    status: Mapped[str] = mapped_column(String(50), nullable=False, default="new", index=True)

    # Idempotency
    idempotency_key: Mapped[str] = mapped_column(String(128), nullable=False, unique=True, index=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    def __repr__(self) -> str:
        return f"<Lead(id={self.id}, firm_id={self.firm_id}, full_name={self.full_name})>"


class Notification(Base):
    """LexiqAI-native notification outbox record (MVP).

    For Phase 5 tool execution, we record notifications that should be sent.
    Provider delivery (SendGrid/Twilio/etc.) can be implemented later via Integration Worker.
    """

    __tablename__ = "notifications"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        index=True,
    )

    firm_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True, index=True)
    created_by_user_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )

    channel: Mapped[str] = mapped_column(String(20), nullable=False, index=True)  # email|sms
    to: Mapped[str] = mapped_column(String(255), nullable=False)
    subject: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    message: Mapped[str] = mapped_column(Text, nullable=False)

    status: Mapped[str] = mapped_column(String(50), nullable=False, default="queued", index=True)

    # Idempotency
    idempotency_key: Mapped[str] = mapped_column(String(128), nullable=False, unique=True, index=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    def __repr__(self) -> str:
        return f"<Notification(id={self.id}, channel={self.channel}, to={self.to}, status={self.status})>"


class Firm(Base):
    """Firm/Organization model for multi-tenant support."""

    __tablename__ = "firms"

    # Primary key
    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        index=True,
    )

    # Firm details
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    domain: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, unique=True, index=True)

    # AI Configuration
    default_model: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True
    )  # Override global default
    system_prompt: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # Custom persona
    specialties: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True
    )  # JSON array of specialties

    # Qdrant configuration
    qdrant_collection: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True, unique=True, index=True
    )

    # Twilio Integration
    twilio_phone_number: Mapped[Optional[str]] = mapped_column(
        String(20), nullable=True, unique=True, index=True
    )  # E.164 format: +15551234567
    twilio_phone_number_sid: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True, unique=True, index=True
    )  # Twilio Phone Number SID (e.g., PNxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx)
    twilio_subaccount_sid: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True, unique=True, index=True
    )  # Twilio Subaccount SID (e.g., ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx) - for billing/organization

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    # Relationships
    users: Mapped[list["User"]] = relationship("User", back_populates="firm")
    conversations: Mapped[list["Conversation"]] = relationship(
        "Conversation", back_populates="firm"
    )

    def __repr__(self) -> str:
        phone_info = f", phone={self.twilio_phone_number}" if self.twilio_phone_number else ""
        return f"<Firm(id={self.id}, name={self.name}{phone_info})>"


class AgentConfig(Base):
    """Agent configuration database model for user/firm-specific agent settings."""

    __tablename__ = "agent_configs"

    # Primary key
    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        index=True,
    )

    # Foreign keys
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    firm_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("firms.id", ondelete="SET NULL"), nullable=True, index=True
    )

    # Voice configuration
    voice_id: Mapped[str] = mapped_column(String(100), nullable=False, default="1")

    # Scripts
    greeting_script: Mapped[str] = mapped_column(
        Text, nullable=False, default="Hello, thank you for calling. How can I assist you today?"
    )
    closing_script: Mapped[str] = mapped_column(
        Text, nullable=False, default="Thank you for calling. Have a great day!"
    )
    transfer_script: Mapped[str] = mapped_column(
        Text, nullable=False, default="Let me transfer you to someone who can better assist you."
    )

    # Behavior settings
    auto_respond: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    record_calls: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    auto_transcribe: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    enable_voicemail: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="agent_configs")
    firm: Mapped[Optional["Firm"]] = relationship("Firm")

    def __repr__(self) -> str:
        return f"<AgentConfig(id={self.id}, user_id={self.user_id}, firm_id={self.firm_id})>"


class CalendarIntegration(Base):
    """Calendar integration database model (Outlook/Google Calendar)."""

    __tablename__ = "calendar_integrations"

    # Primary key
    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        index=True,
    )

    # Foreign key
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Integration details
    integration_type: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True
    )  # "outlook" or "google"

    # OAuth tokens (should be encrypted in production)
    access_token: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # Encrypted
    refresh_token: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # Encrypted
    token_expires_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Calendar information
    calendar_id: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True
    )  # Outlook calendar ID
    email: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True
    )  # User's email for this calendar

    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_synced_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    sync_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Webhook subscription (for real-time calendar event notifications)
    webhook_subscription_id: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True, index=True
    )  # Microsoft Graph subscription ID
    webhook_subscription_expires_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )  # When subscription expires (must be renewed before expiration)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="calendar_integrations")

    def __repr__(self) -> str:
        return f"<CalendarIntegration(id={self.id}, user_id={self.user_id}, type={self.integration_type})>"


class Conversation(Base):
    """Conversation database model for tracking AI conversations."""

    __tablename__ = "conversations"

    # Primary key
    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        index=True,
    )

    # Foreign keys
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    firm_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("firms.id", ondelete="SET NULL"), nullable=True, index=True
    )
    call_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True, index=True)

    # Conversation metadata
    status: Mapped[str] = mapped_column(String(50), default="active", nullable=False, index=True)
    model_used: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    total_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Timestamps
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )
    ended_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="conversations")
    firm: Mapped[Optional["Firm"]] = relationship("Firm", back_populates="conversations")
    messages: Mapped[list["ConversationMessage"]] = relationship(
        "ConversationMessage", back_populates="conversation", cascade="all, delete-orphan"
    )
    calls: Mapped[list["Call"]] = relationship(
        "Call", back_populates="conversation"
    )

    def __repr__(self) -> str:
        return f"<Conversation(id={self.id}, user_id={self.user_id}, status={self.status})>"


class ConversationMessage(Base):
    """Individual message within a conversation."""

    __tablename__ = "conversation_messages"

    # Primary key
    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        index=True,
    )

    # Foreign key
    conversation_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Message content
    role: Mapped[str] = mapped_column(String(50), nullable=False)  # user, assistant, system, tool
    content: Mapped[str] = mapped_column(Text, nullable=False)
    tool_calls: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON array
    tool_call_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Metadata
    tokens: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    model: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )

    # Relationships
    conversation: Mapped["Conversation"] = relationship("Conversation", back_populates="messages")

    def __repr__(self) -> str:
        return f"<ConversationMessage(id={self.id}, conversation_id={self.conversation_id}, role={self.role})>"


class Call(Base):
    """Call database model for tracking phone calls."""

    __tablename__ = "calls"

    # Primary key
    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        index=True,
    )

    # Foreign keys
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    conversation_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("conversations.id", ondelete="SET NULL"), nullable=True, index=True
    )

    # Call details
    phone_number: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    direction: Mapped[str] = mapped_column(String(10), nullable=False)  # inbound, outbound
    status: Mapped[str] = mapped_column(
        String(50), default="initiated", nullable=False, index=True
    )  # initiated, ringing, in-progress, completed, failed, missed

    # Call metadata
    duration_seconds: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    recording_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    transcript: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Twilio integration
    twilio_call_sid: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True, unique=True, index=True
    )

    # Timestamps
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    answered_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    ended_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="calls")
    conversation: Mapped[Optional["Conversation"]] = relationship(
        "Conversation", back_populates="calls"
    )

    def __repr__(self) -> str:
        return f"<Call(id={self.id}, user_id={self.user_id}, status={self.status}, phone_number={self.phone_number})>"


class FirmPersona(Base):
    """Firm persona / system prompt overrides (MVP).

    This provides a Core API-backed source of truth for firm-specific system prompts.
    Note: This is a separate table from Firm to allow for persona versioning/history in the future.
    """

    __tablename__ = "firm_personas"

    firm_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("firms.id", ondelete="CASCADE"), primary_key=True
    )
    system_prompt: Mapped[str] = mapped_column(Text, nullable=False, default="")

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    def __repr__(self) -> str:
        return f"<FirmPersona(firm_id={self.firm_id})>"


class Client(Base):
    """Client database model for tracking callers with multiple identifiers.
    
    This model supports the Long-Term Memory feature, allowing the system to
    recognize returning callers and personalize their experience.
    
    Supports multiple identification methods:
    - Phone number (primary, always required)
    - Email (secondary, collected during conversation)
    - External CRM ID (for integration with existing systems)
    """

    __tablename__ = "clients"

    # Primary key
    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        index=True,
    )

    # Foreign key
    firm_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("firms.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Primary identifier (always present)
    phone_number: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    
    # Secondary identifiers (optional, collected over time)
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    external_crm_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    
    # Personal information
    first_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    last_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )
    last_called_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )

    # Relationships
    memories: Mapped[list["ClientMemory"]] = relationship(
        "ClientMemory", back_populates="client", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        name = f"{self.first_name or ''} {self.last_name or ''}".strip()
        name_str = f", name={name}" if name else ""
        email_str = f", email={self.email}" if self.email else ""
        return f"<Client(id={self.id}, phone={self.phone_number}{name_str}{email_str})>"


class ClientMemory(Base):
    """Client memory database model for storing conversation summaries.
    
    Stores AI-generated summaries of past interactions. Embeddings are stored
    in Qdrant for semantic search, not in PostgreSQL.
    """

    __tablename__ = "client_memories"

    # Primary key
    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        index=True,
    )

    # Foreign key
    client_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Memory content
    summary_text: Mapped[str] = mapped_column(Text, nullable=False)
    
    # Qdrant point ID (reference to vector in Qdrant)
    qdrant_point_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False, index=True
    )

    # Relationships
    client: Mapped["Client"] = relationship("Client", back_populates="memories")

    def __repr__(self) -> str:
        preview = self.summary_text[:50] + "..." if len(self.summary_text) > 50 else self.summary_text
        return f"<ClientMemory(id={self.id}, client_id={self.client_id}, summary='{preview}')>"
