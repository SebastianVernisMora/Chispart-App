"""
Minimal unified diff patch applier (pure Python).

Supports common cases:
- Modify existing files via @@ hunks
- Create new files when source is /dev/null
- Delete files when target is /dev/null

Limitations:
- Applies hunks at the specified line numbers; no fuzzy matching
- Does not support file renames/copies or mode changes
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple, Dict, Any


@dataclass
class Hunk:
    src_start: int
    src_len: int
    dst_start: int
    dst_len: int
    lines: List[Tuple[str, str]]  # (op, text) where op in {' ', '+', '-'}


@dataclass
class FilePatch:
    src: str
    dst: str
    hunks: List[Hunk]


def _parse_hunk_header(header: str) -> Tuple[int, int, int, int]:
    # Format: @@ -l,s +l,s @@ optional
    import re

    m = re.match(r"@@ -(?P<sline>\d+)(,(?P<slen>\d+))? \+(?P<dline>\d+)(,(?P<dlen>\d+))? @@", header)
    if not m:
        raise ValueError(f"Invalid hunk header: {header}")
    sline = int(m.group("sline"))
    slen = int(m.group("slen") or 1)
    dline = int(m.group("dline"))
    dlen = int(m.group("dlen") or 1)
    return sline, slen, dline, dlen


def parse_unified_diff(diff_text: str) -> List[FilePatch]:
    lines = diff_text.splitlines()
    i = 0
    patches: List[FilePatch] = []
    while i < len(lines):
        line = lines[i]
        # Skip optional diff headers (e.g., diff --git ...)
        if line.startswith("diff "):
            i += 1
            continue
        if line.startswith("--- "):
            src = line[4:].strip()
            i += 1
            if i >= len(lines) or not lines[i].startswith("+++ "):
                raise ValueError("Malformed diff: expected +++ after ---")
            dst = lines[i][4:].strip()
            i += 1
            hunks: List[Hunk] = []
            while i < len(lines) and lines[i].startswith("@@ "):
                header = lines[i]
                sline, slen, dline, dlen = _parse_hunk_header(header)
                i += 1
                hunk_lines: List[Tuple[str, str]] = []
                while i < len(lines) and (lines[i].startswith(" ") or lines[i].startswith("+") or lines[i].startswith("-")):
                    hunk_lines.append((lines[i][0], lines[i][1:]))
                    i += 1
                hunks.append(Hunk(sline, slen, dline, dlen, hunk_lines))
            patches.append(FilePatch(src=src, dst=dst, hunks=hunks))
        else:
            i += 1
    return patches


def apply_patch_to_text(original: List[str], hunks: List[Hunk]) -> List[str]:
    # original is a list of lines WITHOUT trailing newlines
    content = original[:]
    offset = 0
    for h in hunks:
        # Convert 1-based line number to 0-based index
        idx = h.src_start - 1 + offset
        # Build segment from hunk
        # Verify context/removals match
        check_segment: List[str] = []
        for op, text in h.lines:
            if op in (' ', '-'):
                check_segment.append(text)
        # Extract source segment for verification
        src_seg_len = len([1 for op, _ in h.lines if op in (' ', '-')])
        src_segment = content[idx: idx + src_seg_len]
        if src_segment != check_segment:
            raise ValueError("Hunk context mismatch; cannot apply cleanly")
        # Construct destination segment
        dst_segment: List[str] = [text for op, text in h.lines if op in (' ', '+')]
        # Replace in content
        content[idx: idx + src_seg_len] = dst_segment
        # Update offset for subsequent hunks
        offset += len(dst_segment) - src_seg_len
    return content


def apply_unified_diff(diff_text: str, root_dir: str | Path = ".") -> Dict[str, Any]:
    root = Path(root_dir).resolve()
    patches = parse_unified_diff(diff_text)
    results: Dict[str, Any] = {"applied": [], "created": [], "deleted": [], "errors": []}

    for p in patches:
        src = p.src.split()[-1]
        dst = p.dst.split()[-1]
        # Normalize paths (remove a/ and b/ prefixes if present)
        def norm(path: str) -> str:
            if path.startswith("a/") or path.startswith("b/"):
                return path[2:]
            return path

        src_path = norm(src)
        dst_path = norm(dst)

        # Handle creations and deletions
        if src_path == "/dev/null":
            # Create new file dst_path from hunks: lines with + or ' '
            try:
                lines: List[str] = []
                for h in p.hunks:
                    for op, text in h.lines:
                        if op in (' ', '+'):
                            lines.append(text)
                out_path = (root / dst_path)
                out_path.parent.mkdir(parents=True, exist_ok=True)
                out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
                results["created"].append(str(out_path))
            except Exception as e:
                results["errors"].append({"file": dst_path, "error": str(e)})
            continue
        if dst_path == "/dev/null":
            # Delete existing file
            try:
                del_path = (root / src_path)
                if del_path.exists():
                    del_path.unlink()
                results["deleted"].append(str(del_path))
            except Exception as e:
                results["errors"].append({"file": src_path, "error": str(e)})
            continue

        # Modify existing file
        try:
            target = (root / src_path)
            if not target.exists():
                # If src doesn't exist, try dst as fallback
                target = (root / dst_path)
            original_text = target.read_text(encoding="utf-8").splitlines()
            new_text = apply_patch_to_text(original_text, p.hunks)
            target.write_text("\n".join(new_text) + "\n", encoding="utf-8")
            results["applied"].append(str(target))
        except Exception as e:
            results["errors"].append({"file": dst_path or src_path, "error": str(e)})

    return results

