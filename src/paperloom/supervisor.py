"""Subprocess supervision. Every subprocess paperloom spawns (MinerU and its
descendants) must be reaped on every exit path — normal completion,
KeyboardInterrupt, SIGTERM, SIGHUP, an unhandled exception, os._exit, or the
process being SIGKILLed/OOM-killed. See §6 of paperloom.md.

Every subprocess.Popen call in the codebase must go through `spawn()` or the
`child()` context manager below — never call subprocess.Popen directly."""

import atexit
import ctypes
import os
import signal
import subprocess
import sys
import threading
import weakref
from contextlib import contextmanager

PR_SET_PDEATHSIG = 1  # Linux prctl() constant; see prctl(2)


def _pdeathsig_preexec() -> None:
    """POSIX pre-exec hook: ask the kernel to SIGKILL this child the instant
    its parent (the paperloom process) dies, for ANY reason — os._exit,
    SIGKILL, OOM-kill, crash. atexit/signal handlers can't cover those cases
    since they require the parent to run code while it dies; this does not.
    Linux-only (no equivalent prctl on macOS/Windows); no-ops elsewhere."""
    if sys.platform == "linux":
        try:
            libc = ctypes.CDLL("libc.so.6", use_errno=True)
            libc.prctl(PR_SET_PDEATHSIG, signal.SIGKILL)
        except OSError:
            pass


class Supervisor:
    def __init__(self):
        self._procs: set[weakref.ref[subprocess.Popen]] = set()
        self._lock = threading.Lock()
        atexit.register(self.shutdown)
        sig_names = ("SIGTERM", "SIGINT", "SIGHUP")
        for name in sig_names:
            sig = getattr(signal, name, None)
            if sig is None:
                continue  # SIGHUP doesn't exist as an attribute on Windows
            try:
                signal.signal(sig, self._on_signal)
            except (ValueError, AttributeError):
                pass  # signals not settable in threads

    def spawn(self, cmd: list[str], **kwargs) -> subprocess.Popen:
        popen_kwargs = dict(kwargs)
        if sys.platform != "win32":
            popen_kwargs.setdefault("start_new_session", True)
            popen_kwargs.setdefault("preexec_fn", _pdeathsig_preexec)
        else:
            popen_kwargs.setdefault(
                "creationflags",
                subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NO_WINDOW,
            )
        proc = subprocess.Popen(cmd, **popen_kwargs)
        with self._lock:
            self._procs.add(weakref.ref(proc))
        return proc

    def _terminate(self, proc: subprocess.Popen) -> None:
        if proc.poll() is not None:
            return
        try:
            if sys.platform != "win32":
                os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
            else:
                proc.send_signal(signal.CTRL_BREAK_EVENT)
        except (ProcessLookupError, OSError):
            return
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            try:
                if sys.platform != "win32":
                    os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
                else:
                    proc.kill()
            except (ProcessLookupError, OSError):
                pass

    def shutdown(self) -> None:
        with self._lock:
            refs = list(self._procs)
            self._procs.clear()
        for ref in refs:
            proc = ref()
            if proc is not None:
                self._terminate(proc)

    def _on_signal(self, signum, frame):
        self.shutdown()
        sys.exit(128 + signum)


_supervisor = Supervisor()


def spawn(cmd: list[str], **kwargs) -> subprocess.Popen:
    """Only entry point for spawning subprocesses in paperloom."""
    return _supervisor.spawn(cmd, **kwargs)


@contextmanager
def child(cmd: list[str], **kwargs):
    """Context manager: spawn, yield, terminate on exit even if user code raises."""
    proc = spawn(cmd, **kwargs)
    try:
        yield proc
    finally:
        _supervisor._terminate(proc)
