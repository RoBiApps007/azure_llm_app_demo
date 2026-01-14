# GitHub Copilot Instructions: [Project Name]

## 1. Core Architecture & Python Standards
- **Version**: Target Python 3.11+. Use modern syntax: `ExceptionGroup`, `TaskGroup`, `X | Y` type unions.
- **Typing**: **Strict typing is mandatory.** All functions must have complete type hints. Use `typing.Annotated` for metadata-heavy types.
- **Code Style**: Follow PEP 8. Use **Google-Style Docstrings**. Refactor functions longer than 40 lines.
- **Project Structure**: Follow the `src/` layout. All imports must be absolute (e.g., `from app.core.config import settings`).

## 2. Secrets, Config & Security
- **Secrets**: **Zero Hardcoding Policy.** Use `pydantic-settings` (BaseSettings).
- **Sensitive Data**: Use Pydantic's `SecretStr` for tokens and passwords to prevent accidental logging/leakage.
- **Auth**: Standardize on OAuth2 with Bearer Tokens. Auth logic resides in `app.core.security`.

## 3. Advanced Session & Resource Management
- **Lifecycle**: Use FastAPI `lifespan` events for `httpx.AsyncClient` and DB engine setup/teardown.
- **Persistence**: Always use `async with` context managers for sessions (DB, Redis, API-Clients).
- **Efficiency**: Use connection pooling for SQLAlchemy (`async_sessionmaker`).

## 4. 'concerto' Package - Measurement Data Domain
- **Initialization**: Use `import concerto as conc` when using the concerto package in your python scripts.
- **Object Model**: `concerto.data.FileObject` contains multiple `concerto.data.DataSet` objects organized by proper CONCERTo measurement types.
- **Memory**: For large datasets, use always either the `concerto.data.dataset_object` or `concerto.data.FileObject.dataset_object` methods to get all meta information without loading data into memory, and load data only via the CONCERTO DataSet object `concerto.data.DataSet.values` method when needed.
- **Metadata**: Every CONCERTO dataset (signal or  channel) must have proper `units` and `base_type` defined.

## 5. Robust AsyncIO & Concurrency
- **Non-Blocking**: Never use `time.sleep` or sync `requests`. Use `asyncio.sleep` and `httpx`.
- **Concurrency**: Use `asyncio.Semaphore` to limit memory-intensive `concerto` tasks.
- **Safety**: Every I/O call must have an `asyncio.wait_for` timeout.

## 6. Global Exception Handling & Logging
- **Exception Chain**: Always use `raise NewException(...) from err`.
- **Logging**: Use a central structured logger. **Log Context**: Include `request_id` or `measurement_id`.
- **No PII/Secrets**: Ensure no personal data or `SecretStr` values are printed/logged.

## 7. Testing & Quality
- **Framework**: `pytest` + `pytest-asyncio`. Coverage target > 80%.
- **Mocks**: Mock all `concerto` file system calls and external APIs using `pytest-mock`.