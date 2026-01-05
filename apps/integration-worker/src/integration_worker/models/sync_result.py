"""Pydantic models for sync results."""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class SyncResult(BaseModel):
    """Result of a calendar sync operation."""
    
    success: bool = Field(..., description="Whether the sync was successful")
    integration_id: str = Field(..., description="Calendar integration ID")
    appointments_synced: int = Field(default=0, description="Number of appointments synced")
    appointments_updated: int = Field(default=0, description="Number of appointments updated")
    appointments_deleted: int = Field(default=0, description="Number of appointments deleted")
    errors: List[str] = Field(default_factory=list, description="List of errors encountered")
    started_at: Optional[datetime] = Field(default=None, description="When sync started")
    completed_at: Optional[datetime] = Field(default=None, description="When sync completed")
    
    @property
    def total_changes(self) -> int:
        """Total number of changes made."""
        return self.appointments_synced + self.appointments_updated + self.appointments_deleted
    
    @property
    def has_errors(self) -> bool:
        """Whether any errors occurred."""
        return len(self.errors) > 0


class TokenRefreshResult(BaseModel):
    """Result of a token refresh operation."""
    
    success: bool = Field(..., description="Whether the refresh was successful")
    integration_id: str = Field(..., description="Calendar integration ID")
    error: Optional[str] = Field(default=None, description="Error message if failed")
    expires_at: Optional[datetime] = Field(default=None, description="New token expiration time")

