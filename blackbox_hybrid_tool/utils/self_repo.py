"""
Self-repo utilities: snapshot, embed, extract, analyze, and safe-apply changes.
"""
from __future__ import annotations

import base64
import hashlib
import io
import json
import os
import re
import tarfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple


EMBED_MODULE = Path(__file__).resolve().parent.parent / "_embedded_payload.py"
PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _iter_project_files(root: Path) -> List[Path]:
    exts = {".py", ".md", ".toml", ".txt", ".json", ".yml", ".yaml", ".html", ".ini", ".cfg"}
    ignore_dirs = {"__pycache__", ".git", ".venv", "venv", "env", ".self_backup", "htmlcov", "logs", ".pytest_cache"}
    files: List[Path] = []
    for p in root.rglob("*"):
        if p.is_dir():
            if p.name in ignore_dirs:
                # skip entire tree
                for _ in p.rglob("*"):
                    pass
                continue
            continue
        if p.suffix.lower() in exts or p.name in {"Dockerfile", ".gitignore", "Makefile"}:
            files.append(p)
    return files


def _make_tar_bytes(root: Path, paths: List[Path]) -> bytes:
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        for path in paths:
            arcname = path.relative_to(root)
            tar.add(path, arcname=str(arcname))
    return buf.getvalue()


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def make_snapshot(root: Optional[Path] = None) -> Dict[str, object]:
    root = root or PROJECT_ROOT
    files = _iter_project_files(root)
    data = _make_tar_bytes(root, files)
    meta = {
        "timestamp": int(time.time()),
        "file_count": len(files),
        "sha256": _sha256(data),
        "size": len(data),
        "root": str(root),
    }
    return {"data": data, "meta": meta}


def embed_snapshot(root: Optional[Path] = None) -> Path:
    snap = make_snapshot(root)
    b64 = base64.b64encode(snap["data"]).decode("ascii")
    # Split to manageable lines
    chunks = [b64[i : i + 120] for i in range(0, len(b64), 120)]
    meta_json = json.dumps(snap["meta"], ensure_ascii=False)
    content = (
        "# Auto-generated embedded snapshot. Do not edit manually.\n"
        "EMBEDDED_META = " + repr(meta_json) + "\n"
        "EMBEDDED_ARCHIVE_BASE64 = (\n" + "\n".join(["    '" + c + "'" for c in chunks]) + "\n)\n"
    )
    EMBED_MODULE.write_text(content, encoding="utf-8")
    return EMBED_MODULE


def ensure_embedded_snapshot(root: Optional[Path] = None) -> Tuple[bool, Dict[str, object]]:
    """Ensure there's an up-to-date embedded snapshot.
    Returns (changed, meta)
    """
    root = root or PROJECT_ROOT
    snap = make_snapshot(root)
    current_meta: Dict[str, object] = {}
    if EMBED_MODULE.exists():
        try:
            # dynamic import without caching
            import importlib.util

            spec = importlib.util.spec_from_file_location("_embedded_payload", EMBED_MODULE)
            mod = importlib.util.module_from_spec(spec)  # type: ignore
            assert spec and spec.loader
            spec.loader.exec_module(mod)  # type: ignore
            meta_json = getattr(mod, "EMBEDDED_META", "{}")
            current_meta = json.loads(meta_json)
            # Compare hash
            b64 = "".join(getattr(mod, "EMBEDDED_ARCHIVE_BASE64", []))
            cur_bytes = base64.b64decode(b64) if b64 else b""
            if _sha256(cur_bytes) == snap["meta"]["sha256"]:
                return False, current_meta
        except Exception:
            pass
    embed_snapshot(root)
    return True, snap["meta"]  # type: ignore


def extract_snapshot(dest: Path) -> Dict[str, object]:
    if not EMBED_MODULE.exists():
        raise FileNotFoundError("No embedded snapshot found")
    import importlib.util

    spec = importlib.util.spec_from_file_location("_embedded_payload", EMBED_MODULE)
    mod = importlib.util.module_from_spec(spec)  # type: ignore
    assert spec and spec.loader
    spec.loader.exec_module(mod)  # type: ignore
    b64 = "".join(getattr(mod, "EMBEDDED_ARCHIVE_BASE64", []))
    meta_json = getattr(mod, "EMBEDDED_META", "{}")
    data = base64.b64decode(b64)
    meta = json.loads(meta_json)
    dest.mkdir(parents=True, exist_ok=True)
    with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as tar:
        tar.extractall(dest)
    return {"path": str(dest), "meta": meta}


def analyze_dependencies(root: Optional[Path] = None) -> Dict[str, object]:
    """Lightweight dependency and structure analysis."""
    root = root or PROJECT_ROOT
    result: Dict[str, object] = {"root": str(root)}
    req = root / "requirements.txt"
    pyproject = root / "pyproject.toml"
    deps: List[str] = []
    if req.exists():
        deps = [line.strip() for line in req.read_text(encoding="utf-8").splitlines() if line.strip() and not line.strip().startswith("#")]
    result["requirements"] = deps
    if pyproject.exists():
        result["pyproject"] = True
    # Static imports scan
    imports: Dict[str, int] = {}
    for p in root.rglob("*.py"):
        if any(seg in {"__pycache__", ".venv", "venv", ".git", ".self_backup"} for seg in p.parts):
            continue
        try:
            for line in p.read_text(encoding="utf-8").splitlines():
                m = re.match(r"\s*import\s+([a-zA-Z0-9_\.]+)", line)
                if m:
                    top = m.group(1).split(".")[0]
                    imports[top] = imports.get(top, 0) + 1
                m2 = re.match(r"\s*from\s+([a-zA-Z0-9_\.]+)\s+import\s+", line)
                if m2:
                    top = m2.group(1).split(".")[0]
                    imports[top] = imports.get(top, 0) + 1
        except Exception:
            continue
    result["imports"] = imports
    return result


def backup_current(root: Optional[Path] = None) -> Path:
    root = root or PROJECT_ROOT
    backup_dir = root / ".self_backup"
    backup_dir.mkdir(exist_ok=True)
    ts = time.strftime("%Y%m%d-%H%M%S")
    out = backup_dir / f"backup-{ts}.tar.gz"
    files = _iter_project_files(root)
    data = _make_tar_bytes(root, files)
    out.write_bytes(data)
    return out


def replace_tree(src: Path, dest: Path) -> None:
    """Replace dest tree with src contents (safe-ish)."""
    import shutil
    # Copy over files from src to dest
    for p in src.rglob("*"):
        rel = p.relative_to(src)
        target = dest / rel
        if p.is_dir():
            target.mkdir(parents=True, exist_ok=True)
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(p, target)

