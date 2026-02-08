#!/usr/bin/env python
"""
Verification script for integration worker setup.

Run this script to verify that the basic setup is working correctly.

Usage:
    python verify_setup.py
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))


def verify_imports():
    """Verify that all core modules can be imported."""
    print("✓ Verifying imports...")
    
    try:
        from integration_worker.config import get_settings, Settings
        print("  ✓ Config module imported successfully")
    except ImportError as e:
        print(f"  ✗ Failed to import config: {e}")
        return False
    
    try:
        from integration_worker.celery_app import app
        print("  ✓ Celery app imported successfully")
    except ImportError as e:
        print(f"  ✗ Failed to import celery_app: {e}")
        return False
    
    try:
        from integration_worker.database.session import get_session
        print("  ✓ Database session imported successfully")
    except ImportError as e:
        print(f"  ✗ Failed to import database session: {e}")
        return False
    
    try:
        from integration_worker.utils.logging import setup_logging, get_logger
        print("  ✓ Logging utils imported successfully")
    except ImportError as e:
        print(f"  ✗ Failed to import logging utils: {e}")
        return False
    
    try:
        from integration_worker.utils.errors import (
            IntegrationWorkerError,
            SyncError,
            TokenRefreshError,
        )
        print("  ✓ Custom errors imported successfully")
    except ImportError as e:
        print(f"  ✗ Failed to import errors: {e}")
        return False
    
    return True


def verify_tasks():
    """Verify that all task modules can be imported."""
    print("\n✓ Verifying task modules...")
    
    try:
        from integration_worker.tasks import calendar_sync
        print("  ✓ calendar_sync tasks imported")
    except ImportError as e:
        print(f"  ✗ Failed to import calendar_sync: {e}")
        return False
    
    try:
        from integration_worker.tasks import token_refresh
        print("  ✓ token_refresh tasks imported")
    except ImportError as e:
        print(f"  ✗ Failed to import token_refresh: {e}")
        return False
    
    try:
        from integration_worker.tasks import webhook_processing
        print("  ✓ webhook_processing tasks imported")
    except ImportError as e:
        print(f"  ✗ Failed to import webhook_processing: {e}")
        return False
    
    try:
        from integration_worker.tasks import cleanup
        print("  ✓ cleanup tasks imported")
    except ImportError as e:
        print(f"  ✗ Failed to import cleanup: {e}")
        return False
    
    return True


def verify_celery_config():
    """Verify Celery configuration."""
    print("\n✓ Verifying Celery configuration...")
    
    from integration_worker.celery_app import app
    
    # Check basic config
    assert app.main == "integration_worker", "App name mismatch"
    print("  ✓ Celery app name is correct")
    
    # Check Beat schedule
    beat_schedule = app.conf.beat_schedule
    expected_tasks = ["sync-all-calendars", "refresh-expiring-tokens", "cleanup-sync-logs", "cleanup-orphaned-resources"]
    
    for task_name in expected_tasks:
        if task_name not in beat_schedule:
            print(f"  ✗ Missing scheduled task: {task_name}")
            return False
    
    print(f"  ✓ All {len(expected_tasks)} scheduled tasks are configured")
    
    # Check configuration
    assert app.conf.task_serializer == "json", "Task serializer should be json"
    assert app.conf.timezone == "UTC", "Timezone should be UTC"
    print("  ✓ Celery configuration is correct")
    
    return True


def main():
    """Run all verification checks."""
    print("=" * 60)
    print("Integration Worker Setup Verification")
    print("=" * 60)
    
    checks = [
        ("Module Imports", verify_imports),
        ("Task Modules", verify_tasks),
        ("Celery Configuration", verify_celery_config),
    ]
    
    results = []
    
    for check_name, check_func in checks:
        try:
            result = check_func()
            results.append((check_name, result))
        except Exception as e:
            print(f"\n✗ {check_name} failed with error: {e}")
            results.append((check_name, False))
    
    # Print summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    
    all_passed = True
    for check_name, result in results:
        status = "✓ PASSED" if result else "✗ FAILED"
        print(f"{status:12} - {check_name}")
        if not result:
            all_passed = False
    
    print("=" * 60)
    
    if all_passed:
        print("\n✓ All checks passed! Setup is complete.")
        print("\nNext steps:")
        print("  1. Copy .env.example to .env and fill in your values")
        print("  2. Install dependencies: pip install -r requirements.txt")
        print("  3. Run tests: pytest")
        print("  4. Start worker: celery -A integration_worker.celery_app worker --loglevel=info")
        return 0
    else:
        print("\n✗ Some checks failed. Please review the errors above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())

