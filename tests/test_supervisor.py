import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

import pytest

from paperloom.supervisor import child

HARNESS = Path(__file__).parent / "fixtures" / "supervisor_harness.py"


def _pid_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def _wait_until(predicate, timeout: float = 10.0, interval: float = 0.1) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if predicate():
            return True
        time.sleep(interval)
    return predicate()


def _wait_for_json(path: Path, timeout: float = 15.0) -> dict:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if path.exists() and path.stat().st_size > 0:
            try:
                return json.loads(path.read_text())
            except json.JSONDecodeError:
                pass  # harness may still be mid-write
        time.sleep(0.1)
    raise TimeoutError(f"{path} never appeared with valid JSON")


def _launch_harness(mode: str, out: Path) -> subprocess.Popen:
    return subprocess.Popen([sys.executable, str(HARNESS), mode, "--out", str(out)])


def _cleanup(harness: subprocess.Popen) -> None:
    if harness.poll() is None:
        harness.kill()
        harness.wait(timeout=10)


def test_sigterm_parent_kills_child(tmp_path):
    """Spawn a long-running child, SIGTERM the parent (harness) process,
    assert the child is gone within 10s."""
    out = tmp_path / "pids.json"
    harness = _launch_harness("simple", out)
    try:
        child_pid = _wait_for_json(out)["child"]
        assert _pid_alive(child_pid)

        harness.send_signal(signal.SIGTERM)
        harness.wait(timeout=10)

        assert _wait_until(lambda: not _pid_alive(child_pid))
    finally:
        _cleanup(harness)


def test_raise_inside_child_context_manager_terminates_child():
    """Spawn a child, raise inside the `with child(...)` block, assert the
    child is gone."""
    proc_holder = {}
    with pytest.raises(RuntimeError):
        with child(["sleep", "100"]) as proc:
            proc_holder["proc"] = proc
            assert proc.poll() is None
            raise RuntimeError("boom")

    proc = proc_holder["proc"]
    assert _wait_until(lambda: not _pid_alive(proc.pid))


def test_grandchild_killed_via_process_group(tmp_path):
    """Spawn a child that itself spawns a grandchild, kill the parent
    (harness), assert the grandchild is gone too (validates process-group
    kill, not just direct-child termination)."""
    out = tmp_path / "pids.json"
    harness = _launch_harness("chain", out)
    try:
        data = _wait_for_json(out)
        child_pid, grandchild_pid = data["child"], data["grandchild"]
        assert _pid_alive(child_pid)
        assert _pid_alive(grandchild_pid)

        harness.send_signal(signal.SIGTERM)
        harness.wait(timeout=10)

        assert _wait_until(lambda: not _pid_alive(child_pid))
        assert _wait_until(lambda: not _pid_alive(grandchild_pid))
    finally:
        _cleanup(harness)


@pytest.mark.skipif(
    sys.platform != "linux",
    reason="PR_SET_PDEATHSIG orphan-proofing (the only thing that can catch "
    "os._exit/SIGKILL/OOM) is Linux-only",
)
def test_os_exit_parent_still_kills_children(tmp_path):
    """Spawn 10 children in parallel, os._exit(1) the parent (bypasses
    atexit), assert all 10 children are gone within 10s of parent death."""
    out = tmp_path / "pids.json"
    harness = _launch_harness("many", out)
    try:
        pids = _wait_for_json(out)["children"]
        assert len(pids) == 10
        for pid in pids:
            assert _pid_alive(pid)

        harness.wait(timeout=10)  # os._exit(1): returns almost immediately

        assert _wait_until(lambda: all(not _pid_alive(p) for p in pids))
    finally:
        _cleanup(harness)
