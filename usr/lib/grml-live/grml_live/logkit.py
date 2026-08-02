import contextlib
import os
import subprocess
import sys
from pathlib import Path


@contextlib.contextmanager
def tee_output_to(logfile: Path):
    """Duplicate stdout and stderr to logfile."""
    logfile.unlink(missing_ok=True)
    logfile.touch()

    tee_proc = subprocess.Popen(["tee", "-a", logfile], stdin=subprocess.PIPE)

    sys.stdout.flush()
    sys.stderr.flush()
    saved_stdout_fd = os.dup(1)
    saved_stderr_fd = os.dup(2)

    os.dup2(tee_proc.stdin.fileno(), 1)
    os.dup2(tee_proc.stdin.fileno(), 2)
    # Drop our copy of the stdin FD, so fd 1 and 2 are the only writers left and tee gets EOF below.
    tee_proc.stdin.close()

    # print() is block buffered whenever fd 1 is not a tty.
    # Turn on life buffering so the logs do not get intertwined.
    sys.stdout.reconfigure(line_buffering=True)

    try:
        yield
    finally:
        sys.stdout.flush()
        sys.stderr.flush()
        # Restoring closes the last write ends, so tee reaches EOF and exits.
        os.dup2(saved_stdout_fd, 1)
        os.dup2(saved_stderr_fd, 2)
        os.close(saved_stdout_fd)
        os.close(saved_stderr_fd)
        tee_proc.wait()
