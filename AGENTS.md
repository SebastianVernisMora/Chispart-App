# Repository Guidelines

## Project Structure & Module Organization
- `blackbox_hybrid_tool/`: main package
  - `core/`: orchestration and AI clients (e.g., `ai_client.py`)
  - `cli/`: CLI commands
  - `utils/`: patches, web helpers, repo snapshots
  - `config/`: runtime config (e.g., `models.json`)
- `main.py`: FastAPI entry (API, playground, health).
- `tests/`: pytest suite (`test_*.py`).
- `static/`: web playground assets.
- `docs/`: documentation.

## Build, Test, and Development Commands
- Install (dev): `pip install -r requirements-dev.txt`
- Run API: `python main.py` or `uvicorn main:app --reload`
- Docker: `docker-compose up --build` (hot‑reload: `docker-compose --profile dev up`)
- Tests: `pytest` (HTML coverage in `htmlcov/index.html`)
- Format & lint: `pre-commit install` then `pre-commit run -a`

## Coding Style & Naming Conventions
- Formatting: Black (line length 88) and isort (profile `black`).
- Linting: Flake8 (ignores `E203,W503`) per `.flake8`.
- Typing: mypy (strict, Python 3.10). Prefer full type hints.
- Naming: modules/functions `snake_case`, classes `CapWords`, constants `UPPER_CASE`.
- Shared utilities in `utils/`; configurable values in `config/`.

## Testing Guidelines
- Framework: pytest with coverage (`--cov=blackbox_hybrid_tool`, threshold ≥ 80%).
- Location: `tests/` with files `test_*.py`, classes `Test*`, functions `test_*`.
- Scope: cover logic in `core/` and `utils/`; mock external I/O (HTTP, FS).
- Selective runs: `pytest -k "<expr>"` or quieter `pytest -q`.

## Commit & Pull Request Guidelines
- Commits: Conventional Commits (`feat:`, `fix:`, `docs:`, `test:`, `refactor:`); imperative, concise.
- PRs: clear description and motivation, linked issues (`Closes #123`), tests included, CI green, and docs updated if API/CLI changes. Add screenshots/GIFs for playground changes.

## Security & Configuration Tips
- Secrets live in `.env` (see `.env.example`); never commit keys.
- Required: `BLACKBOX_API_KEY`. Optional: `CONFIG_FILE`, `BLACKBOX_MODELS_CSV`.
- Write/patch operations are restricted by `WRITE_ROOT` (default `/app`). Avoid paths outside it.

## Architecture Overview
- `main.py` exposes FastAPI endpoints and delegates to `AIOrchestrator` for Blackbox model selection and to clients in `core/`.
- `utils/` provides unified‑diff patch application and repository snapshots for reproducibility.

