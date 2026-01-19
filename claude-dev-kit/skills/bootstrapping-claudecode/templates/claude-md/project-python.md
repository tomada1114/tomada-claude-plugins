# Project CLAUDE.md (Python)

Python プロジェクト用のテンプレート。

---

## Project Overview

[プロジェクトの説明]

**Tech Stack:**
- Python 3.11+
- [FastAPI / Django / Flask]
- [SQLAlchemy / Prisma]
- pytest
- [その他のライブラリ]

---

## Critical Rules

### 1. Code Organization

```
src/
├── api/              # API endpoints
├── core/             # Core business logic
├── models/           # Data models
├── services/         # Business services
├── utils/            # Utilities
└── tests/            # Test files
```

### 2. Python Best Practices

- Type hints を使用
- Docstrings で関数を文書化
- f-strings を使用
- リスト内包表記を適切に使用
- Context managers を使用

### 3. Code Style

- PEP 8 に従う
- Black でフォーマット
- isort でインポート整理
- mypy で型チェック
- 絵文字禁止

### 4. Error Handling

```python
from typing import TypeVar, Generic
from dataclasses import dataclass

T = TypeVar('T')

@dataclass
class Result(Generic[T]):
    success: bool
    data: T | None = None
    error: str | None = None
```

### 5. Testing

- pytest を使用
- pytest-cov でカバレッジ
- pytest-asyncio で非同期テスト
- fixtures を活用
- 80%+ カバレッジ

---

## Test Structure

```python
class TestUserService:
    """UserService のテストクラス"""

    def test_create_user_success(self):
        """正常なユーザー作成"""
        # Given
        user_data = {"name": "Test", "email": "test@example.com"}

        # When
        result = user_service.create(user_data)

        # Then
        assert result.success
        assert result.data.name == "Test"

    def test_create_user_invalid_email(self):
        """無効なメールアドレスでエラー"""
        # Given
        user_data = {"name": "Test", "email": "invalid"}

        # When
        result = user_service.create(user_data)

        # Then
        assert not result.success
        assert "email" in result.error.lower()
```

---

## Environment Variables

```bash
# Required
DATABASE_URL=
SECRET_KEY=

# Optional
DEBUG=false
LOG_LEVEL=INFO
```

---

## Development Commands

```bash
# Install dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Format code
black src tests
isort src tests

# Type check
mypy src
```

---

## Git Workflow

- Conventional commits
- main に直接コミットしない
- PR にはレビュー必須
- CI がパスしてからマージ
