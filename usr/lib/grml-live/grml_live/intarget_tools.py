import os
import shutil
from dataclasses import dataclass
from pathlib import Path


@dataclass(kw_only=True)
class CopyFilesArgs:
    mode: int
    recursive: bool
    ignore_missing: bool
    paths: list[str]


def do_fcopy_file(to_copy: Path, dest_root: Path, path: str, mode: int):
    dest_path = dest_root / path

    print(f"I: fcopy: Installing {to_copy} as {dest_path}.")
    try:
        dest_exists = bool(dest_path.lstat())
    except FileNotFoundError:
        dest_exists = False

    if dest_exists:
        print(f"W: fcopy: Destination {dest_path} already exists, removing.")
        dest_path.unlink()

    # this is probably fine, as we expect to run as root and do not support
    # different file/directory ownership.
    dest_path.parent.mkdir(exist_ok=True, parents=True)

    shutil.copy2(to_copy, dest_path, follow_symlinks=False)

    try:
        dest_path.chmod(mode, follow_symlinks=False)
    except NotImplementedError:
        pass

    os.chown(dest_path, 0, 0, follow_symlinks=False)

    return True


def do_fcopy_path(files_dir: Path, dest_root: Path, classes: list[str], path: str, mode: int) -> bool:
    to_copy = None
    for class_name in classes:
        class_path = files_dir / class_name / path
        if class_path.exists():
            to_copy = class_path

    if to_copy:
        do_fcopy_file(to_copy, dest_root, path, mode)
        return True
    else:
        return False


def do_fcopy_recursive(files_dir: Path, dest_root: Path, classes: list[str], path_root: str, mode: int):
    tree = {}

    for class_name in classes:
        class_files_dir = files_dir / class_name
        if not class_files_dir.exists():
            continue

        class_path_root = class_files_dir / path_root
        if not class_path_root.exists():
            continue

        files = [p.relative_to(class_files_dir) for p in class_path_root.glob("**/*") if not p.is_dir()]
        for file in files:
            tree[file] = class_name

    for path, class_name in tree.items():
        do_fcopy_file(files_dir / class_name / path, dest_root, path, mode)


def do_copy_files(
    conf_dir: Path, dest_root: Path, classes: list[str], files_name: str, copy_args: CopyFilesArgs
) -> int:
    print(f"D: copy_files {copy_args.recursive=} {copy_args.ignore_missing=} {copy_args.mode=} {copy_args.paths=}")
    rc = 0
    files_dir = conf_dir / files_name

    try:
        if copy_args.recursive:
            for path in copy_args.paths:
                do_fcopy_recursive(files_dir, dest_root, classes, path, copy_args.mode)

        else:
            for path in copy_args.paths:
                found = do_fcopy_path(files_dir, dest_root, classes, path, copy_args.mode)
                if not found and not copy_args.ignore_missing:
                    print(f"E: Source {path=} is missing")
                    rc = 1

    except Exception as except_inst:
        print(f"E: copy_files failed: {except_inst} - returning with exit code 130", flush=True)
        rc = 130

    return rc


def _parse_fcopy_args(fcopy_args: list[str]) -> CopyFilesArgs:
    user = "root"
    group = "root"
    mode = 0o644
    recursive = False
    ignore_missing = False
    paths = []

    # FAI fcopy parameters:
    # -B Remove backup files with suffix .pre_fcopy.
    # -r Copy recursively (traverse down the tree). Copy all files below SOURCE.
    #    These are all subdirectory leaves in the SOURCE tree.
    #    Ignore "ignored" directories (see "-I" for details).
    # -i Ignore warnings about no matching class and non-existing source directories.
    #    These warnings will not set the exit code to 1.
    # -v verbose
    # -m user,group,mode Set user, group and mode for all copied files (mode as octal
    #    number, user and group numeric id or name). If not specified, use file
    #    file-modes or data of source file.
    # -M Use default values for user, group and mode. This is equal to -m root,root,0644

    parse_m = False
    for index, arg in enumerate(fcopy_args):
        if parse_m:
            # TODO: handle errors
            user, group, mode = arg.split(",")
            mode = int(mode, 8)
            parse_m = False
        elif arg in ["-B", "-v"]:
            # defaulted / ignored
            pass
        elif arg == "-m":
            parse_m = True
        elif arg == "-M":
            user, group = "root", "root"
            mode = 0o644
        elif arg == "-r":
            recursive = True
        elif arg == "-i":
            ignore_missing = True
        elif not arg.startswith("-"):
            paths = fcopy_args[index:]
            break
        else:
            raise ValueError(f"fcopy: param {arg} not understood")

    if not paths:
        raise ValueError("fcopy: no paths given")

    paths = [path.lstrip("/") for path in paths]

    if user != "root" or group != "root":
        raise ValueError("E: When copying files, user/group must be root/root")

    return CopyFilesArgs(
        mode=mode,
        recursive=recursive,
        ignore_missing=ignore_missing,
        paths=paths,
    )


def do_fcopy(conf_dir: Path, chroot_dir: Path, classes: list[str], remaining_args: list[str]) -> int:
    try:
        copy_args = _parse_fcopy_args(remaining_args)
    except Exception as except_inst:
        print(f"E: Parsing fcopy_args {remaining_args!r} failed: {except_inst}")
        return 1

    return do_copy_files(conf_dir, chroot_dir, classes, "files", copy_args)


def _parse_copy_media_files_args(args: list[str]) -> CopyFilesArgs:
    mode = 0o644
    recursive = False
    ignore_missing = False
    paths = []

    # Supported parameters:
    # -r Copy recursively (traverse down the tree). Copy all files below SOURCE.
    #    These are all subdirectory leaves in the SOURCE tree.
    # -i Ignore warnings about no matching class and non-existing source directories.
    #    These warnings will not set the exit code to 1.
    # -m mode Set mode for all copied files (mode as octal number).

    parse_m = False
    for index, arg in enumerate(args):
        if parse_m:
            mode = int(arg, 8)
            parse_m = False
        elif arg == "-m":
            parse_m = True
        elif arg == "-r":
            recursive = True
        elif arg == "-i":
            ignore_missing = True
        elif not arg.startswith("-"):
            paths = args[index:]
            break
        else:
            raise ValueError(f"copy-media-files: param {arg} not understood")

    if not paths:
        raise ValueError("copy-media-files: no paths given")

    paths = [path.lstrip("/") for path in paths]

    return CopyFilesArgs(
        mode=mode,
        recursive=recursive,
        ignore_missing=ignore_missing,
        paths=paths,
    )


def do_copy_media_files(conf_dir: Path, chroot_dir: Path, classes: list[str], remaining_args: list[str]) -> int:
    if not remaining_args:
        raise ValueError("copy-media-files: need 2 or more parameters")

    target = remaining_args.pop(0)
    if target not in ("media", "netboot"):
        raise ValueError(f"copy-media-files: target {target} not understood")

    try:
        copy_args = _parse_copy_media_files_args(remaining_args)
    except Exception as except_inst:
        print(f"E: Parsing fcopy_args {remaining_args!r} failed: {except_inst}")
        return 1

    dest_dir = chroot_dir / "grml-live" / target

    return do_copy_files(conf_dir, dest_dir, classes, "media-files", copy_args)
