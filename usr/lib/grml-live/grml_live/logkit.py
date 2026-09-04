import contextlib
import functools
import os
import subprocess
import sys
from pathlib import Path
from typing import IO

try:
    # Python 3.14 internal API with a plan to stabliziation.
    # For now we treat this as an optional, possibly changing thing.
    # Worst case we get no colors, but also nothing should break.
    import _colorize
except ImportError:
    _colorize = None


def _check_stdout_tty():
    try:
        return sys.stdout.isatty()
    except NameError:
        return False


# We check this only at startup, as later one we tee our output into a log and
# then stdout.isatty NEVER returns True.
_STDOUT_IS_A_TTY = _check_stdout_tty()


@functools.cache
def _get_tty_color(colorname: str) -> str:
    if not _colorize:
        return ""
    try:
        colors = _colorize.get_colors()
    except Exception as except_inst:
        print(f"D: _colorize.get_colors failed: {except_inst}")
        return ""
    return getattr(colors, colorname, None) or ""


def _get_stdio_color(colorname: str) -> str:
    if not _STDOUT_IS_A_TTY:
        return ""
    return _get_tty_color(colorname)


def _print_colored(colorname: str, file: IO, prefix: str, *message_parts: str):
    start_color = _get_stdio_color(colorname)
    if start_color:
        end_color = _get_stdio_color("RESET")
    else:
        end_color = ""

    first = message_parts[0]
    if prefix:
        prefix += " "
    print(f"{start_color}{prefix}{first}", *message_parts[1:], file=file, end=f"\n{end_color}", flush=True)


def debug(*message_parts: str):
    _print_colored("RESET", sys.stdout, "D:", *message_parts)


def info(*message_parts: str):
    _print_colored("GREEN", sys.stdout, "I:", *message_parts)


def info_header(*message_parts: str):
    _print_colored("GREEN", sys.stdout, "", *message_parts)


def warn(*message_parts: str):
    _print_colored("BLUE", sys.stdout, "W:", *message_parts)


def error(*message_parts: str):
    _print_colored("RED", sys.stderr, "E:", *message_parts)


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
