# Integration Worker Tests

Comprehensive test suite for the integration-worker service.

## Test Structure

```
tests/
├── conftest.py                      # Shared fixtures and configuration
├── test_config.py                   # Configuration tests
├── test_celery_app.py               # Celery app configuration tests
│
├── test_models/
│   └── test_sync_result.py          # SyncResult and TokenRefreshResult tests
│
├── test_services/
│   └── test_outlook_service.py      # OutlookService comprehensive tests
│
├── test_tasks/
│   ├── test_calendar_sync.py        # Calendar sync task tests
│   ├── test_token_refresh.py        # Token refresh task tests
│   └── test_webhook_processing.py   # Webhook processing task tests
│
├── test_database/
│   └── test_repositories.py         # Repository tests
│
└── test_utils/
    ├── test_logging.py               # Logging utility tests
    └── test_errors.py                # Custom exception tests
```

## Running Tests

### Run All Tests

```bash
# With coverage
pytest --cov=integration_worker --cov-report=html --cov-report=term-missing

# Verbose output
pytest -v

# With output
pytest -v -s
```

### Run Specific Test Files

```bash
# Test OutlookService
pytest tests/test_services/test_outlook_service.py -v

# Test calendar sync tasks
pytest tests/test_tasks/test_calendar_sync.py -v

# Test models
pytest tests/test_models/test_sync_result.py -v
```

### Run Specific Test Classes

```bash
# Test OutlookService class
pytest tests/test_services/test_outlook_service.py::TestOutlookService -v

# Test specific test method
pytest tests/test_services/test_outlook_service.py::TestOutlookService::test_sync_calendar_success -v
```

## Test Coverage

### Current Coverage

| Module | Tests | Coverage |
|--------|-------|----------|
| `config.py` | 3 tests | ✅ High |
| `celery_app.py` | 4 tests | ✅ High |
| `services/outlook_service.py` | 11 tests | ✅ High |
| `tasks/calendar_sync.py` | 4 tests | ✅ Medium |
| `tasks/token_refresh.py` | 3 tests | ✅ Medium |
| `tasks/webhook_processing.py` | 2 tests | ✅ Medium |
| `models/sync_result.py` | 6 tests | ✅ High |
| `database/repositories.py` | 6 tests | ✅ High |
| `utils/logging.py` | 2 tests | ✅ Medium |
| `utils/errors.py` | 7 tests | ✅ High |

**Total Tests:** 48+ test cases

## Test Fixtures

### Available Fixtures (conftest.py)

- `mock_settings` - Mock Settings configuration
- `mock_calendar_integration` - Mock CalendarIntegration model
- `mock_user` - Mock User model
- `mock_appointment` - Mock Appointment model
- `mock_outlook_event` - Mock Outlook calendar event (Microsoft Graph format)
- `mock_db_session` - Mock async database session
- `celery_config` - Celery test configuration
- `celery_app` - Celery app for task testing

## Test Categories

### Unit Tests

Test individual components in isolation with mocked dependencies:

- ✅ Configuration loading
- ✅ Model validation
- ✅ Service methods
- ✅ Repository methods
- ✅ Utility functions
- ✅ Custom exceptions

### Integration Tests

Test components working together:

- ✅ Celery task execution
- ✅ Task scheduling
- ✅ Database operations (with mocks)

### End-to-End Tests (Future)

Test full workflows with real dependencies:

- ⏭️ Live calendar sync with test account
- ⏭️ Token refresh with real MSAL
- ⏭️ Webhook processing with real events

## Mocking Strategy

### External Dependencies

We mock:
- Microsoft Graph API calls (`httpx.AsyncClient`)
- MSAL authentication (`ConfidentialClientApplication`)
- Database session operations
- Celery task delays

### Internal Dependencies

We test:
- Business logic
- Data transformations
- Error handling
- Edge cases

## Test Data

### Mock Calendar Event

```python
{
    "id": "test-event-123",
    "subject": "Test Meeting",
    "start": {
        "dateTime": "2026-01-04T10:00:00Z",
        "timeZone": "UTC"
    },
    "end": {
        "dateTime": "2026-01-04T11:00:00Z",
        "timeZone": "UTC"
    },
    "organizer": {
        "emailAddress": {
            "name": "John Doe",
            "address": "john@example.com"
        }
    },
    "isCancelled": False
}
```

## Continuous Integration

### GitHub Actions (Future)

```yaml
name: Integration Worker Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: |
          cd apps/integration-worker
          pip install -r requirements.txt -r requirements-dev.txt
      - name: Run tests
        run: |
          cd apps/integration-worker
          pytest --cov=integration_worker --cov-report=xml
      - name: Upload coverage
        uses: codecov/codecov-action@v3
```

## Best Practices

### Writing New Tests

1. **Use descriptive test names** - `test_sync_calendar_success`, not `test1`
2. **One assertion per test** - Keep tests focused
3. **Mock external dependencies** - Don't call real APIs
4. **Test edge cases** - Empty lists, None values, errors
5. **Use fixtures** - Reuse common test data
6. **Document complex tests** - Add docstrings

### Example Test Template

```python
@pytest.mark.asyncio
async def test_method_name_scenario(self, mock_db_session, mock_calendar_integration):
    """Test [method name] [scenario description]."""
    # Setup
    service = OutlookService(mock_db_session)
    
    with patch.object(service.calendar_repo, 'get_by_id', return_value=mock_calendar_integration):
        # Execute
        result = await service.method_name(params)
    
    # Assert
    assert result.success is True
```

## Next Steps

- ⏭️ Add integration tests with real database
- ⏭️ Add E2E tests with test Outlook account
- ⏭️ Set up CI/CD pipeline
- ⏭️ Add performance tests
- ⏭️ Add load tests for concurrent syncs

---

**Test Status:** ✅ Comprehensive unit test suite complete  
**Total Tests:** 48+ test cases  
**Coverage:** High across all modules

