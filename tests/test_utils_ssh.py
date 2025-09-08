from unittest.mock import patch

from blackbox_hybrid_tool.utils.ssh import run_ssh_command, sync_files, deploy_remote


def test_run_ssh_command_invokes_subprocess(monkeypatch):
    class R:
        returncode = 0
        stdout = "ok"
        stderr = ""
    with patch("blackbox_hybrid_tool.utils.ssh.subprocess.run", return_value=R()) as m:
        code = run_ssh_command("host", "echo hi", user="u", key_path="k", port=2222)
        assert code == 0
        called = "ssh" in " ".join(m.call_args[0][0])
        assert called


def test_sync_files_invokes_scp(monkeypatch):
    class R:
        returncode = 0
        stdout = ""
        stderr = ""
    with patch("blackbox_hybrid_tool.utils.ssh.subprocess.run", return_value=R()) as m:
        code = sync_files("file.txt", "/tmp/x", host="h", user="u", key_path="k", port=2222, recursive=True)
        assert code == 0
        assert m.call_args[0][0][0] == "scp"


def test_deploy_remote_commands(monkeypatch):
    # Ensure we call run_ssh_command with a constructed command
    with patch("blackbox_hybrid_tool.utils.ssh.run_ssh_command", return_value=0) as r:
        assert deploy_remote("h", "/opt/app", user="u", use_docker=True, compose=True) == 0
        assert deploy_remote("h", "/opt/app", user="u", use_docker=True, compose=False) == 0
        assert deploy_remote("h", "/opt/app", user="u", use_docker=False) == 0
        assert r.call_count == 3

