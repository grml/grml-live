#!/usr/bin/env python3
# called by minifai inside an unshare environment.
# Ideally uses nothing from minifai.
import itertools
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
def rmdir(path: Path | str):
    path = Path(path)
    path.rmdir()


@_operation
def run_program(args, **kwargs):
    """Run program. Output goes to stdout/stderr. Caller needs to check returncode."""
    kwargs["stdin"] = subprocess.DEVNULL
    print(f"D: run_program: {args=}")
    return subprocess.run(args, check=False, **kwargs).returncode


@_operation
def bindmount_proc_sys_into(root_dir: Path | str):
    root_dir = Path(root_dir)
    for mount in ["proc", "sys"]:
        dest_dir = str(root_dir / mount)
        print(f"I: Bind-mounting /{mount} into {dest_dir}")
        subprocess.run(["mount", "--rbind", f"/{mount}", dest_dir], check=True, stdin=subprocess.DEVNULL)


@_operation
def clamp_to_source_date(root_dir: Path | str, source_date_epoch: str):
    root_dir = Path(root_dir)
    epoch = int(source_date_epoch)
    dev0 = root_dir.lstat().st_dev

    print(f"I: Clamping mtimes in {root_dir} to {epoch}")
    os.utime(root_dir, (epoch, epoch), follow_symlinks=False)

    for dirpath, dirnames, filenames in os.walk(root_dir, followlinks=False):
        kept_dirs = []
        for name in dirnames:
            path = os.path.join(dirpath, name)
            stat_result = os.lstat(path)
            if stat_result.st_dev != dev0:
                continue
            kept_dirs.append(name)
            if stat_result.st_mtime > epoch:
                os.utime(path, (epoch, epoch), follow_symlinks=False)

        dirnames[:] = kept_dirs

        for name in itertools.chain(dirnames, filenames):
            path = os.path.join(dirpath, name)
            if os.lstat(path).st_mtime > epoch:
                os.utime(path, (epoch, epoch), follow_symlinks=False)


def _parse_and_run(ops_stream: list[dict], operations: dict) -> int:
    for op in ops_stream:
        op_name = op["op"]
        args = op["args"]
        kwargs = op["kwargs"]
        try:
            print(f"I: unshared_helper executing {op_name} {' '.join(str(arg) for arg in args)} {kwargs}", flush=True)
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


def _reply(sock, jsonable_data):
    encoded = json.dumps(jsonable_data).encode()
    sock.send(encoded)


def _server(socket_path, operations) -> int:
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
        sock.connect(socket_path)
        while True:
            size = sock.recv(4)
            if not size:
                return 0
            (size,) = struct.unpack("<L", size)
            if not size:
                return 0
            data = sock.recv(size).decode()
            try:
                decoded = json.loads(data)
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
        encoded = json.dumps({"ops": ops}).encode()
    except TypeError:
        print(f"ops: {ops}", flush=True)
        raise
    size = struct.pack("<L", len(encoded))
    socket.send(size + encoded)
    result = socket.recv(4096)
    res = json.loads(result)
    sys.stdout.flush()
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
