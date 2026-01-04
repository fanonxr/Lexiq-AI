"""Enhanced Client Model with Multiple Identifiers

This is an OPTIONAL enhancement for future consideration.
The current phone-based lookup is fine for MVP!
"""

from sqlalchemy import String, Index
from sqlalchemy.orm import Mapped, mapped_column

class Client(Base):
    """Enhanced client model with multiple identification methods."""
    
    __tablename__ = "clients"
    
    # Primary key (stable)
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    
    # Firm relationship
    firm_id: Mapped[str] = mapped_column(String(36), ForeignKey("firms.id"))
    
    # Phone (primary identifier) - KEEP THIS
    phone_number: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    
    # Optional: Email (if collected)
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    
    # Optional: External CRM ID (if they have a CRM)
    external_crm_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    
    # Name fields
    first_name: Mapped[Optional[str]] = mapped_column(String(100))
    last_name: Mapped[Optional[str]] = mapped_column(String(100))
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    last_called_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    
    # Composite indexes
    __table_args__ = (
        Index('ix_clients_firm_phone', 'firm_id', 'phone_number', unique=True),
        Index('ix_clients_firm_email', 'firm_id', 'email', unique=False),  # Not unique (optional field)
    )

# Lookup logic with fallbacks
async def identify_client_enhanced(
    firm_id: str,
    phone_number: str,
    email: Optional[str] = None,
    external_id: Optional[str] = None
) -> Client:
    """
    Identify client with multiple fallback strategies.
    
    Priority:
    1. Phone number (primary)
    2. Email (if provided)
    3. External CRM ID (if provided)
    """
    # Try phone first (fastest, most reliable)
    client = await find_by_phone(firm_id, phone_number)
    if client:
        return client
    
    # Fallback to email if provided
    if email:
        client = await find_by_email(firm_id, email)
        if client:
            # Update phone number!
            client.phone_number = phone_number
            await session.commit()
            return client
    
    # Fallback to external ID
    if external_id:
        client = await find_by_external_id(firm_id, external_id)
        if client:
            return client
    
    # Create new client
    return await create_client(firm_id, phone_number, email, external_id)

