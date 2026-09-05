#!/usr/bin/env python3
# called by minifai inside an unshare environment.
# Ideally uses nothing from minifai.
import json
import os
import shutil
import socket
import struct
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any, ParamSpec

from . import intarget_tools

SELF = Path(__file__)
ENTRY_POINT = Path(__file__).parent.parent / "unshared_helper"
assert ENTRY_POINT.exists()
_IS_EXECUTING = False
_OPERATIONS = {}

_P = ParamSpec("_P")


def _encodable_arg(arg):
    if isinstance(arg, Path):
        return str(arg)
    if isinstance(arg, list):
        return [_encodable_arg(value) for value in arg]
    return arg


def _operation(func: Callable[_P, Any]) -> Callable[_P, dict]:
    # Types are for the building mode. The execution path is not type checked.
    op_name = func.__name__
    assert op_name not in _OPERATIONS, f"operation {op_name} already registered"
    _OPERATIONS[op_name] = func

    def inner(*args: _P.args, **kwargs: _P.kwargs) -> dict:
        if _IS_EXECUTING:
            return func(*args, **kwargs)
        else:
            return {
                "op": op_name,
                "args": [_encodable_arg(arg) for arg in args],
                "kwargs": {k: _encodable_arg(v) for (k, v) in kwargs.items()},
            }

    inner.__name__ = op_name
    return inner


@_operation
def hello_world():
    print(f"Hi from {SELF} - running as {os.getuid()} in {os.getcwd()}")


@_operation
def mkdir(path: Path | str):
    Path(path).mkdir()


@_operation
def ensure_dir(path: Path | str):
    Path(path).mkdir(exist_ok=True)


@_operation
def ensure_empty_dir(path: Path | str):
    path = Path(path)
    if path.exists():
        shutil.rmtree(path)
    path.mkdir()


@_operation
def fcopy(conf_dir: Path | str, chroot_dir: Path | str, classes: str, arglist: str):
    conf_dir = Path(conf_dir)
    chroot_dir = Path(chroot_dir)
    rc = intarget_tools.do_fcopy(conf_dir, chroot_dir, classes.split(" "), arglist.split(" "))
    return rc


@_operation
def copy_media_files(conf_dir: Path | str, chroot_dir: Path | str, classes: str, arglist: str):
    conf_dir = Path(conf_dir)
    chroot_dir = Path(chroot_dir)
    rc = intarget_tools.do_copy_media_files(conf_dir, chroot_dir, classes.split(" "), arglist.split(" "))
    return rc


@_operation
def write_file_text(path: Path | str, contents: str, executable: bool = False):
    path = Path(path)
    with path.open("wt") as file:
        file.write(contents)
        if executable:
            os.fchmod(file.fileno(), 0o755)


@_operation
def have_text_in_file(path: Path | str, text: str):
    return 0 if (text in Path(path).read_text()) else 1


@_operation
def unlink(path: Path | str):
    path = Path(path)
    path.unlink()


@_operation
def chown(path: Path | str, numeric_owner: str, numeric_group: str):
    path = Path(path)
    os.chown(str(path), int(numeric_owner), int(numeric_group), follow_symlinks=False)


@_operation
def run_program(args, **kwargs):
    """Run program. Output goes to stdout/stderr. Caller needs to check returncode."""
    kwargs["stdin"] = subprocess.DEVNULL
    args_str = '" "'.join(args)
    print(f'D: Running unshared: "{args_str}"', flush=True)
    try:
        returncode = subprocess.run(args, check=False, **kwargs).returncode
    finally:
        sys.stdout.flush()
        sys.stderr.flush()
    return returncode


@_operation
def bindmount_proc_sys_into(root_dir: Path | str):
    root_dir = Path(root_dir)
    for mount in ["proc", "sys"]:
        dest_dir = str(root_dir / mount)
        print(f"I: Bind-mounting /{mount} into {dest_dir} ...")
        subprocess.run(["mount", "--rbind", f"/{mount}", dest_dir], check=True, stdin=subprocess.DEVNULL)

    dev_fd_symlink = root_dir / "dev" / "fd"
    if not dev_fd_symlink.exists(follow_symlinks=False):
        print(f"I: Setting up {dev_fd_symlink} ...")
        dev_fd_symlink.unlink(missing_ok=True)
        subprocess.run(["ln", "-s", "/proc/self/fd", dev_fd_symlink], check=True, stdin=subprocess.DEVNULL)


def _parse_and_run(ops_stream: list[dict], operations: dict) -> int:
    for op in ops_stream:
        op_name = op["op"]
        args = op["args"]
        kwargs = op["kwargs"]
        sys.stdout.flush()
        try:
            rc = operations[op_name](*args, **kwargs)
        except Exception as except_inst:
            print(f"E: {op_name} failed: {except_inst}", flush=True)
            print(f"E: {op_name} args: {args=}", flush=True)
            print(f"E: {op_name} kwargs: {kwargs=}", flush=True)
            rc = 1

        sys.stdout.flush()
        if rc:
            return rc

    return 0


def _frame_message(message: str) -> bytes:
    encoded = message.encode()
    return struct.pack("<L", len(encoded)) + encoded


def _reply(sock, jsonable_data):
    sock.sendall(_frame_message(json.dumps(jsonable_data)))


def _socket_recv_exactly(sock, size: int) -> bytes:
    buf = b""
    while len(buf) < size:
        chunk = sock.recv(size - len(buf))
        if not chunk:
            break  # peer closed
        buf += chunk
    return buf


class RemoteCleanlyClosedConnection(Exception):
    pass


class RemoteUnexpectedlyClosedConnection(Exception):
    pass


class InvalidMessageReceived(Exception):
    pass


def _socket_read_framed_message(sock) -> str:
    size = _socket_recv_exactly(sock, 4)
    if not size:
        raise RemoteCleanlyClosedConnection("disconnected")
    if len(size) != 4:
        raise RemoteUnexpectedlyClosedConnection(f"short size read, received {len(size)}")
    (size,) = struct.unpack("<L", size)
    if not size:
        raise InvalidMessageReceived("size 0 message")

    # read data
    buf = _socket_recv_exactly(sock, size)
    if len(buf) != size:
        raise RemoteUnexpectedlyClosedConnection(f"short data read, received {len(buf)}, expected {size}")
    return buf.decode()


def _server(socket_path, operations) -> int:
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM | socket.SOCK_CLOEXEC) as sock:
        sock.connect(socket_path)
        while True:
            try:
                message = _socket_read_framed_message(sock)
            except RemoteCleanlyClosedConnection:
                return 0  # client closed cleanly
            except (RemoteUnexpectedlyClosedConnection, InvalidMessageReceived) as except_inst:
                print(f"E: {except_inst}")
                return 1

            try:
                decoded = json.loads(message)
            except Exception as except_inst:
                print(f"E: JSON decode failed: {except_inst}")
                _reply(sock, {"error": "invalid_json"})
                continue
            if "ops" not in decoded:
                print("E: JSON is missing ops key")
                _reply(sock, {"error": "invalid_json"})
                continue
            rc = _parse_and_run(decoded["ops"], operations)
            _reply(sock, {"returncode": rc})


def send_ops_to_server(socket, ops: list[dict]):
    sys.stdout.flush()
    assert ops
    assert isinstance(ops[0]["op"], str)
    try:
        message = json.dumps({"ops": ops})
    except TypeError:
        print(f"ops: {ops}", flush=True)
        raise
    socket.sendall(_frame_message(message))
    result = _socket_read_framed_message(socket)
    res = json.loads(result)
    sys.stdout.flush()
    if "error" in res:
        raise RuntimeError(f"unshared helper: {res['error']}")
    return res["returncode"]


def make_server_command(socket_path):
    return [str(ENTRY_POINT), "--server", socket_path]


def main() -> int:
    if len(sys.argv) != 3 or sys.argv[1:2] != ["--server"]:
        print(f"E: Usage: {ENTRY_POINT} --server <socket_path>")
        return 1
    return _server(sys.argv[2], _OPERATIONS)


if __name__ == "__main__":
    sys.exit(main())
