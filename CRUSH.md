# CRUSH.md: Development Guide for Blackbox Hybrid Tool

## Development Commands

- **Install Dependencies**: `pip install -r requirements-dev.txt`
- **Run API Server**: `python main.py` or `uvicorn main:app --reload`
- **Run with Docker**: `docker-compose up --build` (dev mode: `docker-compose --profile dev up`)
- **Run Tests**: 
  - All tests: `pytest`
  - Single test: `pytest tests/test_file.py::TestClass::test_function`
  - By keyword: `pytest -k "keyword"` (quieter: `pytest -k "keyword" -q`)
- **Coverage Report**: `pytest` (HTML report in `htmlcov/index.html`, threshold ≥ 80%)
- **Format & Lint**: 
  - Setup: `pre-commit install`
  - Run: `pre-commit run -a`
  - Manual tools: `black .` | `isort .` | `flake8` | `mypy`

## Code Style Guidelines

- **Formatting**: Black (88 chars), isort (profile `black`)
- **Linting**: Flake8 (ignores `E203,W503`) per `.flake8`
- **Type Checking**: mypy (strict mode, Python 3.10), full type hints required
- **Naming Conventions**:
  - Modules/functions: `snake_case`
  - Classes: `CapWords`
  - Constants: `UPPER_CASE`
- **Imports**: Group standard library, third-party, and local imports (isort handles this)
- **Error Handling**: Use typed exceptions with context, prefer specific over generic exceptions
- **Structure**: 
  - Shared utilities in `utils/`
  - Configurable values in `config/`
  - Tests in `tests/` with prefix `test_`

## Testing Guidelines

- Name test files `test_*.py`, classes `Test*`, functions `test_*`
- Cover logic in `core/` and `utils/` thoroughly
- Mock external I/O (HTTP, filesystem) in tests
- Assert both happy path and error cases

## Commit Conventions

- Follow Conventional Commits: `feat:`, `fix:`, `docs:`, `test:`, `refactor:`
- Keep commits atomic, focused, and with clear messages
- PRs should include tests and clear descriptions

## Security Best Practices

- Store secrets in `.env` (see `.env.example`), never commit keys
- Required: `BLACKBOX_API_KEY`
- Respect `WRITE_ROOT` limitation (default `/app`) for file operations