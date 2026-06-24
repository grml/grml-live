# This is a spaghetti-code minimal reimplementation of the FAI API surface grml-live needs,
# for building Grml Live Linux. If you have additional API surface needs, please contribute.
# Please beware that this implementation is an interim step, and we may or may not continue
# with the FAI API.
#
import argparse
import contextlib
import datetime
import os
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


class FaiScriptFailed(Exception):
    pass


class FaiAction(StrEnum):
    BOOTSTRAP = "bootstrap"
    DIRINSTALL = "dirinstall"
    SOFTUPDATE = "softupdate"
    RECONFIGURE = "reconfigure"
    REBUILD = "rebuild"


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
            "--map-user=65536",
            "--map-group=65536",
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

        listen_socket.settimeout(120)
        try:
            request_socket, _ = listen_socket.accept()
        except TimeoutError:
            print("E: unshared helper service did not connect")
            subproc.kill()
            raise

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
        r"--chrooted-customize-hook=apt-mark auto \~i \?not\(\~prequired\) \?not\(\~pimportant\) \?not\(\~pstandard\)",
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


def cleanup_dyld_cache(
    chroot_dir: Path,
    unshared_service: UnsharedService,
):
    # The dynamic linker auxiliary cache is not reproducible and is always
    # invalid at boot (see Debian bug #845034). Unfortunately this must be
    # done from outside the chroot, as *any* program invocation inside will
    # recreate the file.
    print("I: Cleaning ldconfig cache")
    unshared_service.batch(
        [
            unshared_helper.unlink(chroot_dir / "var/cache/ldconfig/aux-cache"),
            unshared_helper.rmdir(chroot_dir / "var/cache/ldconfig"),
        ]
    )


def _run_tasks(
    conf_dir: Path,
    output_dir: Path,
    chroot_dir: Path,
    classes: list[str],
    grml_live_config: Path,
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
    unshared_service.run(unshared_helper.write_file_text(grml_live_config_chroot, grml_live_config.read_text()))

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

            if not should_skip_task(dynamic_state, "build"):
                for class_name in classes:
                    run_class_scripts("media-scripts", conf_dir, chroot_dir, class_name, helper_tools_paths, env)

                epoch = os.getenv("SOURCE_DATE_EPOCH")
                if epoch:
                    print(f"I: Clamping mtimes to {epoch}")
                    unshared_service.run(unshared_helper.clamp_to_source_date(chroot_dir, epoch))

                cleanup_dyld_cache(chroot_dir, unshared_service)

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
    chroot_dir.mkdir(
        exist_ok=True  # for now, as grml_live has to mount the mirror
    )

    with start_unshared_service() as unshared_service:
        unshared_service.run(unshared_helper.hello_world())

        skiptasks = []
        rc = 0

        try:
            if args.action == FaiAction.BOOTSTRAP:
                install_base(conf_dir, chroot_dir, classes, args.debian_suite, args.mirror_url)
                skiptasks = ["configure"]
            elif args.action == FaiAction.DIRINSTALL:
                install_base(conf_dir, chroot_dir, classes, args.debian_suite, args.mirror_url)
            elif args.action == FaiAction.SOFTUPDATE:
                pass
            elif args.action == FaiAction.RECONFIGURE:
                skiptasks = ["updatebase", "instsoft"]
            elif args.action == FaiAction.REBUILD:
                skiptasks = ["updatebase", "instsoft", "configure"]
            else:
                print(f"E: minifai: Unknown fai action: {args.action!r}")
                rc = 1

            if not rc:
                rc = _run_tasks(
                    conf_dir,
                    output_dir,
                    chroot_dir,
                    classes,
                    args.grml_live_config,
                    args.action,
                    skiptasks,
                    unshared_service,
                )
        except (ClassFileParsingFailed, FaiScriptFailed):
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
