"""Tests for sync result models."""

import pytest
from datetime import datetime, timezone

from integration_worker.models.sync_result import SyncResult, TokenRefreshResult


class TestSyncResult:
    """Test suite for SyncResult model."""
    
    def test_sync_result_creation(self):
        """Test creating a SyncResult."""
        result = SyncResult(
            success=True,
            integration_id="test-id",
            appointments_synced=5,
            appointments_updated=2,
            appointments_deleted=1,
            errors=[],
        )
        
        assert result.success is True
        assert result.integration_id == "test-id"
        assert result.appointments_synced == 5
        assert result.appointments_updated == 2
        assert result.appointments_deleted == 1
        assert len(result.errors) == 0
    
    def test_sync_result_total_changes(self):
        """Test total_changes property."""
        result = SyncResult(
            success=True,
            integration_id="test-id",
            appointments_synced=5,
            appointments_updated=2,
            appointments_deleted=1,
        )
        
        assert result.total_changes == 8  # 5 + 2 + 1
    
    def test_sync_result_has_errors(self):
        """Test has_errors property."""
        result_no_errors = SyncResult(
            success=True,
            integration_id="test-id",
            errors=[],
        )
        assert result_no_errors.has_errors is False
        
        result_with_errors = SyncResult(
            success=False,
            integration_id="test-id",
            errors=["Error 1", "Error 2"],
        )
        assert result_with_errors.has_errors is True
        assert len(result_with_errors.errors) == 2
    
    def test_sync_result_defaults(self):
        """Test SyncResult default values."""
        result = SyncResult(
            success=True,
            integration_id="test-id",
        )
        
        assert result.appointments_synced == 0
        assert result.appointments_updated == 0
        assert result.appointments_deleted == 0
        assert result.errors == []
        assert result.started_at is None
        assert result.completed_at is None


class TestTokenRefreshResult:
    """Test suite for TokenRefreshResult model."""
    
    def test_token_refresh_result_creation(self):
        """Test creating a TokenRefreshResult."""
        expires_at = datetime.now(timezone.utc)
        result = TokenRefreshResult(
            success=True,
            integration_id="test-id",
            error=None,
            expires_at=expires_at,
        )
        
        assert result.success is True
        assert result.integration_id == "test-id"
        assert result.error is None
        assert result.expires_at == expires_at
    
    def test_token_refresh_result_with_error(self):
        """Test TokenRefreshResult with error."""
        result = TokenRefreshResult(
            success=False,
            integration_id="test-id",
            error="Token refresh failed",
        )
        
        assert result.success is False
        assert result.error == "Token refresh failed"
        assert result.expires_at is None

