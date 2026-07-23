# This is a spaghetti-code minimal reimplementation of the FAI API surface grml-live needs,
# for building Grml Live Linux. If you have additional API surface needs, please contribute.
# Please beware that this implementation is an interim step, and we may or may not continue
# with the FAI API.
#
import argparse
import contextlib
import datetime
import json
import os
import shlex
import shutil
import socket
import subprocess
import sys
import tempfile
import traceback
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from threading import Event, Thread

from . import unshared_helper
from .classes import ClassFileParsingFailed, parse_class_varfile
from .packages import PackageList, parse_class_packages

APT_DEBUG_ACQUIRE = "Debug::Acquire::http=true"

# UID/GID *inside* the userns that is mapped to the executing user.
UNSHARE_UID = 65536
UNSHARE_GID = 65536


class FaiScriptFailed(Exception):
    pass


class ProgramStartFailed(Exception):
    pass


class FaiAction(StrEnum):
    DIRINSTALL = "dirinstall"
    SOFTUPDATE = "softupdate"
    RECONFIGURE = "reconfigure"
    REBUILD = "rebuild"
    REBUILD_MEDIA = "rebuild_media"


@dataclass
class DynamicState:
    """Holds state that can change in FAI hooks, for example by calling "skiptask"."""

    def __init__(self):
        self.skip_tasks = set()


@dataclass(kw_only=True)
class ChrootBuildDirectories:
    # xxx_inside is always the path _inside_ the chroot ("relative", if chrooted).
    build_dir_inside: str
    build_dir: Path
    log_dir_inside: str
    log_dir: Path
    netboot_dir_inside: str
    netboot_dir: Path
    media_dir_inside: str
    media_dir: Path
    sources_dir_inside: str
    sources_dir: Path


@dataclass
class UnsharedService:
    request_socket: socket.socket

    def run(self, op: dict, check=True) -> int:
        res = unshared_helper.send_ops_to_server(self.request_socket, [op])
        if check and res:
            raise RuntimeError(f"E: unshared operation failed with rc={res}, op: {op}")
        return res

    def batch(self, ops: list[dict], check=True) -> int:
        res = unshared_helper.send_ops_to_server(self.request_socket, ops)
        if check and res:
            raise RuntimeError(f"E: unshared operations failed with rc={res}, ops: {ops}")
        return res


def now_for_log() -> str:
    return datetime.datetime.now().isoformat()


def _unquote_bash_single(s: str):
    out, i, n = [], 0, len(s)
    while i < n:
        c = s[i]
        if c == "'":
            j = s.index("'", i + 1)
            out.append(s[i + 1 : j])
            i = j + 1
        elif c == "\\" and i + 1 < n:
            out.append(s[i + 1])
            i += 2
        else:
            out.append(c)
            i += 1
    return "".join(out)


def _parse_bash_set(text: str) -> dict[str, str]:
    """Parse output of bash set, when restricted to single line key=value pairs."""
    env = {}
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        key, _, value = line.partition("=")
        env[key] = _unquote_bash_single(value)
    return env


def _prepare_subprocess_args(args, *, unshared: bool, chroot_dir: Path | None, **kwargs):
    args = [arg if isinstance(arg, str) else str(arg) for arg in args]
    args_str = '" "'.join(args)
    if "env" in kwargs:
        # Always pass-through SOURCE_DATE_EPOCH
        env = {}
        if "SOURCE_DATE_EPOCH" in os.environ:
            env["SOURCE_DATE_EPOCH"] = os.environ["SOURCE_DATE_EPOCH"]
        kwargs["env"] = env | kwargs["env"]  # do not update original dict

    prefix_args = []
    hint = ""
    if unshared:
        unshare = [
            "unshare",
            "--user",
            "--map-auto",
            f"--map-user={UNSHARE_UID}",
            f"--map-group={UNSHARE_GID}",
            "--pid",
            "--mount-proc",
            "--uts",
            "--fork",
            "--kill-child",
            "--setuid",
            "0",
            "--setgid",
            "0",
        ]
        hint = "unshared"
        if chroot_dir:
            unshare = [*unshare, "--root", str(chroot_dir)]
            hint = f"{hint} in chroot {chroot_dir}"
        prefix_args = [*unshare, "--"]
    elif chroot_dir:
        prefix_args = ["chroot", str(chroot_dir)]

    print(f'D: Running{" " + hint if hint else ""} "{args_str}"', flush=True)
    return prefix_args, args, kwargs


def run_x(args, check: bool = True, unshared: bool = False, chroot_dir: Path | None = None, **kwargs):
    """Run program. Output goes to stdout/stderr."""
    prefix_args, args, kwargs = _prepare_subprocess_args(args, unshared=unshared, chroot_dir=chroot_dir, **kwargs)

    return subprocess.run(prefix_args + args, check=check, **kwargs)


def popen(args, unshared: bool = False, chroot_dir: Path | None = None, **kwargs):
    prefix_args, args, kwargs = _prepare_subprocess_args(args, unshared=unshared, chroot_dir=chroot_dir, **kwargs)
    return subprocess.Popen(prefix_args + args, **kwargs)


def run_chrooted(chroot_dir: Path, args, check: bool = True, unshared: bool = True, **kwargs):
    """Run program with arguments in chroot chroot_dir."""
    kwargs["env"] = {
        "PATH": "/usr/sbin:/sbin:/usr/bin:/bin",
        "TERM": "dumb",
    } | kwargs.get("env", {})
    return run_x(
        args,
        check=check,
        unshared=unshared,
        chroot_dir=chroot_dir,
        **kwargs,
    )


def chrooted_dpkg_print_architecture(chroot_dir: Path) -> str:
    """Read dpkg --print-architecture of chroot"""
    result = run_chrooted(chroot_dir, ["dpkg", "--print-architecture"], capture_output=True)
    return result.stdout.strip().decode()


def chrooted_apt_install(chroot_dir: Path, install_list: list[str]):
    """Run apt install in chroot_dir."""
    env = {
        "DEBIAN_FRONTEND": "noninteractive",
    }
    args = [
        "apt",
        "-oapt::cmd::disable-script-warning=1",
        "install",
        "-q",
        "-y",
        "--no-install-recommends",
        *install_list,
    ]
    if os.environ.get("GRML_LIVE_DEBUG_APT", "") != "":
        args.insert(1, f"-o{APT_DEBUG_ACQUIRE}")
    run_chrooted(
        chroot_dir,
        args,
        env=env,
        stdin=subprocess.DEVNULL,
    )


def chrooted_debconf_set_selections(chroot_dir: Path, selections_file: Path):
    """Run debconf-set-selections in chroot_dir, piping in selections_file."""

    if not selections_file.exists():
        return

    env = {
        "DEBIAN_FRONTEND": "noninteractive",
    }
    print("I: Loading debconf selections from", selections_file)
    with selections_file.open("r") as selections_fd:
        run_chrooted(chroot_dir, ["debconf-set-selections", "-v"], env=env, stdin=selections_fd)


def run_script(chroot_dir: Path, script: Path, helper_tools_paths: list[Path], env: dict[str, str]):
    """
    Run a FAI hook script or class script, if it exists.
    PATH will include helper_tools_paths.
    Environment will include env.
    """

    if not script.exists():
        return

    env = {
        "target": str(chroot_dir),
        "ROOTCMD": "grml-live-chroot",
        "PATH": ":".join([str(p) for p in helper_tools_paths] + [os.environ["PATH"]]),
    } | env
    print()
    print(f"I: *** Running script {script} ***")
    proc = run_x([script], check=False, unshared=True, env=env, stdin=subprocess.DEVNULL)
    if proc.returncode != 0:
        print(f"E: Script {script} failed with exitcode {proc.returncode} - aborting.")
        raise FaiScriptFailed()
    print(f"I: Finished script {script}.")


def run_class_scripts(
    script_type: str,
    conf_dir: Path,
    chroot_dir: Path,
    class_name: str,
    helper_tools_paths: list[Path],
    env: dict[str, str],
):
    print()
    print(f'I: Running "{script_type}" for class {class_name}...')
    print()
    scripts_dir = conf_dir / script_type / class_name
    for script in sorted(scripts_dir.glob("*")):
        if script.name.endswith(".dpkg-old") or script.name.endswith(".dpkg-new"):
            print(f"W: Skipping {script} due to name suffix, please delete it")
            continue
        run_script(chroot_dir, script, helper_tools_paths, env)


def install_packages_for_classes(
    conf_dir: Path,
    chroot_dir: Path,
    classes: list[str],
    helper_tools_paths: list[Path],
    hook_env: dict,
    dynamic_state: DynamicState,
    unshared_service: UnsharedService,
):
    """Run equivalent of "instsoft" task: set debconf selections and install packages listed in package lists."""

    # debconf is not Essential. Ensure it is installed, so we can use debconf-set-selections.
    chrooted_apt_install(chroot_dir, ["debconf"])

    dpkg_architecture = chrooted_dpkg_print_architecture(chroot_dir)

    # First pass: Parse all package configs and build merged list
    class_package_lists = {}
    full_package_list = PackageList()

    for class_name in classes:
        package_list = parse_class_packages(conf_dir, class_name)
        class_package_lists[class_name] = package_list
        full_package_list.merge(package_list)

    # Show what packages will be skipped if any
    skip_packages = full_package_list.skip_list_for_arch(dpkg_architecture)
    if skip_packages:
        print(f"I: Skipping {len(skip_packages)} packages: {', '.join(sorted(skip_packages))}")

    # Second pass: Install packages and run hooks for each class
    for class_name in classes:
        chrooted_debconf_set_selections(chroot_dir, conf_dir / "debconf" / class_name)

        run_script(chroot_dir, conf_dir / "hooks" / class_name / "instsoft", helper_tools_paths, hook_env)

        # Use the previously parsed package list and apply final skip rules
        package_list = class_package_lists[class_name]
        install_args = package_list.as_apt_params(restrict_to_arch=dpkg_architecture, exclude_from=full_package_list)
        if install_args:
            print(f"I: Installing packages for class {class_name}")
            chrooted_apt_install(chroot_dir, install_args)

    print()
    print("I: Installing all packages together to detect relationship errors")
    chrooted_apt_install(chroot_dir, full_package_list.as_apt_params(restrict_to_arch=dpkg_architecture))
    unshared_service.run(
        unshared_helper.write_file_text(
            (chroot_dir / "grml-live" / "log" / "install_packages.list"),
            (
                "# List of packages installed by minifai\n"
                + ("\n".join(full_package_list.list_for_arch(dpkg_architecture)))
                + "\n"
            ),
        )
    )


def show_env(log_text: str, env):
    print(f"D: Showing {log_text} ...")
    for k, v in dict(env).items():
        print(f"D: {log_text}: {k}={v}")
    print()


def do_skiptask(dynamic_state: DynamicState, skiptask_args: list[str]) -> int:
    if not skiptask_args:
        return 0
    print(f"I: Requesting skipping of tasks: {' '.join(skiptask_args)}")
    dynamic_state.skip_tasks.update(skiptask_args)
    return 0


def helper_socket_thread(
    tempdir: Path,
    conf_dir: Path,
    chroot_dir: Path,
    classes: list[str],
    exit_event: Event,
    dynamic_state: DynamicState,
    unshared_service: UnsharedService,
):
    address_family = socket.AF_UNIX
    socket_type = socket.SOCK_STREAM
    request_queue_size = 5

    listen_socket = socket.socket(address_family, socket_type)
    listen_socket.bind(f"{tempdir}/sock")
    listen_socket.listen(request_queue_size)
    listen_socket.settimeout(1)

    while not exit_event.is_set():
        try:
            request_socket, _ = listen_socket.accept()
        except TimeoutError:
            continue

        try:
            request_socket.settimeout(5 * 60)  # 5 minutes
            orig_req = request_socket.recv(4096).decode()
            req = orig_req.split("\n")
            rc = 120
            if len(req) != 2 and req[1] != "":
                print("W: socket thread: got message:", repr(orig_req))
                print("W: socket thread: no newline, message truncated?")
            else:
                req = req[0].split(" ")
                if req[0] == "fcopy":
                    rc = unshared_service.run(
                        unshared_helper.fcopy(conf_dir, chroot_dir, " ".join(classes), " ".join(req[1:]))
                    )
                elif req[0] == "copy-media-files":
                    rc = unshared_service.run(
                        unshared_helper.copy_media_files(conf_dir, chroot_dir, " ".join(classes), " ".join(req[1:]))
                    )
                elif req[0] == "skiptask":
                    rc = do_skiptask(dynamic_state, req[1:])
                else:
                    print("W: socket thread: request not understood:", repr(orig_req))

            request_socket.send(f"{rc!s}\n".encode())
            request_socket.close()

        except Exception:
            print(f"E: {now_for_log()} helper_socket_thread caught fatal exception", flush=True)
            traceback.print_exc()
            break

    listen_socket.close()


def write_helper_tool(tools_path: Path, tool_name: str, body: str):
    with (tools_path / tool_name).open("wt") as file:
        file.write(body)
        os.fchmod(file.fileno(), 0o755)


@contextlib.contextmanager
def helper_tools(
    conf_dir: Path, chroot_dir: Path, classes: list[str], dynamic_state: DynamicState, unshared_service: UnsharedService
):
    tempdir = Path(tempfile.mkdtemp())

    write_helper_tool(
        tempdir,
        "grml-live-command",
        f"""#!/bin/sh
PN=$(basename "$0")
if [ "$PN" = "grml-live-command" ]; then
  PN="$1"
  shift
fi
echo "D: minifai $PN: $(date +%FT%T) requesting $@"
RC=$(echo $PN "$@" | socat -t3600 - UNIX-CONNECT:{tempdir}/sock,forever)
if [ -z "$RC" ]; then
  echo "E: minifai $PN: $(date +%FT%T) got no reply from server"
  exit 119
elif [ "$RC" != "0" ]; then
  echo "E: minifai $PN: server sent error code $RC"
  exit "$RC"
fi
exit 0
""",
    )

    (tempdir / "fcopy").symlink_to(tempdir / "grml-live-command")
    (tempdir / "skiptask").symlink_to(tempdir / "grml-live-command")

    write_helper_tool(
        tempdir,
        "ifclass",
        f"""#!/bin/bash
haystack=:{":".join(classes)}:
if [[ ":$haystack:" = *:$1:* ]]; then
    echo "I: ifclass $1: yes."
    exit 0
else
    echo "I: ifclass $1: no."
    exit 1
fi
""",
    )

    # Tool to provide $ROOTCMD. Will be invoked from scripts, which run in an
    # unshared context. Usually each script gets its own unshared context,
    # therefore each script gets a new mount namespace, and so on.
    # However, each script can run $ROOTCMD multiple times, so we should also
    # avoid mounting one /proc per $ROOTCMD invocation.
    write_helper_tool(
        tempdir,
        "grml-live-chroot",
        f"""#!/bin/bash
set -e
export PATH=/usr/sbin:/usr/bin:/sbin:/bin
CHROOT_DIR="{chroot_dir}"
test -d "$CHROOT_DIR"/proc/self || mount --rbind /proc "$CHROOT_DIR"/proc
for filename in null full tty ; do
  if ! test -c "$CHROOT_DIR"/dev/$filename ; then
    rm -f "$CHROOT_DIR"/dev/$filename
    touch "$CHROOT_DIR"/dev/$filename
    mount --bind /dev/$filename "$CHROOT_DIR"/dev/$filename
  fi
done
set +e
exec chroot "$CHROOT_DIR" "$@"
""",
    )

    exit_event = Event()
    thread = Thread(
        target=helper_socket_thread,
        args=(tempdir, conf_dir, chroot_dir, classes, exit_event, dynamic_state, unshared_service),
        daemon=False,
    )
    thread.start()
    try:
        yield tempdir
    finally:
        exit_event.set()
        thread.join()
        shutil.rmtree(tempdir, ignore_errors=True)


@contextlib.contextmanager
def policy_rcd(chroot_dir: Path, unshared_service: UnsharedService):
    marker = "!MINIFAI!"
    print("I: Installing temporary policy-rc.d")
    program = chroot_dir / "usr" / "sbin" / "policy-rc.d"
    contents = f"#!/bin/sh\n# Installed by grml-live minifai {marker}\nexit 101\n"
    unshared_service.run(unshared_helper.write_file_text(program, contents, executable=True))

    try:
        yield
    finally:
        try:
            if marker in program.read_text():
                print(f"I: Cleaning up {program}")
                program.unlink()
            else:
                print(f"I: Not cleaning up {program} - our marker went missing")
        except Exception:
            print(f"W: Failed cleaning up {program}")


@contextlib.contextmanager
def start_unshared_service():
    tempdir = Path(tempfile.mkdtemp())

    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as listen_socket:
        socket_path = f"{tempdir}/sock"
        listen_socket.bind(socket_path)
        listen_socket.listen(1)  # queue size

        args = unshared_helper.make_server_command(socket_path)
        subproc = popen(args, unshared=True)

        request_socket = None
        # 12 sec total timeout
        listen_socket.settimeout(1)
        for _ in range(12):
            try:
                request_socket, _ = listen_socket.accept()
            except TimeoutError:
                if subproc.poll() is not None:
                    print(f"E: unshared helper service exited with rc={subproc.returncode} before connecting")
                    raise ProgramStartFailed() from None
                continue

            break

        if request_socket is None:
            print("E: unshared helper service did not connect after timeout")
            subproc.kill()
            raise ProgramStartFailed()

        yield UnsharedService(request_socket)

    subproc.kill()


def read_envvars_for_classes(conf_dir: Path, classes: list[str]) -> dict:
    """Read environment variable files"""
    env = {}

    for class_name in classes:
        varfile = conf_dir / "env" / class_name
        if varfile.exists():
            env.update(parse_class_varfile(varfile))

    return env


def install_base(conf_dir: Path, chroot_dir: Path, classes, debian_suite: str, mirror_url: str):
    """Install Debian base system from given mirror"""
    print(f'I: Installing Debian base system for suite "{debian_suite}" using mmdebstrap')

    # Work around APT bug: http://bugs.debian.org/1092164
    included_packages = ["netbase"]

    # Allow using https:// sources. Do this unconditionally, so sources added with
    # fcopy /etc/apt just work.
    included_packages.append("ca-certificates")

    # Find keyring to use for mmdebstrap
    keyring_dir = conf_dir / "bootstrap-keyring"
    keyring_file = None
    for class_name in classes:
        if (keyring_dir / class_name).exists():
            keyring_file = keyring_dir / class_name

    if keyring_file is None:
        raise RuntimeError("No bootstrap-keyring found for any class, cannot build chroot")

    # Should use delete_on_close=False, but needs Python >= 3.12
    with tempfile.NamedTemporaryFile(delete=False, dir=chroot_dir) as keyring_tempfile:
        keyring_tempfile.write(keyring_file.read_bytes())
    os.chmod(keyring_tempfile.name, 0o644)
    run_x(["ls", "-la", keyring_tempfile.name])

    args = [
        "mmdebstrap",
        "--format=directory",
        "--variant=required",
        "--verbose",
        "--skip=check/empty",  # grml-live pre-creates directories in chroot, skip emptyness check.
        f"--keyring={keyring_tempfile.name}",
        # Delete keyring_tempfile from within mmdebstrap's userns.
        f"--chrooted-customize-hook=rm /{Path(keyring_tempfile.name).name}",
        # Mark most leaf packages as automatically installed, so autoremove could remove them if possible.
        r"--chrooted-customize-hook="
        + r"apt-mark auto \~i\ \?not\(\~prequired\)\ \?not\(\~pimportant\)\ \?not\(\~pstandard\)",
        f"--include={','.join(included_packages)}",
        debian_suite,
        chroot_dir,
        mirror_url,
    ]

    if os.environ.get("GRML_LIVE_DEBUG_APT", "") != "":
        args.insert(1, f"--aptopt={APT_DEBUG_ACQUIRE}")
        args.insert(1, "--chrooted-customize-hook=rm /etc/apt/apt.conf.d/99mmdebstrap")
    if os.environ.get("APT_PROXY", "") != "":
        args.insert(1, "--aptopt='Acquire::http { Proxy \"" + os.environ["APT_PROXY"] + '"; }')

    run_x(args)


def extract_iso(chroot_dir: Path, extract_iso_name: str):
    """Unpack squashfs from an existing ISO to use it as the chroot_dir contents."""
    print(f"I: Unpacking ISO from {extract_iso_name}")

    try:
        # Run unshared, so the unpacked chroot is owned by the correct uids.
        run_x(["osirrox", "-indev", extract_iso_name, "-extract", "live", chroot_dir])
        temp_files = sorted(chroot_dir.rglob("*"))
        print(f"D: found extracted files: {temp_files!s}")

        squashfs_files = sorted(chroot_dir.glob("*/*.squashfs"))
        if not squashfs_files:
            raise RuntimeError(f"Could not find any squashfs files in ISO {extract_iso_name}")
        if len(squashfs_files) != 1:
            raise RuntimeError(
                f"Found more than one squashfs file in ISO {extract_iso_name}: {' '.join(squashfs_files)}"
            )
        run_x(["unsquashfs", "-f", "-d", chroot_dir, squashfs_files[0]], unshared=True)
        run_x(["rm", "-rf", *temp_files], unshared=True)
    except:
        # This should be safe as chroot_dir is expected to be empty at first!
        run_x(["rm", "-rf", chroot_dir], unshared=True)
        raise


def should_skip_task(dynamic_state: DynamicState, task: str) -> bool:
    if task in dynamic_state.skip_tasks:
        print(f'I: Skipping FAI task "{task}", as dynamically requested')
        return True
    return False


def task_updatebase(chroot_dir: Path, dynamic_state: DynamicState):
    if should_skip_task(dynamic_state, "updatebase"):
        return
    run_chrooted(chroot_dir, ["apt", "-oapt::cmd::disable-script-warning=1", "--error-on=any", "update", "-q"])


def _create_chroot_dirs(chroot_dir: Path, unshared_service: UnsharedService) -> ChrootBuildDirectories:
    """Create required directories _inside_ the chroot."""

    # This code is as ugly as it looks.
    build_dir_relative = "grml-live"
    build_dir = chroot_dir / build_dir_relative

    log_dir_name = "log"
    log_dir = build_dir / log_dir_name

    media_dir_name = "media"
    media_dir = build_dir / media_dir_name

    netboot_dir_name = "netboot"
    netboot_dir = build_dir / netboot_dir_name

    sources_dir_name = "grml_sources"
    sources_dir = build_dir / sources_dir_name

    print(f"I: Creating build directory and subdirs: {build_dir}")
    unshared_service.batch(
        [
            unshared_helper.ensure_empty_dir(absolute_dir)
            for absolute_dir in [build_dir, log_dir, netboot_dir, media_dir, sources_dir]
        ]
    )

    return ChrootBuildDirectories(
        build_dir_inside=f"/{build_dir_relative}/",
        build_dir=build_dir,
        log_dir_inside=f"/{build_dir_relative}/{log_dir_name}/",
        log_dir=log_dir,
        media_dir_inside=f"/{build_dir_relative}/{media_dir_name}/",
        media_dir=media_dir,
        netboot_dir_inside=f"/{build_dir_relative}/{netboot_dir_name}/",
        netboot_dir=netboot_dir,
        sources_dir_inside=f"/{build_dir_relative}/{sources_dir_name}/",
        sources_dir=sources_dir,
    )


def install_class_helper_tools(
    conf_dir: Path,
    build_dir: Path,
    classes: list[str],
    unshared_service: UnsharedService,
) -> Path:
    """
    Copy class-config helpers into chroot.

    Later classes will overwrite earlier classes' files. This is intentional.
    """

    class_helper_tools_path = build_dir / "tools"
    unshared_service.run(unshared_helper.ensure_empty_dir(class_helper_tools_path))
    for class_name in classes:
        class_path = conf_dir / "tools" / class_name
        if not class_path.exists():
            continue
        for helper in class_path.glob("*"):
            if not helper.is_file():
                continue
            unshared_service.run(
                unshared_helper.write_file_text(
                    class_helper_tools_path / helper.name,
                    helper.read_text(),
                    executable=True,
                )
            )

    return class_helper_tools_path


def copy_directory_out(
    target_dir: Path,
    source_dir: Path,
):
    """
    Copy contents of a directory from A (source_dir) to B (target_dir).
    Intended to be used when copying from unshared context to the "outside".
    Does not preserve file modes, ownership, etc.
    """
    target_dir.mkdir(exist_ok=True)
    run_x(
        [
            "/bin/cp",
            "--no-preserve=all",
            "--preserve=timestamp",
            "-r",
            str(source_dir) + "/.",
            str(target_dir) + "/",
        ]
    )


def install_extra_chroot_files(
    chroot_dir: Path,
    chroot_install: str,
    unshared_service: UnsharedService,
):
    if not chroot_install:
        return
    chroot_install_source_dir = Path(chroot_install)
    if not chroot_install_source_dir.exists() or not chroot_install_source_dir.is_dir():
        print("W: Configuration variable $CHROOT_INSTALL is set but not a directory; ignoring")
        return

    print(f"I: Copying local files to chroot from {chroot_install_source_dir!s}")
    unshared_service.run(
        unshared_helper.run_program(
            [
                "rsync",
                "-avz",
                "--inplace",
                str(chroot_install_source_dir) + "/",
                str(chroot_dir) + "/",
            ]
        )
    )


def _build_mksquashfs_options(conf_dir: Path) -> list[str]:
    squashfs_excludes_file = conf_dir / "grml" / "squashfs-excludes"
    options = [
        "-noappend",
        # use block size 1m as this gives good result with regards to time + compression
        "-b",
        "1m",
        "-comp",
        "xz",
        # Ignore all extended attributes. This avoids:
        # 1) leaking containerization supplied selinux attributes into the squashfs,
        # 2) prevents unpacking errors in a later build-only step in containers not supporting xattrs.
        "-no-xattrs",
        # Static file exclusion list.
        "-wildcards",
        "-ef",
        str(squashfs_excludes_file),
        "-one-file-system",
    ]
    return options


def mksquashfs(
    conf_dir: Path,
    grml_cd_dir: Path,
    chroot_dir: Path,
    grml_name: str,
    unshared_service: UnsharedService,
):
    live_dir = grml_cd_dir / "live"
    squashfs_dir = live_dir / grml_name
    squashfs_file = squashfs_dir / f"{grml_name}.squashfs"

    mksquashfs_binary = os.environ["MKSQUASHFS_BINARY"]
    options = _build_mksquashfs_options(conf_dir)
    args = [mksquashfs_binary, str(chroot_dir) + "/", squashfs_file, *options]

    # We must run mksquashfs inside the userns so it sees the correct ownership info,
    # but we want the resulting file to be owned by the user outside of the userns.
    unshared_service.batch(
        [
            unshared_helper.ensure_dir(live_dir),
            unshared_helper.ensure_dir(squashfs_dir),
            unshared_helper.run_program(args),
            unshared_helper.chown(squashfs_file, str(UNSHARE_UID), str(UNSHARE_GID)),
            unshared_helper.chown(squashfs_dir, str(UNSHARE_UID), str(UNSHARE_GID)),
            unshared_helper.chown(live_dir, str(UNSHARE_UID), str(UNSHARE_GID)),
        ]
    )


def create_on_media_md5sums(grml_cd_dir: Path, grml_name: str):
    print("I: preparing md5sums file")

    grml_dir = grml_cd_dir / "GRML"
    grml_dir.mkdir(exist_ok=True)  # media-scripts may have created it
    named_grml_dir = grml_dir / grml_name
    named_grml_dir.mkdir(exist_ok=True)  # media-scripts may have created it
    md5sums_file = named_grml_dir / "md5sums"

    filenames = [
        filename.relative_to(grml_cd_dir) for filename in sorted(grml_cd_dir.rglob("*")) if not filename.is_dir()
    ]

    with md5sums_file.open("wb") as output:
        run_x(["/bin/md5sum", *filenames], cwd=grml_cd_dir, stdout=output)

    run_x(["/bin/ls", "-la", md5sums_file])


def create_netboot_package(
    output_dir: Path,
    chroot_netboot_dir: Path,
    iso_name: str,
):
    """
    Create netboot tar package.
    Filename is derived from the iso_name, and its toplevel directory matches the tar filename.
    """
    output_basename = iso_name.rpartition(".iso")[0] + "-netboot"
    output_netboot_dir = output_dir / "netboot"
    output_netboot_dir.mkdir()
    output_name = output_netboot_dir / (output_basename + ".tar")
    print(f"I: building netboot tar: {output_name.name}")

    run_x(
        [
            "tar",
            "-C",
            chroot_netboot_dir,
            "-cf",
            output_name,
            "--owner=0",
            "--group=0",
            "--transform",
            r"s|^./|" + output_basename + "/|",
            ".",
        ]
    )

    checksum_filename = Path(str(output_name) + ".sha256")
    with checksum_filename.open("wt") as checksum_file_handle:
        run_x(["sha256sum", output_name.name], cwd=output_name.parent, stdout=checksum_file_handle)


def create_sources_package(
    output_dir: Path,
    chroot_sources_dir: Path,
    iso_name: str,
):
    """
    Create sources tar package.
    Filename is derived from the iso_name, and its toplevel directory matches the tar filename.
    """
    output_basename = iso_name.rpartition(".iso")[0] + "-sources"
    output_name = output_dir / (output_basename + ".tar")
    print(f"I: building sources tar: {output_name.name}")

    run_x(
        [
            "tar",
            "-C",
            chroot_sources_dir,
            "-cf",
            output_name,
            "--owner=0",
            "--group=0",
            "--transform",
            r"s|^./|" + output_basename + "/|",
            ".",
        ]
    )

    checksum_filename = Path(str(output_name) + ".sha256")
    with checksum_filename.open("wt") as checksum_file_handle:
        run_x(["sha256sum", output_name.name], cwd=output_name.parent, stdout=checksum_file_handle)


def _build_buildinfo_data(
    conf_dir: Path,
    output_dir: Path,
    fai_action: str,
    classes: list[str],
    grml_live_config: dict[str, str],
):
    # TODO: collect the data in each step creating the data, instead of doing it all here.
    proc = popen(["dpkg", "--print-architecture"], stdout=subprocess.PIPE, text=True)
    stdout_data, _ = proc.communicate()
    host_arch = stdout_data.strip()

    proc = popen(["xorriso", "--version"], stdout=subprocess.PIPE, text=True)
    stdout_data, _ = proc.communicate()
    mkisofs_version = stdout_data.splitlines()[0].strip()

    proc = popen(["mksquashfs", "-version"], stdout=subprocess.PIPE, text=True)
    stdout_data, _ = proc.communicate()
    mksquashfs_version = stdout_data.splitlines()[0].strip()

    buildinfo = {
        "build_date": grml_live_config["DATE"],
        "fai_action": fai_action,
        "chroot_install": os.environ["CHROOT_INSTALL"],
        "classes": ",".join(classes),
        "default_bootoptions": grml_live_config["DEFAULT_BOOTOPTIONS"],
        "distri_info": grml_live_config["DISTRI_INFO"],
        "distri_name": grml_live_config["DISTRI_NAME"],
        "extract_iso_name": os.environ["EXTRACT_ISO_NAME"],
        "fai_cmdline": " ".join(sys.argv[1:]),
        "fai_version": "minifai",
        "grml_architecture": os.environ["ARCH"],
        "grml_bootid": grml_live_config["BOOTID"],
        "grml_debian_version": os.environ["SUITE"],
        "grml_iso_name": os.environ["ISO_NAME"],
        "grml_live_cmdline": os.environ["CMDLINE"],
        "grml_live_config_file": os.environ["LIVE_CONF"],
        "grml_live_version": os.environ["GRML_LIVE_VERSION"],
        "grml_local_config": os.environ["LOCAL_CONFIG"],
        "grml_name": grml_live_config["GRML_NAME"],
        "grml_short_name": grml_live_config["SHORT_NAME"],
        "grml_username": grml_live_config["USERNAME"],
        "grml_version": grml_live_config["VERSION"],
        "host_architecture": host_arch,
        "mkisofs_cmdline": " ".join(
            _build_xorriso_options(
                output_dir / "grml_isos",
                output_dir / "grml_cd",
                grml_live_config["GRML_NAME"],
                grml_live_config["VERSION"],
                os.environ["ISO_NAME"],
                os.environ["ARCH"],
            )
        ),
        "mkisofs_version": mkisofs_version,
        "mksquashfs_cmdline": " ".join(_build_mksquashfs_options(conf_dir)),
        "mksquashfs_version": mksquashfs_version,
        "release_info": grml_live_config["RELEASE_INFO"],
        "release_name": grml_live_config["RELEASENAME"],
        "secure_boot": os.environ["SECURE_BOOT"],
        "timestamp": os.environ["SOURCE_DATE_EPOCH"],
        "wayback_date": os.environ["WAYBACK_DATE"],
    }
    buildinfo = {key: value.replace(str(output_dir), "<output_dir>") for key, value in buildinfo.items()}
    return buildinfo


def write_buildinfo_json(
    conf_dir: Path,
    output_dir: Path,
    grml_cd_dir: Path,
    fai_action: str,
    classes: list[str],
    grml_live_config: dict[str, str],
):
    buildinfo = _build_buildinfo_data(
        conf_dir,
        output_dir,
        fai_action,
        classes,
        grml_live_config,
    )
    print(f"I: buildinfo data:\n{buildinfo!s}")
    (grml_cd_dir / "conf").mkdir(exist_ok=True)
    (grml_cd_dir / "conf" / "buildinfo.json").write_text(json.dumps(buildinfo))


def _build_xorriso_options(
    iso_dir: Path, grml_cd_dir: Path, grml_name: str, version: str, iso_name: str, arch: str
) -> list[str]:

    efi_args = ["-eltorito-alt-boot", "-e", "boot/efi.img", "-no-emul-boot", "-isohybrid-gpt-basdat"]

    if arch == "arm64":
        # No BIOS boot on arm64, only UEFI
        boot_args = []
    elif arch == "amd64":
        # TODO: avoid the arch check and use the file existence instead
        # Use GRUB for BIOS boot via El Torito
        boot_args = [
            "-b",
            "boot/grub/i386-pc/eltorito.img",
            "-no-emul-boot",
            "-boot-load-size",
            "4",
            "-boot-info-table",
            "--grub2-boot-info",
            "--grub2-mbr",
            str(grml_cd_dir / "boot" / "grub" / "i386-pc" / "boot_hybrid.img"),
        ]
    else:
        raise NotImplementedError()

    return [
        "xorriso",
        "-as",
        "mkisofs",
        "-V",
        f"{grml_name} {version}",
        "-publisher",
        "grml-live | grml.org",
        "-l",
        "-r",
        "-J",
        *boot_args,
        *efi_args,
        "-o",
        str(iso_dir / iso_name),
        str(grml_cd_dir) + "/",
    ]


def create_media(
    output_dir: Path,
    grml_cd_dir: Path,
    grml_name: str,
    version: str,
    iso_name: str,
    arch: str,
):
    iso_dir = output_dir / "grml_isos"
    iso_dir.mkdir()
    print("I: Generating ISO file ...")
    run_x(_build_xorriso_options(iso_dir, grml_cd_dir, grml_name, version, iso_name, arch))

    checksum_filename = Path(str(iso_dir / iso_name) + ".sha256")
    with checksum_filename.open("wt") as checksum_file_handle:
        run_x(["sha256sum", iso_name], cwd=iso_dir, stdout=checksum_file_handle)


def _run_tasks(
    conf_dir: Path,
    output_dir: Path,
    chroot_dir: Path,
    classes: list[str],
    grml_live_config: dict[str, str],
    fai_action: str,
    skip_tasks: list[str],
    unshared_service: UnsharedService,
) -> int:
    dynamic_state = DynamicState()
    chroot_directories = _create_chroot_dirs(chroot_dir, unshared_service)
    grml_cd_dir = output_dir / "grml_cd"
    grml_cd_dir.mkdir()
    grml_logs_dir = output_dir / "grml_logs"
    grml_logs_dir.mkdir(exist_ok=True)

    # Create a file in log_dir, so grml-live does not complain.
    unshared_service.run(
        unshared_helper.write_file_text(
            (chroot_directories.log_dir / "minifai"),
            ("This chroot was created by grml-live minifai. Not all FAI features are supported.\n"),
        )
    )

    # duplicate grml_live_config into the chroot, so chrooted scripts can use it.
    grml_live_config_chroot = chroot_directories.build_dir / "config"
    unshared_service.run(
        unshared_helper.write_file_text(
            grml_live_config_chroot, "\n".join(f"{k}={shlex.quote(v)}" for k, v in grml_live_config.items())
        )
    )

    arch = os.environ["ARCH"]
    print(f"I: ARCH: {arch!r}")
    chroot_install = os.environ["CHROOT_INSTALL"]
    print(f"I: CHROOT_INSTALL: {chroot_install!r}")
    grml_name = os.environ["GRML_NAME"]
    print(f"I: GRML_NAME: {grml_name!r}")
    iso_name = os.environ["ISO_NAME"]
    print(f"I: ISO_NAME: {iso_name!r}")
    version = os.environ["VERSION"]
    print(f"I: VERSION: {version!r}")

    do_skiptask(dynamic_state, skip_tasks)

    env = {
        "GRML_LIVE_CONFIG": str(grml_live_config_chroot),
        "GRML_LIVE_BUILDDIR": chroot_directories.build_dir_inside,
        "GRML_LIVE_MEDIADIR": chroot_directories.media_dir_inside,
        "GRML_LIVE_NETBOOTDIR": chroot_directories.netboot_dir_inside,
        "GRML_LIVE_SOURCESDIR": chroot_directories.sources_dir_inside,
        "LOGDIR": str(chroot_directories.log_dir),
    } | read_envvars_for_classes(conf_dir, classes)
    show_env("Merged class variables", env)

    # Setup /proc, /sys inside chroot_dir, so future chroot calls will have these mounts.
    unshared_service.run(unshared_helper.bindmount_proc_sys_into(chroot_dir))

    try:
        with helper_tools(conf_dir, chroot_dir, classes, dynamic_state, unshared_service) as helper_tools_path:
            class_helper_tools_path = install_class_helper_tools(
                conf_dir, chroot_directories.build_dir, classes, unshared_service
            )

            helper_tools_paths = [helper_tools_path, class_helper_tools_path]

            hook_env = env | {"FAI_ACTION": fai_action}
            for class_name in classes:
                run_script(chroot_dir, conf_dir / "hooks" / class_name / "updatebase", helper_tools_paths, hook_env)

            with policy_rcd(chroot_dir, unshared_service):
                task_updatebase(chroot_dir, dynamic_state)

                if not should_skip_task(dynamic_state, "instsoft"):
                    install_packages_for_classes(
                        conf_dir, chroot_dir, classes, helper_tools_paths, hook_env, dynamic_state, unshared_service
                    )

            if not should_skip_task(dynamic_state, "configure"):
                for class_name in classes:
                    run_class_scripts("scripts", conf_dir, chroot_dir, class_name, helper_tools_paths, env)

                install_extra_chroot_files(chroot_dir, chroot_install, unshared_service)

            if not should_skip_task(dynamic_state, "squashfs"):
                # mksquashfs is the last thing that should need the userns.
                mksquashfs(conf_dir, grml_cd_dir, chroot_dir, grml_name, unshared_service)

            if not should_skip_task(dynamic_state, "build"):
                for class_name in classes:
                    run_class_scripts("media-scripts", conf_dir, chroot_dir, class_name, helper_tools_paths, env)

                print("I: installing media files from chroot build")
                run_x(
                    [
                        "/bin/cp",
                        "--no-preserve=all",
                        "--preserve=timestamp",
                        "-rv",
                        str(chroot_directories.media_dir) + "/.",
                        grml_cd_dir,
                    ],
                )

                write_buildinfo_json(conf_dir, output_dir, grml_cd_dir, fai_action, classes, grml_live_config)

                create_netboot_package(
                    output_dir,
                    chroot_directories.netboot_dir,
                    iso_name,
                )
                if "SOURCES" in classes:
                    create_sources_package(
                        output_dir,
                        chroot_directories.sources_dir,
                        iso_name,
                    )

                # After this, no new files should appear.
                create_on_media_md5sums(grml_cd_dir, grml_name)

                # After this, no files should be touched any more.
                source_date_epoch = os.getenv("SOURCE_DATE_EPOCH")
                if source_date_epoch:
                    print(f"I: Clamping mtimes to {source_date_epoch}")
                    unshared_service.run(unshared_helper.clamp_to_source_date(grml_cd_dir, source_date_epoch))

                create_media(output_dir, grml_cd_dir, grml_name, version, iso_name, arch)

    finally:
        copy_directory_out(grml_logs_dir / "fai", chroot_directories.log_dir)

    return 0


def create_argparser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    # path to fai classes, scripts, ...
    parser.add_argument("config", type=Path)
    parser.add_argument("classes")
    parser.add_argument(
        "action",
        choices=[value.value for value in FaiAction.__members__.values()],
        metavar="ACTION",
        help="FAI action to execute (choices: %(choices)s)",
    )
    parser.add_argument("output_dir", type=Path)
    parser.add_argument("grml_live_config", type=Path)
    parser.add_argument("debian_suite", type=str)
    parser.add_argument("mirror_url", type=str)
    return parser


def _main(program_name: str, argv: list[str]) -> int:
    print(f"I: {program_name} started with {argv=}")
    args = create_argparser().parse_args(argv[1:])
    print(f"I: {program_name} parsed args: {args}")
    classes = args.classes.split(",")
    print(f"I: Using classes: {classes}")
    conf_dir = args.config.absolute()
    print(f"I: Using conf_dir: {conf_dir}")
    output_dir: Path = args.output_dir.absolute()
    print(f"I: Using output_dir: {args.output_dir}")

    if not conf_dir.exists():
        raise ValueError(f"Config directory {conf_dir} does not exist")
    if not output_dir.exists():
        raise ValueError(f"Output directory {output_dir} does not exist")

    chroot_dir = output_dir / "grml_chroot"

    grml_live_config = _parse_bash_set(args.grml_live_config.read_text())
    show_env("configdump", grml_live_config)

    rc = 0

    try:
        with start_unshared_service() as unshared_service:
            unshared_service.run(unshared_helper.hello_world())
            skiptasks = []

            extract_iso_name = os.environ["EXTRACT_ISO_NAME"]
            if extract_iso_name:
                if args.action == FaiAction.DIRINSTALL:
                    raise ValueError("Building a new chroot is incompatible with extracting an existing ISO")
                extract_iso(chroot_dir, extract_iso_name)
            else:
                try:
                    chroot_dir.mkdir()
                except FileExistsError:
                    if args.action == FaiAction.DIRINSTALL:
                        raise ValueError(f"chroot directory {chroot_dir} unexpectedly already exists") from None

            if args.action == FaiAction.DIRINSTALL:
                install_base(conf_dir, chroot_dir, classes, args.debian_suite, args.mirror_url)
            elif args.action == FaiAction.SOFTUPDATE:
                pass
            elif args.action == FaiAction.RECONFIGURE:
                skiptasks = ["updatebase", "instsoft"]
            elif args.action == FaiAction.REBUILD:
                skiptasks = ["updatebase", "instsoft", "configure"]
            elif args.action == FaiAction.REBUILD_MEDIA:
                skiptasks = ["updatebase", "instsoft", "configure", "squashfs"]
            else:
                print(f"E: minifai: Unknown fai action: {args.action!r}")
                rc = 1

            if not rc:
                rc = _run_tasks(
                    conf_dir,
                    output_dir,
                    chroot_dir,
                    classes,
                    grml_live_config,
                    args.action,
                    skiptasks,
                    unshared_service,
                )
    except (ClassFileParsingFailed, FaiScriptFailed, ProgramStartFailed):
        # assume exception site already printed relevant info
        rc = 3
    except Exception:
        print(f"E: {now_for_log()} minifai main caught fatal exception")
        traceback.print_exc()
        rc = 2

    print(f"I: minifai exiting with exit code {rc}")
    return rc


def main() -> int:
    return _main(sys.argv[0], sys.argv)


if __name__ == "__main__":
    sys.exit(main())
