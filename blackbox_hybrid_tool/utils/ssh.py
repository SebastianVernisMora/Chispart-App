from __future__ import annotations

import os
import shlex
import subprocess
from pathlib import Path
from typing import Dict, Iterable, List, Optional


def _ssh_base_args(host: str, user: Optional[str] = None, key_path: Optional[str] = None, port: int = 22) -> List[str]:
    target = f"{user}@{host}" if user else host
    args = ["ssh", "-p", str(port)]
    if key_path:
        args += ["-i", str(key_path)]
    # Non-interactive, strict options suitable for automation
    args += ["-o", "StrictHostKeyChecking=no", "-o", "BatchMode=yes", target]
    return args


def run_ssh_command(
    host: str,
    command: str,
    user: Optional[str] = None,
    key_path: Optional[str] = None,
    port: int = 22,
    env: Optional[Dict[str, str]] = None,
    timeout: Optional[int] = None,
) -> int:
    """Run a remote command via SSH. Returns exit code.

    Example:
      run_ssh_command('server', 'docker ps', user='ubuntu', key_path='~/.ssh/id_rsa')
    """
    args = _ssh_base_args(host, user, key_path, port)
    full_cmd = args + [command]
    proc = subprocess.run(full_cmd, env={**os.environ, **(env or {})}, timeout=timeout, capture_output=True, text=True)
    if proc.stdout:
        print(proc.stdout)
    if proc.stderr:
        print(proc.stderr)
    return proc.returncode


def sync_files(
    local: str | Path,
    remote: str,
    host: str,
    user: Optional[str] = None,
    key_path: Optional[str] = None,
    port: int = 22,
    recursive: bool = True,
) -> int:
    """Copy files to remote using scp. remote is a path on the remote machine.

    Example:
      sync_files('dist/app.tar.gz', '/opt/app', host='server', user='ubuntu')
    """
    src = str(local)
    target = f"{user}@{host}:{remote}" if user else f"{host}:{remote}"
    args = ["scp", "-P", str(port)]
    if key_path:
        args += ["-i", str(key_path)]
    if recursive:
        args.append("-r")
    args += [src, target]
    proc = subprocess.run(args, capture_output=True, text=True)
    if proc.stdout:
        print(proc.stdout)
    if proc.stderr:
        print(proc.stderr)
    return proc.returncode


def deploy_remote(
    host: str,
    project_dir: str,
    user: Optional[str] = None,
    key_path: Optional[str] = None,
    port: int = 22,
    use_docker: bool = True,
    compose: bool = False,
    service: Optional[str] = None,
) -> int:
    """Basic remote deployment helper.

    - use_docker + compose: docker compose pull/build + up -d
    - use_docker only: docker build . && docker run ... (simplified)
    - no docker: python -m venv .venv && pip install -r requirements.txt && systemd-restart (placeholder)
    """
    if use_docker:
        if compose:
            cmd = (
                f"cd {shlex.quote(project_dir)} && "
                f"docker compose pull || true && docker compose build && docker compose up -d"
            )
        else:
            image = "app:latest"
            cmd = (
                f"cd {shlex.quote(project_dir)} && "
                f"docker build -t {image} . && "
                f"docker rm -f app || true && docker run -d --name app -p 8000:8000 {image}"
            )
    else:
        cmd = (
            f"cd {shlex.quote(project_dir)} && "
            f"python3 -m venv .venv && . .venv/bin/activate && pip install -U pip && pip install -r requirements.txt && "
            f"nohup python main.py >/tmp/app.out 2>&1 &"
        )
    return run_ssh_command(host, cmd, user=user, key_path=key_path, port=port)

