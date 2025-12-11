# Database Library

Shared SQLAlchemy models and Alembic migrations for LexiqAI.

## Structure

- **`models.py`** - SQLAlchemy model definitions
- **`env.py`** - Alembic configuration
- **`versions/`** - Alembic migration scripts

## Status

🚧 **In Development** - Database models will be created in Phase 1-2.

## Usage

```python
from libs.database.models import User, Call, Firm
```

