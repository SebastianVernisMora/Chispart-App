"""
Ligera integración con GitHub API usando token personal (PAT).

Funciones básicas:
- get_user(): verifica el token y devuelve el usuario
- create_gist(files, description, public): crea un Gist con uno o más archivos

Nota: Para operaciones de PR completas (crear rama, blobs/trees/commits), se recomienda
usar el Git Data API. Aquí dejamos métodos iniciales y estructura para extender.
"""

from __future__ import annotations

import os
from typing import Dict, Any
import requests


class GitHubClient:
    def __init__(self, token: str | None = None, base_url: str = "https://api.github.com"):
        self.token = token or os.getenv("GH_TOKEN") or os.getenv("GITHUB_TOKEN")
        if not self.token:
            raise ValueError("Falta GH_TOKEN/GITHUB_TOKEN en el entorno o parámetro")
        self.base_url = base_url.rstrip("/")

    @property
    def headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }

    def get_user(self) -> Dict[str, Any]:
        r = requests.get(f"{self.base_url}/user", headers=self.headers)
        r.raise_for_status()
        return r.json()

    def create_gist(self, files: Dict[str, str], description: str = "", public: bool = False) -> Dict[str, Any]:
        payload = {
            "description": description,
            "public": public,
            "files": {name: {"content": content} for name, content in files.items()},
        }
        r = requests.post(f"{self.base_url}/gists", headers=self.headers, json=payload)
        r.raise_for_status()
        return r.json()

