"""Pytest configuration and fixtures for cognitive-orch tests."""

import os
import sys
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path

# Add py_common to Python path
project_root = Path(__file__).parent.parent.parent
py_common_path = project_root / "libs" / "py-common" / "src"
if py_common_path.exists() and str(py_common_path) not in sys.path:
    sys.path.insert(0, str(py_common_path))

# Set environment variables before any imports that might use them
# This prevents Pydantic validation errors from environment variables with trailing spaces
os.environ.pop("INTERNAL_API_KEY_ENABLED", None)  # Remove if exists with bad value
os.environ["INTERNAL_API_KEY_ENABLED"] = "false"  # Set clean value

# Now we can safely import
from cognitive_orch.config import Settings, get_settings


@pytest.fixture(autouse=True)
def mock_settings():
    """Mock settings for all tests to avoid environment variable issues."""
    # Create a clean settings object with defaults
    settings = Settings()
    
    # Ensure internal_api_key_enabled is a proper boolean
    settings.internal_api_key_enabled = False
    settings.internal_api_key = None
    
    # Patch get_settings to return our mock
    with patch("cognitive_orch.config.get_settings", return_value=settings):
        yield settings
