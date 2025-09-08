Branding Guide
===============

This guide explains how to rebrand the app without code changes, and how to proceed if you want a full package rename later.

Quick Branding (no code rename)
- Set environment variables in your `.env` or deployment config:
  - `APP_NAME` (default: "Blackbox Hybrid Tool")
  - `APP_TAGLINE` (default: "API para herramienta híbrida de modelos AI")
  - `APP_VERSION` (default: "1.0.0")
  - `APP_SLUG` (used for Docker container name)
- Run `docker-compose up --build`. The FastAPI title and root endpoint will reflect your branding.

Where the name appears
- API: FastAPI title/description (`main.py`) reads `APP_NAME`, `APP_TAGLINE`, `APP_VERSION`.
- Docker: `container_name` in `docker-compose.yml` uses `APP_SLUG`.
- CLI: entry-points are `blackbox-tool`, `blackbox-hybrid-tool`, `blackbox_hybrid_tool`. You can keep these as aliases even if the product name differs.
- Playground: `static/playground.html` includes a static title string. You can modify this file to reflect your brand.

Optional: Full package rename
Renaming the Python package (module path) is optional and more invasive. Steps:
1) Rename directory `blackbox_hybrid_tool/` to your new package name (e.g., `my_tool/`).
2) Update imports across the codebase from `blackbox_hybrid_tool` to `my_tool`.
3) Update `setup.py` `name=...`, URLs, and entry points if you want different command names.
4) Update `docker-compose.yml` volume paths and environment variables referencing the old path.
5) Update documentation references to paths and commands.

Recommendation: keep the internal package name stable and rebrand via env vars and README/UI texts to minimize risk.

