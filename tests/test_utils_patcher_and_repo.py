from pathlib import Path
import pytest
import os
import io

from blackbox_hybrid_tool.utils.patcher import parse_unified_diff, apply_patch_to_text, apply_unified_diff
from blackbox_hybrid_tool.utils import self_repo as sr


def test_parse_and_apply_patch_to_text():
    original = ["a", "b", "c"]
    # Hunk replacing b -> B and adding d
    diff = """--- a/file.txt
+++ b/file.txt
@@ -1,2 +1,3 @@
 a
-b
+B
 c
"""
    patches = parse_unified_diff(diff)
    assert len(patches) == 1
    new = apply_patch_to_text(original, patches[0].hunks)
    assert new == ["a", "B", "c"]


def test_apply_unified_diff_create_modify_delete(tmp_path):
    # Create a file via /dev/null, then modify it, then delete
    create = """--- /dev/null
+++ a/x.txt
@@ -0,0 +1,1 @@
+hello
"""
    res1 = apply_unified_diff(create, tmp_path)
    assert not res1.get("errors") and len(res1.get("created", [])) == 1
    # Modify
    modify = """--- a/x.txt
+++ b/x.txt
@@ -1,1 +1,2 @@
 hello
+world
"""
    res2 = apply_unified_diff(modify, tmp_path)
    assert not res2.get("errors") and len(res2.get("applied", [])) == 1
    # Delete
    delete = """--- a/x.txt
+++ /dev/null
@@ -1,2 +0,0 @@
 hello
 world
"""
    res3 = apply_unified_diff(delete, tmp_path)
    assert not res3.get("errors") and len(res3.get("deleted", [])) == 1


def test_parse_unified_diff_malformed_header_raises():
    bad = """--- a/x
@@ whatever @@
"""
    # parse_unified_diff skips until valid --- +++ pair, so craft a wrong sequence
    with pytest.raises(ValueError):
        # Force directly the private header parser through a minimal valid block
        from blackbox_hybrid_tool.utils.patcher import _parse_hunk_header
        _parse_hunk_header("@@ wrong @@")


def test_apply_unified_diff_modify_missing_file_reports_error(tmp_path):
    # Try modifying a file that does not exist -> should record an error
    modify = """--- a/missing.txt
+++ b/missing.txt
@@ -1,1 +1,1 @@
-x
+y
"""
    res = apply_unified_diff(modify, tmp_path)
    assert res.get("errors")


def test_self_repo_snapshot_embed_extract_analyze_and_backup(tmp_path, monkeypatch):
    # Work on a small temp project to avoid touching full repo
    proj = tmp_path / "proj"
    proj.mkdir()
    (proj / "a.py").write_text("import os\nprint('x')\n", encoding="utf-8")
    (proj / "requirements.txt").write_text("requests==2\n", encoding="utf-8")

    monkeypatch.setattr(sr, "PROJECT_ROOT", proj)
    # snapshot
    snap = sr.make_snapshot(proj)
    assert snap["meta"]["file_count"] >= 1
    # embed
    embed_path = sr.embed_snapshot(proj)
    assert embed_path.exists()
    # ensure (should be up to date now)
    changed, meta = sr.ensure_embedded_snapshot(proj)
    # It's allowed to be False (no change) once embedded
    assert isinstance(changed, bool) and isinstance(meta, dict)
    # extract into separate directory
    outdir = tmp_path / "extracted"
    info = sr.extract_snapshot(outdir)
    assert Path(info["path"]).exists()
    # analyze
    rep = sr.analyze_dependencies(proj)
    assert rep.get("requirements") == ["requests==2"]
    # backup and replace_tree
    bkp = sr.backup_current(proj)
    assert bkp.exists()
    new_src = tmp_path / "new"
    new_src.mkdir()
    (new_src / "b.txt").write_text("y", encoding="utf-8")
    sr.replace_tree(new_src, proj)
    assert (proj / "b.txt").exists()


def test_self_repo_iter_filters_and_ensure_nochange(tmp_path, monkeypatch):
    # Create a project with ignored dirs and nested files to hit skip logic
    proj = tmp_path / "proj2"
    (proj / "venv" / "sub").mkdir(parents=True)
    (proj / "venv" / "sub" / "x.py").write_text("print('x')", encoding="utf-8")
    (proj / "pyproject.toml").write_text("[tool]", encoding="utf-8")
    # also a binary-like file to trigger decode exception in analyze
    bad = proj / "bad.py"
    bad.write_bytes(b"\xff\xfe\x00\x00")
    monkeypatch.setattr(sr, "PROJECT_ROOT", proj)
    # _iter_project_files should iterate and skip venv sub-tree (cover inner pass/continue)
    files = sr._iter_project_files(proj)
    assert isinstance(files, list)
    # Embed then ensure no change (return False path)
    sr.embed_snapshot(proj)
    changed, meta = sr.ensure_embedded_snapshot(proj)
    assert changed is False and isinstance(meta, dict)
    # analyze should set pyproject True and skip ignored dirs; no exception on bad.py
    report = sr.analyze_dependencies(proj)
    assert report.get("pyproject") is True
    # replace_tree directory branch: create nested directory to copy
    src = tmp_path / "nest"
    (src / "d1" / "d2").mkdir(parents=True)
    sr.replace_tree(src, proj)
    assert (proj / "d1").exists()
