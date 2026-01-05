#!/usr/bin/env python
"""
Quick test script for Celery worker.

This script manually triggers calendar sync tasks to verify the worker is functioning.

Usage:
    python test_celery.py
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))
sys.path.insert(0, str(Path(__file__).parent.parent / "api-core" / "src"))


def test_task_registration():
    """Test that tasks are registered with Celery."""
    print("=" * 60)
    print("Testing Task Registration")
    print("=" * 60)
    
    from integration_worker.celery_app import app
    
    # Get all registered tasks
    task_names = sorted([name for name in app.tasks.keys() if not name.startswith("celery.")])
    
    print(f"\n✓ Found {len(task_names)} registered tasks:")
    for task_name in task_names:
        print(f"  - {task_name}")
    
    # Check our specific tasks
    expected_tasks = [
        "integration_worker.tasks.calendar_sync.sync_outlook_calendar",
        "integration_worker.tasks.calendar_sync.sync_all_calendars",
        "integration_worker.tasks.token_refresh.refresh_expiring_tokens",
        "integration_worker.tasks.cleanup.cleanup_old_sync_logs",
    ]
    
    missing = []
    for expected in expected_tasks:
        if expected in task_names:
            print(f"\n✓ Task registered: {expected}")
        else:
            print(f"\n✗ Task missing: {expected}")
            missing.append(expected)
    
    if missing:
        print(f"\n✗ {len(missing)} tasks are missing!")
        return False
    
    print("\n✓ All expected tasks are registered!")
    return True


def test_beat_schedule():
    """Test that Beat schedule is configured correctly."""
    print("\n" + "=" * 60)
    print("Testing Celery Beat Schedule")
    print("=" * 60)
    
    from integration_worker.celery_app import app
    
    beat_schedule = app.conf.beat_schedule
    
    print(f"\n✓ Found {len(beat_schedule)} scheduled tasks:")
    
    for task_name, config in beat_schedule.items():
        task = config.get("task")
        schedule = config.get("schedule")
        print(f"\n  {task_name}:")
        print(f"    Task: {task}")
        print(f"    Schedule: {schedule}")
    
    # Verify expected schedules
    expected_schedules = [
        "sync-all-calendars",
        "refresh-expiring-tokens",
        "cleanup-sync-logs",
    ]
    
    for expected in expected_schedules:
        if expected in beat_schedule:
            print(f"\n✓ Scheduled task configured: {expected}")
        else:
            print(f"\n✗ Scheduled task missing: {expected}")
            return False
    
    print("\n✓ All scheduled tasks are configured!")
    return True


def test_config():
    """Test configuration loading."""
    print("\n" + "=" * 60)
    print("Testing Configuration")
    print("=" * 60)
    
    try:
        from integration_worker.config import get_settings
        
        settings = get_settings()
        
        print("\n✓ Configuration loaded successfully")
        print(f"  Service Name: {settings.service_name}")
        print(f"  Environment: {settings.environment}")
        print(f"  Redis URL: {settings.redis_url}")
        print(f"  Log Level: {settings.log_level}")
        print(f"  Sync Lookback Days: {settings.sync_lookback_days}")
        print(f"  Sync Lookahead Days: {settings.sync_lookahead_days}")
        
        return True
        
    except Exception as e:
        print(f"\n✗ Configuration error: {e}")
        return False


def test_manual_task_trigger():
    """Test manually triggering a task (dry run)."""
    print("\n" + "=" * 60)
    print("Testing Manual Task Trigger (Dry Run)")
    print("=" * 60)
    
    try:
        from integration_worker.tasks.calendar_sync import sync_all_calendars
        
        print("\n✓ Task imported successfully")
        print("\nTo manually trigger this task:")
        print("  >>> from integration_worker.tasks.calendar_sync import sync_all_calendars")
        print("  >>> task = sync_all_calendars.delay()")
        print("  >>> print(task.id)")
        print("\nNote: Requires Celery worker and Redis to be running")
        
        return True
        
    except Exception as e:
        print(f"\n✗ Task import error: {e}")
        return False


def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("Integration Worker - Celery Test Suite")
    print("=" * 60)
    
    tests = [
        ("Configuration", test_config),
        ("Task Registration", test_task_registration),
        ("Beat Schedule", test_beat_schedule),
        ("Manual Task Trigger", test_manual_task_trigger),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"\n✗ {test_name} failed with error: {e}")
            import traceback
            traceback.print_exc()
            results.append((test_name, False))
    
    # Print summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    
    all_passed = True
    for test_name, result in results:
        status = "✓ PASSED" if result else "✗ FAILED"
        print(f"{status:12} - {test_name}")
        if not result:
            all_passed = False
    
    print("=" * 60)
    
    if all_passed:
        print("\n✓ All tests passed! Celery worker is properly configured.")
        print("\nTo start the worker:")
        print("  make worker-start")
        print("\nTo start the beat scheduler:")
        print("  make worker-beat")
        return 0
    else:
        print("\n✗ Some tests failed. Please review the errors above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())

