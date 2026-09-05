# This is a spaghetti-code minimal reimplementation of the FAI API surface grml-live needs,
# for building Grml Live Linux. If you have additional API surface needs, please contribute.
# Please be aware that we will gradually move away from FAI compatibility.
#
import contextlib
import datetime
import json
import os
import shlex
import socket
import subprocess
import tempfile
import traceback
from dataclasses import dataclass
from pathlib import Path
from threading import Event, Thread

from . import build_facts, file_ops, logkit, unshared_helper
from .classes import ClassFileParsingFailed, parse_class_varfile
from .packages import PackageList, parse_class_packages

APT_DEBUG_ACQUIRE = "Debug::Acquire::http=true"

# UID/GID *inside* the userns that is mapped to the executing user.
UNSHARE_UID = 65536
UNSHARE_GID = 65536


class ClassScriptFailed(Exception):
    pass


class ProgramStartFailed(Exception):
    pass


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
            raise RuntimeError(f"unshared operation failed with rc={res}, op: {op}")
        return res

    def batch(self, ops: list[dict], check=True) -> int:
        res = unshared_helper.send_ops_to_server(self.request_socket, ops)
        if check and res:
            raise RuntimeError(f"unshared operations failed with rc={res}, ops: {ops}")
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
        "-oDpkg::Use-Pty=0",
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
    logkit.info(f"Loading debconf selections from {selections_file}")
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
    logkit.info(f"*** Running script {script} ***")
    proc = run_x([script], check=False, unshared=True, env=env, stdin=subprocess.DEVNULL)
    if proc.returncode != 0:
        logkit.error(f"Script {script} failed with exitcode {proc.returncode} - aborting.")
        raise ClassScriptFailed()
    logkit.info(f"Finished script {script}.")


def run_class_scripts(
    script_type: str,
    conf_dir: Path,
    chroot_dir: Path,
    class_name: str,
    helper_tools_paths: list[Path],
    env: dict[str, str],
):
    scripts_dir = conf_dir / script_type / class_name
    scripts = sorted(scripts_dir.glob("*"))
    if not scripts:
        logkit.info(f'No "{script_type}" to run for class {class_name}.')
        return

    logkit.info(f'Running "{script_type}" for class {class_name}...')
    for script in scripts:
        if script.name.endswith(".dpkg-old") or script.name.endswith(".dpkg-new"):
            logkit.warn(f"Skipping {script} due to name suffix, please delete it")
            continue
        run_script(chroot_dir, script, helper_tools_paths, env)


def install_packages_for_classes(
    conf_dir: Path,
    chroot_dir: Path,
    classes: list[str],
    helper_tools_paths: list[Path],
    hook_env: dict,
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
        logkit.info(f"Skipping {len(skip_packages)} packages: {', '.join(sorted(skip_packages))}")

    # Second pass: Install packages and run hooks for each class
    for class_name in classes:
        chrooted_debconf_set_selections(chroot_dir, conf_dir / "debconf" / class_name)

        run_script(chroot_dir, conf_dir / "hooks" / class_name / "instsoft", helper_tools_paths, hook_env)

        # Use the previously parsed package list and apply final skip rules
        package_list = class_package_lists[class_name]
        install_args = package_list.as_apt_params(restrict_to_arch=dpkg_architecture, exclude_from=full_package_list)
        if install_args:
            logkit.info(f"Installing packages for class {class_name}")
            chrooted_apt_install(chroot_dir, install_args)

    print()
    logkit.info("Installing all packages together to detect relationship errors")
    chrooted_apt_install(chroot_dir, full_package_list.as_apt_params(restrict_to_arch=dpkg_architecture))
    unshared_service.run(
        unshared_helper.write_file_text(
            (chroot_dir / "grml-live" / "log" / "install_packages.list"),
            (
                "# List of packages installed by grml-live\n"
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


def helper_socket_thread(
    socket_path: Path,
    conf_dir: Path,
    chroot_dir: Path,
    classes: list[str],
    exit_event: Event,
    unshared_service: UnsharedService,
):
    address_family = socket.AF_UNIX
    socket_type = socket.SOCK_STREAM | socket.SOCK_CLOEXEC
    request_queue_size = 5

    listen_socket = socket.socket(address_family, socket_type)
    listen_socket.bind(socket_path)
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
                logkit.warn("socket thread: got message:", repr(orig_req))
                logkit.warn("socket thread: no newline, message truncated?")
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
                else:
                    logkit.warn("socket thread: request not understood:", repr(orig_req))

            request_socket.sendall(f"{rc!s}\n".encode())
            request_socket.close()

        except Exception:
            logkit.error(f"{now_for_log()} helper_socket_thread caught fatal exception")
            traceback.print_exc()
            break

    listen_socket.close()


def write_helper_tool(tools_path: Path, tool_name: str, body: str):
    with (tools_path / tool_name).open("wt") as file:
        file.write(body)
        os.fchmod(file.fileno(), 0o755)


@contextlib.contextmanager
def helper_tools(conf_dir: Path, chroot_dir: Path, classes: list[str], unshared_service: UnsharedService):
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tempdir_name:
        tempdir = Path(tempdir_name)
        socket_path = f"{tempdir}/glapisock"

        write_helper_tool(
            tempdir,
            "grml-live-command",
            f"""#!/bin/sh
PN=$(basename "$0")
if [ "$PN" = "grml-live-command" ]; then
  PN="$1"
  shift
fi
echo "D: grml-live $PN: $(date +%FT%T) requesting $@"
RC=$(echo $PN "$@" | socat -t3600 - UNIX-CONNECT:{socket_path},forever)
if [ -z "$RC" ]; then
  echo "E: grml-live $PN: $(date +%FT%T) got no reply from server"
  exit 119
elif [ "$RC" != "0" ]; then
  echo "E: grml-live $PN: server sent error code $RC"
  exit "$RC"
fi
exit 0
""",
        )

        (tempdir / "fcopy").symlink_to(tempdir / "grml-live-command")

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
            args=(socket_path, conf_dir, chroot_dir, classes, exit_event, unshared_service),
            daemon=False,
        )
        thread.start()
        try:
            yield tempdir
        finally:
            exit_event.set()
            thread.join()


@contextlib.contextmanager
def policy_rcd(chroot_dir: Path, unshared_service: UnsharedService):
    marker = "!GRML-LIVE!"
    logkit.info("Installing temporary policy-rc.d")
    program = chroot_dir / "usr" / "sbin" / "policy-rc.d"
    contents = f"#!/bin/sh\n# Installed by grml-live {marker}\nexit 101\n"
    unshared_service.run(unshared_helper.write_file_text(program, contents, executable=True))

    try:
        yield
    finally:
        try:
            have_marker = not bool(
                unshared_service.run(unshared_helper.have_text_in_file(program, marker), check=False)
            )

            if have_marker:
                logkit.info(f" Cleaning up {program}")
                unshared_service.run(unshared_helper.unlink(program))
            else:
                logkit.info(f"Not cleaning up {program} - our marker went missing")
        except Exception as except_inst:
            logkit.warn(f"Failed cleaning up {program}: {except_inst}")


@contextlib.contextmanager
def start_unshared_service():
    with (
        tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tempdir,
        socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as listen_socket,
    ):
        socket_path = str(Path(tempdir) / "glusnhsock")
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
                    logkit.error(f"unshared helper service exited with rc={subproc.returncode} before connecting")
                    raise ProgramStartFailed() from None
                continue

            break

        if request_socket is None:
            logkit.error("unshared helper service did not connect after timeout")
            subproc.kill()
            raise ProgramStartFailed()

        try:
            yield UnsharedService(request_socket)
        finally:
            subproc.kill()


def read_envvars_for_classes(conf_dir: Path, classes: list[str]) -> dict[str, str]:
    """Read environment variable files"""
    env = {}

    for class_name in classes:
        varfile = conf_dir / "env" / class_name
        if varfile.exists():
            env.update(parse_class_varfile(varfile))

    return env


def install_base(conf_dir: Path, chroot_dir: Path, classes: list[str], debian_suite: str, mirror_url: str):
    """Install Debian base system from given mirror"""
    logkit.info(f'Installing Debian base system for suite "{debian_suite}" using mmdebstrap ...')

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
        args.insert(1, '--aptopt=Acquire::http { Proxy "' + os.environ["APT_PROXY"] + '"; }')

    run_x(args)


def extract_iso(config: build_facts.BuildConfiguration):
    """Unpack squashfs from an existing ISO to use it as the chroot_dir contents."""
    logkit.info(f"Unpacking ISO from {config.source_image}")
    assert config.extract_programs is not None

    try:
        # Run unshared, so the unpacked chroot is owned by the correct uids.
        run_x(
            [
                config.extract_programs.osirrox,
                "-indev",
                config.source_image,
                "-extract",
                "live",
                config.grml_chroot_dir,
            ]
        )
        temp_files = sorted(config.grml_chroot_dir.rglob("*"))
        print(f"D: found extracted files: {temp_files!s}")

        squashfs_files = sorted(config.grml_chroot_dir.glob("*/*.squashfs"))
        if not squashfs_files:
            raise RuntimeError(f"Could not find any squashfs files in ISO {config.source_image}")
        if len(squashfs_files) != 1:
            found_files = " ".join([str(filename) for filename in squashfs_files])
            raise RuntimeError(f"Found more than one squashfs file in ISO {config.source_image}: {found_files}")
        run_x(
            [config.extract_programs.unsquashfs, "-f", "-d", config.grml_chroot_dir, squashfs_files[0]], unshared=True
        )
        run_x(["rm", "-rf", *temp_files], unshared=True)
    except:
        # This should be safe as chroot_dir is expected to be empty at first!
        run_x(["rm", "-rf", config.grml_chroot_dir], unshared=True)
        raise


def should_skip_task(skip_tasks: list[str], task: str) -> bool:
    if task in skip_tasks:
        logkit.info(f'Skipping grml-live task "{task}", as requested')
        return True
    return False


def task_updatebase(chroot_dir: Path):
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

    logkit.info(f"Creating build directory and subdirs: {build_dir}")
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
    chroot_install_source_dir: Path,
    unshared_service: UnsharedService,
):
    # If chroot_install_source_dir is set, then grml_live.main checked its usable.
    logkit.info(f"Copying local files to chroot from {chroot_install_source_dir!s} ...")
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


def _build_mksquashfs_cmdline(config: build_facts.BuildConfiguration) -> list[str]:
    squashfs_excludes_file = config.config_dir / "grml" / "squashfs-excludes"
    cmdline = [
        config.builder_programs.mksquashfs,
        str(config.grml_chroot_dir) + "/",
        config.grml_cd_squashfs_name,
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
        squashfs_excludes_file,
        "-one-file-system",
    ]
    return [str(value) for value in cmdline]


def mksquashfs(
    config: build_facts.BuildConfiguration,
    unshared_service: UnsharedService,
):
    mksquashfs_cmdline = _build_mksquashfs_cmdline(config)
    filesystem_module_file = config.grml_cd_squashfs_dir / "filesystem.module"

    logkit.info(f"Building squashfs {config.grml_cd_squashfs_name} ...")
    # We must run mksquashfs inside the userns so it sees the correct ownership info,
    # but we want the resulting file to be owned by the user outside of the userns.
    unshared_service.batch(
        [
            unshared_helper.ensure_dir(config.grml_cd_live_dir),
            unshared_helper.ensure_dir(config.grml_cd_squashfs_dir),
            unshared_helper.run_program(mksquashfs_cmdline),
            unshared_helper.write_file_text(filesystem_module_file, config.grml_cd_squashfs_name.name),
            unshared_helper.chown(filesystem_module_file, str(UNSHARE_UID), str(UNSHARE_GID)),
            unshared_helper.chown(config.grml_cd_squashfs_name, str(UNSHARE_UID), str(UNSHARE_GID)),
            unshared_helper.chown(config.grml_cd_squashfs_dir, str(UNSHARE_UID), str(UNSHARE_GID)),
            unshared_helper.chown(config.grml_cd_live_dir, str(UNSHARE_UID), str(UNSHARE_GID)),
        ]
    )


def create_on_media_md5sums(grml_cd_dir: Path, grml_name: str):
    grml_dir = grml_cd_dir / "GRML"
    grml_dir.mkdir(exist_ok=True)  # media-scripts may have created it
    named_grml_dir = grml_dir / grml_name
    named_grml_dir.mkdir(exist_ok=True)  # media-scripts may have created it
    md5sums_file = named_grml_dir / "md5sums"

    filenames = [
        filename.relative_to(grml_cd_dir) for filename in sorted(grml_cd_dir.rglob("*")) if not filename.is_dir()
    ]

    logkit.info(f"Building testcd md5sums {md5sums_file} ...")
    with md5sums_file.open("wb") as output:
        run_x(["/bin/md5sum", *filenames], cwd=grml_cd_dir, stdout=output)


def create_sha256_checksum_file(file_to_checksum: Path):
    checksum_filename = Path(str(file_to_checksum) + ".sha256")
    with checksum_filename.open("wt") as checksum_file_handle:
        run_x(["sha256sum", file_to_checksum.name], cwd=file_to_checksum.parent, stdout=checksum_file_handle)


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
    output_netboot_dir.mkdir(exist_ok=True)  # some workflows accept that this already exists
    output_name = output_netboot_dir / (output_basename + ".tar")

    logkit.info(f"Building netboot package {output_name.name} ...")
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
    create_sha256_checksum_file(output_name)


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

    logkit.info(f"Building sources tarball {output_name.name} ...")
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
    create_sha256_checksum_file(output_name)


def _build_buildinfo_data(
    config: build_facts.BuildConfiguration,
) -> dict[str, str | None]:
    # TODO: collect the data in each step creating the data, instead of doing it all here.
    proc = popen([config.builder_programs.xorriso, "--version"], stdout=subprocess.PIPE, text=True)
    stdout_data, _ = proc.communicate()
    xorriso_version = stdout_data.splitlines()[0].strip()

    proc = popen([config.builder_programs.mksquashfs, "-version"], stdout=subprocess.PIPE, text=True)
    stdout_data, _ = proc.communicate()
    mksquashfs_version = stdout_data.splitlines()[0].strip()

    buildinfo: dict[str, str | Path | None] = {
        "build_date": config.date,
        "fai_action": str(config.fai_action),
        "chroot_install": config.chroot_install_src_directory,
        "classes": ",".join(config.classes),
        "default_bootoptions": config.default_bootoptions,
        "distri_info": config.distri_info,
        "distri_name": config.distri_name,
        "source_image": config.source_image,
        "grml_architecture": config.arch,
        "grml_bootid": config.bootid,
        "grml_debian_version": config.debian_suite,
        "grml_iso_name": config.iso_name,
        "grml_live_cmdline": " ".join(config.cmdline),
        "grml_live_version": config.grml_live_version,
        "grml_name": config.grml_name,
        "grml_short_name": config.short_name,
        "grml_username": config.username,
        "grml_version": config.grml_version,
        "host_architecture": config.arch,
        "mksquashfs_cmdline": " ".join(_build_mksquashfs_cmdline(config)),
        "mksquashfs_version": mksquashfs_version,
        "release_info": config.release_info,
        "release_name": config.release_name,
        "secure_boot": "enable" if config.secure_boot else "disable",
        "timestamp": str(config.source_date_epoch),
        "wayback_date": config.wayback_date,
        "xorriso_cmdline": " ".join(_build_xorriso_cmdline(config)),
        "xorriso_version": xorriso_version,
    }
    clean_buildinfo: dict[str, str | None] = {
        key: str(value).replace(str(config.output_directory), "<output_dir>") if value else value
        for key, value in buildinfo.items()
    }
    return clean_buildinfo


def write_buildinfo_json(
    config: build_facts.BuildConfiguration,
):
    buildinfo = _build_buildinfo_data(
        config,
    )
    logkit.info(f"buildinfo data:\n{buildinfo!s}")
    (config.grml_cd_dir / "conf").mkdir(exist_ok=True)
    (config.grml_cd_dir / "conf" / "buildinfo.json").write_text(json.dumps(buildinfo))


def _build_xorriso_cmdline(
    config: build_facts.BuildConfiguration,
) -> list[str]:
    efi_args = ["-eltorito-alt-boot", "-e", "boot/efi.img", "-no-emul-boot", "-isohybrid-gpt-basdat"]

    if config.arch == "arm64":
        # No BIOS boot on arm64, only UEFI
        boot_args = []
    elif config.arch == "amd64":
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
            config.grml_cd_dir / "boot" / "grub" / "i386-pc" / "boot_hybrid.img",
        ]
    else:
        raise NotImplementedError()

    cmdline = [
        config.builder_programs.xorriso,
        "-as",
        "mkisofs",
        "-V",
        config.iso_volid,
        "-publisher",
        "grml.org/grml-live/",
        "-l",
        "-r",
        "-J",
        *boot_args,
        *efi_args,
        "-o",
        config.grml_isos_dir / config.iso_name,
        str(config.grml_cd_dir) + "/",
    ]
    return [str(value) for value in cmdline]


def create_media(
    config: build_facts.BuildConfiguration,
):
    config.grml_isos_dir.mkdir(exist_ok=True)  # some workflows accept that this already exists
    logkit.info(f"Building ISO image {config.grml_isos_dir / config.iso_name} ...")
    run_x(_build_xorriso_cmdline(config))
    create_sha256_checksum_file(config.grml_isos_dir / config.iso_name)


def _run_tasks(
    config: build_facts.BuildConfiguration,
    grml_live_config: dict[str, str],
    skip_tasks: list[str],
    unshared_service: UnsharedService,
) -> int:
    chroot_directories = _create_chroot_dirs(config.grml_chroot_dir, unshared_service)
    file_ops.create_dir_useable_for_unshare(config.grml_cd_dir)

    # Create a file in log_dir, so grml-live does not complain.
    unshared_service.run(
        unshared_helper.write_file_text(
            (chroot_directories.log_dir / "grml-live"),
            ("This chroot was created by grml-live.\n"),
        )
    )

    # write grml_live_config into the chroot, so chrooted scripts can use it.
    grml_live_config_chroot = chroot_directories.build_dir / "config"
    unshared_service.run(
        unshared_helper.write_file_text(
            grml_live_config_chroot, "\n".join(f"{k}={shlex.quote(v)}" for k, v in grml_live_config.items())
        )
    )

    env: dict[str, str] = {
        "GRML_LIVE_CONFIG": str(grml_live_config_chroot),
        "GRML_LIVE_BUILDDIR": chroot_directories.build_dir_inside,
        "GRML_LIVE_MEDIADIR": chroot_directories.media_dir_inside,
        "GRML_LIVE_NETBOOTDIR": chroot_directories.netboot_dir_inside,
        "GRML_LIVE_SOURCESDIR": chroot_directories.sources_dir_inside,
        "LOGDIR": str(chroot_directories.log_dir),
    } | read_envvars_for_classes(config.config_dir, config.classes)
    show_env("Merged class variables", env)

    # Setup /proc, /sys inside chroot_dir, so future chroot calls will have these mounts.
    unshared_service.run(unshared_helper.bindmount_proc_sys_into(config.grml_chroot_dir))

    try:
        with helper_tools(
            config.config_dir, config.grml_chroot_dir, config.classes, unshared_service
        ) as helper_tools_path:
            class_helper_tools_path = install_class_helper_tools(
                config.config_dir, chroot_directories.build_dir, config.classes, unshared_service
            )

            helper_tools_paths = [helper_tools_path, class_helper_tools_path]

            hook_env: dict[str, str] = env | {"FAI_ACTION": str(config.fai_action)}
            for class_name in config.classes:
                run_script(
                    config.grml_chroot_dir,
                    config.config_dir / "hooks" / class_name / "updatebase",
                    helper_tools_paths,
                    hook_env,
                )

            with policy_rcd(config.grml_chroot_dir, unshared_service):
                if not should_skip_task(skip_tasks, "updatebase"):
                    task_updatebase(config.grml_chroot_dir)

                if not should_skip_task(skip_tasks, "instsoft"):
                    install_packages_for_classes(
                        config.config_dir,
                        config.grml_chroot_dir,
                        config.classes,
                        helper_tools_paths,
                        hook_env,
                        unshared_service,
                    )

            if not should_skip_task(skip_tasks, "configure"):
                for class_name in config.classes:
                    run_class_scripts(
                        "scripts", config.config_dir, config.grml_chroot_dir, class_name, helper_tools_paths, env
                    )

                if config.chroot_install_src_directory:
                    install_extra_chroot_files(
                        config.grml_chroot_dir,
                        config.chroot_install_src_directory,
                        unshared_service,
                    )

            if not should_skip_task(skip_tasks, "squashfs"):
                # mksquashfs is the last thing that should need the userns.
                mksquashfs(config, unshared_service)

            if not should_skip_task(skip_tasks, "build"):
                for class_name in config.classes:
                    run_class_scripts(
                        "media-scripts", config.config_dir, config.grml_chroot_dir, class_name, helper_tools_paths, env
                    )

                logkit.info("Installing media files from chroot build ...")
                run_x(
                    [
                        "/bin/cp",
                        "--no-preserve=all",
                        "--preserve=timestamp",
                        "-rv",
                        str(chroot_directories.media_dir) + "/.",
                        config.grml_cd_dir,
                    ],
                )

                write_buildinfo_json(config)

                create_netboot_package(
                    config.output_directory,
                    chroot_directories.netboot_dir,
                    config.iso_name,
                )
                if "SOURCES" in config.classes:
                    create_sources_package(
                        config.output_directory,
                        chroot_directories.sources_dir,
                        config.iso_name,
                    )

                # After this, no new files should appear.
                create_on_media_md5sums(config.grml_cd_dir, config.grml_name)

                file_ops.clamp_to_source_date_epoch(config.grml_cd_dir)

                create_media(config)

    finally:
        copy_directory_out(config.grml_logs_dir / "fai", chroot_directories.log_dir)

    return 0


def build(config: build_facts.BuildConfiguration):
    grml_live_config: dict[str, str] = {
        "APT_PROXY": os.getenv("APT_PROXY", ""),
        "ARCH": config.arch,
        "BOOTID": config.bootid,
        "BOOT_FILE": config.boot_file,
        "DATE": config.date,
        "DEFAULT_BOOTOPTIONS": config.default_bootoptions,
        "DISTRI_INFO": config.distri_info,
        "DISTRI_NAME": config.distri_name,
        "GRML_LIVE_DEBUG_APT": os.environ.get("GRML_LIVE_DEBUG_APT", ""),
        "GRML_LIVE_VERSION": config.grml_live_version,
        "GRML_NAME": config.grml_name,
        "HOSTNAME": config.hostname,
        "RELEASENAME": config.release_name,
        "RELEASE_INFO": config.release_info,
        "SECURE_BOOT": "debian" if config.secure_boot else "disable",
        "SHORT_NAME": config.short_name,
        "SOURCE_DATE_EPOCH": str(config.source_date_epoch),
        "SQUASHFS_NAME": config.squashfs_name,
        "SUITE": config.debian_suite,
        "USERNAME": config.username,
        "VERSION": config.grml_version,
        "WAYBACK_DATE": config.wayback_date or "",
    }

    show_env("configdump", grml_live_config)

    rc = 0

    try:
        with start_unshared_service() as unshared_service:
            unshared_service.run(unshared_helper.hello_world())
            skiptasks: list[str] = []

            if config.grml_live_action == build_facts.GrmlLiveAction.IMAGE_CREATE:
                if config.grml_chroot_dir.exists():
                    raise ValueError(f"chroot {config.grml_chroot_dir} unexpectedly already exists")
                file_ops.create_dir_useable_for_unshare(config.grml_chroot_dir)

                install_base(
                    config.config_dir,
                    config.grml_chroot_dir,
                    config.classes,
                    config.debian_suite,
                    config.bootstrap_mirror_url,
                )

            elif config.grml_live_action == build_facts.GrmlLiveAction.IMAGE_UPDATE:
                skiptasks = ["updatebase", "instsoft"]
                extract_iso(config)
            else:
                rc = 1
                raise NotImplementedError(f"Action {config.grml_live_action} is not implemented")

            if not rc:
                rc = _run_tasks(config, grml_live_config, skiptasks, unshared_service)
    except (ClassFileParsingFailed, ClassScriptFailed, ProgramStartFailed):
        # assume exception site already printed relevant info
        rc = 3
    except Exception:
        logkit.error(f"{now_for_log()} grml-live builder main caught fatal exception")
        traceback.print_exc()
        rc = 2

    logkit.info(f"grml-live builder exiting with exit code {rc}")
    return rc


def chroot_delete(grml_chroot_dir: Path):
    with start_unshared_service() as unshared_service:
        unshared_service.run(unshared_helper.hello_world())
        unshared_service.run(unshared_helper.run_program(["rm", "-rf", grml_chroot_dir]))
