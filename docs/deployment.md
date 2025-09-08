# Remote Deployment Guide

This repo includes simple SSH helpers to deploy the app to a remote server with or without Docker.

## Prerequisites
- Remote host reachable over SSH (user with sudo or Docker permissions).
- Docker and Docker Compose installed on the server for container-based deployment.
- A valid `.env` on the server (see `.env.example`). At minimum, set `BLACKBOX_API_KEY`.

## Quick Start (Docker Compose)
1) Sync the project to the server (example path `/opt/bbtool`):
```
python -m blackbox_hybrid_tool.cli.main ssh-sync --host your.host --user ubuntu --key ~/.ssh/id_rsa --recursive . /opt/bbtool
```
2) Start (or update) using compose:
```
python -m blackbox_hybrid_tool.cli.main ssh-exec --host your.host --user ubuntu --key ~/.ssh/id_rsa "cd /opt/bbtool && docker compose up -d --build"
```
3) Health check:
```
python -m blackbox_hybrid_tool.cli.main ssh-exec --host your.host --user ubuntu --key ~/.ssh/id_rsa "curl -f http://localhost:8000/health"
```

## One-Step Deploy Helper
Use the built-in `deploy-remote` command. It runs appropriate commands on the server based on flags.
- Docker Compose:
```
python -m blackbox_hybrid_tool.cli.main deploy-remote --host your.host --user ubuntu --key ~/.ssh/id_rsa --dir /opt/bbtool --compose
```
- Plain Docker:
```
python -m blackbox_hybrid_tool.cli.main deploy-remote --host your.host --user ubuntu --key ~/.ssh/id_rsa --dir /opt/bbtool
```
- No Docker (venv + nohup):
```
python -m blackbox_hybrid_tool.cli.main deploy-remote --host your.host --user ubuntu --key ~/.ssh/id_rsa --dir /opt/bbtool --no-docker
```

## CLI SSH Tools
- `ssh-exec`: run a remote command via SSH.
- `ssh-sync`: scp files or folders to the remote host (`--recursive` to copy directories).
- `deploy-remote`: opinionated deployment (compose/docker/venv) in the target directory.

Example:
```
# Logs via docker
python -m blackbox_hybrid_tool.cli.main ssh-exec --host your.host --user ubuntu --key ~/.ssh/id_rsa "docker logs -n 200 blackbox-hybrid-tool"
```

## Compose Reference
The included `docker-compose.yml` defines two services:
- `blackbox-hybrid-tool`: production-like, runs `python main.py` on port `8000`.
- `dev` (profile `dev`): hot-reload via `uvicorn` on port `8001` (mapped to `8000` inside the container).

Start with hot reload locally:
```
docker-compose --profile dev up --build
```

## Notes & Tips
- Secrets: never commit API keys; use `.env`. Required: `BLACKBOX_API_KEY`.
- Update the server’s `.env` at `/opt/bbtool/.env` (or your chosen path) before starting.
- For reliability, consider a reverse proxy (nginx/caddy) in front of port 8000.
- For systemd-based no-docker deployments, adapt `deploy-remote --no-docker` to your own unit file.
