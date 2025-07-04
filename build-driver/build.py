#!/usr/bin/env python3
#
# Main entry point for CI builds.
# We are started by ./build, which in turn is started by the CI config.
# Dependencies can be available, if ./build installs them first.
#
from pathlib import Path
import datetime
import contextlib
import subprocess
import os
import shutil
import time
import sys
import tempfile
from dataclasses import dataclass

import yaml

TOOL_DIR = Path(__file__).parent


@dataclass(frozen=True)
class JobProperties:
    job_timestamp: datetime.datetime
    job_name: str
    arch: str
    classes: list
    debian_suite: str
    version: str
    release_name: str
    grml_name: str
    iso_name: str  # name of the resulting .ISO files
    sources_name: str  # name of the resulting sources tarball
    logs_name: str  # name of the resulting logs directory


def usage(program_name):
    message = f"""
Usage: {program_name} grml_live_path build_mode config_file flavor arch ...

Examples:
    {program_name} /build/job/grml-live release ./config/release-pre2024.XX-rc0 small amd64
    {program_name} /build/job/grml-live daily ./config/daily small amd64 testing
    """
    print(message.strip(), file=sys.stderr)


def run_x(args, check: bool = True, **kwargs):
    # str-ify Paths, not necessary, but for readability in logs.
    args = [arg if isinstance(arg, str) else str(arg) for arg in args]
    args_str = '" "'.join(args)
    print(f'D: Running "{args_str}"', flush=True)
    return subprocess.run(args, check=check, **kwargs)


@contextlib.contextmanager
def ci_section(title: str, *, collapsed: bool = True):
    section_key = f"sec{time.time()}"
    collapsed_str = "[collapsed=true]" if collapsed else ""
    print(f"\x1b[0Ksection_start:{int(time.time())}:{section_key}{collapsed_str}\r\x1b[0K{title}", flush=True)
    yield
    print(f"\x1b[0Ksection_end:{int(time.time())}:{section_key}\r\x1b[0K", flush=True)


def is_docker():
    return (
        Path("/.dockerenv").exists()
        or Path("/run/.containerenv").exists()
        or (Path("/proc/1/cgroup").exists() and b"devices:/docker" in Path("/proc/1/cgroup").read_bytes())
    )


def is_ci():
    return os.getenv("CI", "false") == "true"


def apt_satisfy(deps: str):
    run_x(
        ["apt-get", "satisfy", "-q", "-y", "--no-install-recommends", deps.strip()],
        env=dict(os.environ) | {"DEBIAN_FRONTEND": "noninteractive"},
    )


def print_grml_live_version(grml_live_path: Path):
    result = run_x(["git", "describe", "--always"], cwd=grml_live_path, capture_output=True)
    version = result.stdout.strip().decode()
    print(f"I: grml-live version: {version}")


def run_grml_live(
    grml_live_path: Path,
    output_dir: Path,
    arch: str,
    classes: list,
    debian_suite: str,
    version: str,
    release_name: str,
    grml_name: str,
    iso_name: str,
    old_iso_path: Path | None,
    source_date_epoch: datetime.datetime,
):
    env = dict(os.environ)
    grml_fai_config = grml_live_path / "config"
    env.update(
        {
            "GRML_FAI_CONFIG": str(grml_fai_config),
            "LIVE_CONF": str(grml_live_path / "etc" / "grml" / "grml-live.conf"),
            "SOURCE_DATE_EPOCH": str(int(source_date_epoch.timestamp())),
        }
    )

    grml_live_cmd = [
        grml_live_path / "grml-live",
        "-F",  # do not prompt
        "-A",  # cleanup afterwards
        "-a",
        arch,
        "-c",
        ",".join(classes),
        "-s",
        debian_suite,
        "-v",
        version,
        "-r",
        release_name,
        "-g",
        grml_name,
        "-i",
        iso_name,
        "-o",
        output_dir,
    ]
    if old_iso_path:
        grml_live_cmd += ["-b", "-e", old_iso_path]
    with ci_section("Building with grml-live", collapsed=False):
        run_x(grml_live_cmd, env=env)


def upload_daily(job_name: str, build_dir: Path, job_timestamp: datetime.datetime):
    ssh_key = os.getenv("DAILY_UPLOAD_SSH_KEY")
    remote = os.getenv("DAILY_UPLOAD_REMOTE")
    stamped_dirname = job_timestamp.strftime("%Y-%m-%d_%H_%M_%S")
    with ci_section("Uploading to daily.grml.org"):
        run_x(
            [
                TOOL_DIR / "upload-daily.py",
                ssh_key,
                f"{remote}{job_name}",
                build_dir,
                job_name,
                stamped_dirname,
            ]
        )


def get_dpkg_list_path_for_build(build_dir: Path) -> Path:
    return build_dir / "grml_logs" / "fai" / "dpkg.list"


def generate_changes_list(
    build_dir: Path,
    output_filename: str,
    old_dpkg_list: Path,
    build_job_name: str,
    build_version: str,
):
    package_prefix = "grml"
    git_url_base = "https://github.com/grml"
    git_workspace = Path("/tmp") / "changes-git-workspace"
    output_file = build_dir / "grml_logs" / output_filename
    new_dpkg_list = get_dpkg_list_path_for_build(build_dir)

    with ci_section(f"Generating changes list {output_file!s}"):
        run_x(
            [
                TOOL_DIR / "generate-changes-list.py",
                output_file,
                new_dpkg_list,
                old_dpkg_list,
                package_prefix,
                git_url_base,
                git_workspace,
                build_job_name,
                build_version,
            ]
        )


@contextlib.contextmanager
def results_mover(build_dir: Path, output_dir: Path):
    try:
        yield
    except Exception:
        print("E: Caught fatal exception")
        raise
    finally:
        print(f"I: moving build results from {build_dir} to {output_dir}")
        if output_dir.exists():
            raise RuntimeError(f"output_dir {output_dir} exists, but shutil.move requires it not to")
        shutil.move(build_dir, output_dir)


def download_file(url: str, local_path: Path):
    """Download URL url into local_path, using curl. Raises on failure."""
    run_x(["curl", "-#fSL", "--output", local_path, url])


def skip_sources_requested(build_config: dict, env: dict) -> bool:
    if env.get("SKIP_SOURCES", "") == "1":
        return True
    if build_config.get("skip_sources", False) is True:
        return True
    return False


def get_grml_live_classes(flavor: str, classes_for_mode: list[str], skip_sources: bool) -> list[str]:
    base_classes = [f"GRML_{flavor.upper()}"]

    # Add extra classes from environment variable
    extra_classes = os.getenv("EXTRA_CLASSES", "").strip()
    if extra_classes:
        extra_class_list = [cls.strip() for cls in extra_classes.split(",") if cls.strip()]
        base_classes += extra_class_list
        print(f"I: Adding extra classes: {extra_class_list}")

    if skip_sources:
        print("I: SKIP_SOURCES=1, skipping source download (either from config or ENV)")
    else:
        base_classes += ["SOURCES"]
    return base_classes + classes_for_mode


def build(
    build_dir: Path,
    old_dpkg_list_daily: Path | None,
    old_dpkg_list_last_release: Path | None,
    job_properties: JobProperties,
    grml_live_path: Path,
    old_iso_path: Path | None,
):
    run_grml_live(
        grml_live_path,
        build_dir,
        job_properties.arch,
        job_properties.classes,
        job_properties.debian_suite,
        job_properties.version,
        job_properties.release_name,
        job_properties.grml_name,
        job_properties.iso_name,
        old_iso_path,
        job_properties.job_timestamp,
    )

    if old_dpkg_list_daily:
        generate_changes_list(
            build_dir,
            "changes-last-daily.txt",
            old_dpkg_list_daily,
            job_properties.job_name,
            job_properties.version,
        )

    if old_dpkg_list_last_release:
        generate_changes_list(
            build_dir,
            "changes-last-release.txt",
            old_dpkg_list_last_release,
            job_properties.job_name,
            job_properties.version,
        )


def load_config(build_config_file: str) -> dict:
    with Path(build_config_file).open() as stream:
        return yaml.safe_load(stream)


def bail(message: str) -> int:
    print(f"E: {message}", file=sys.stderr)
    return 2


def install_debian_dependencies():
    # TODO: read (some!) deps from grml-live/debian/control
    with ci_section("Installing dependencies from Debian"):
        apt_satisfy(
            """
            ca-certificates ,
            git ,
            curl ,
            dosfstools ,
            jo ,
            mmdebstrap ,
            moreutils ,
            mtools ,
            python3-paramiko ,
            rsync ,
            squashfs-tools ,
            socat ,
            xorriso ,
            imagemagick ,
            """
        )


def download_old_dpkg_list_last_release(
    tmp_dir: Path, last_release_version: str | None, flavor: str, arch: str
) -> Path | None:
    if last_release_version is None:
        return None

    path = tmp_dir / "dpkg.list.previous_release"
    url = f"https://ftp-master.grml.org/grml-{last_release_version}-metadata/grml-{flavor}-{last_release_version}-{arch}/dpkg.list"
    with ci_section(f"Downloading old dpkg.list {url} to {path!s}"):
        try:
            download_file(url, path)
            return path
        except Exception as except_inst:
            print(f"E: ignoring error while downloading {url}: {except_inst}")
            return None


def download_old_iso(tmp_dir: Path, old_iso_url: str) -> Path | None:
    path = tmp_dir / "old.iso"

    with ci_section(f"Downloading old ISO {old_iso_url} to {path!s}"):
        download_file(old_iso_url, path)

    return path


def download_old_sources(tmp_dir: Path, old_iso_url: str) -> Path | None:
    path = tmp_dir / "old-sources.tar"

    # https://.../2024-12-18_10_03_44/grml_isos/grml...iso
    # => https://.../2024-12-18_10_03_44/ , _, grml...iso
    old_base_url, _, old_iso_name = old_iso_url.rsplit("/", 2)
    # grml-something.iso => grml-something-sources.tar
    old_sources_name = old_iso_name.rsplit(".", 1)[0] + "-sources.tar"
    old_sources_url = f"{old_base_url}/{old_sources_name}"

    with ci_section(f"Downloading old Sources {old_sources_url} to {path!s}"):
        download_file(old_sources_url, path)

    return path


def main(program_name: str, argv: list[str]) -> int:
    print(f"I: {program_name} started with {argv=}")
    try:
        grml_live_path = Path(argv.pop(0))
        build_mode = argv.pop(0)
        build_config_file = argv.pop(0)
        if build_mode == "release":
            flavor = argv.pop(0)
            arch = argv.pop(0)
            debian_suite = ""  # filled from config
            classes_for_mode = ["SNAPSHOT", "NO_ONLINE"]
            upload_to_daily = False

        elif build_mode == "daily":
            flavor = argv.pop(0)
            arch = argv.pop(0)
            debian_suite = argv.pop(0)
            classes_for_mode = []
            upload_to_daily = os.getenv("DO_DAILY_UPLOAD", "") == "1"

        else:
            return bail(f"build_mode {build_mode} not understood, valid options are: release, daily")

    except IndexError:
        usage(program_name)
        return 2

    if arch not in ("amd64", "i386", "arm64"):
        return bail(f"unknown build_arch: {arch}")

    if not is_ci():
        print("I: No CI variable found, assuming local test build")
        if not is_docker():
            return bail("E: Not running inside docker, exiting to avoid data damage")

    build_config = load_config(build_config_file)

    skip_sources = skip_sources_requested(build_config, dict(os.environ))
    # skip SOURCES in release mode as grml-live would re-download all sources,
    # possibly mismatching the versions. Also we do not prepare a working DNS,
    # so it would just fail. In the future, grml-live should support reusing
    # the sources tarball and fetching just the necessary differences.
    classes = get_grml_live_classes(flavor, classes_for_mode, skip_sources or build_mode == "release")

    build_grml_name = f"grml-{flavor}-{arch}"
    last_release_version = build_config["last_release"]

    # build_grml_live_branch = os.getenv("USE_GRML_LIVE_BRANCH", "master")

    # We try to construct an ISO name like this:
    #   daily:   grml-full-daily20230201build20unstable-amd64.iso
    #   release: grml-full-2024.12-arm64.iso
    # Note that release builds do not carry the debian suite in their name.

    CI_PIPELINE_CREATED_AT = os.getenv("CI_PIPELINE_CREATED_AT", "")
    if CI_PIPELINE_CREATED_AT != "":
        print("I: deriving job timestamp from CI_PIPELINE_CREATED_AT variable")
        job_timestamp = datetime.datetime.fromisoformat(CI_PIPELINE_CREATED_AT.replace("Z", "+00:00"))
    else:
        print(f"I: deriving job timestamp from {build_config_file} mtime")
        job_timestamp = datetime.datetime.fromtimestamp(Path(build_config_file).stat().st_mtime)

    if build_mode == "release":
        old_iso_url = build_config["base_iso"][flavor][arch]
        build_version = build_config["release_version"]
        artifact_basename = f"grml-{flavor}-{build_version}-{arch}"

        job_properties = JobProperties(
            job_timestamp=datetime.datetime.now(),
            job_name=f"{build_grml_name}-release",
            arch=arch,
            classes=classes,
            # XXX: should load this from ISO or metadata file
            debian_suite=build_config["debian_suite"],
            # f.e. "pre2024.11-rc0"
            version=build_version,
            # f.e. "Glumpad Grumbirn"
            release_name=build_config["release_name"],
            grml_name=build_grml_name,
            iso_name=f"{artifact_basename}.iso",
            sources_name=f"{artifact_basename}-sources.tar",
            logs_name=f"{artifact_basename}-logs",
        )

    elif build_mode == "daily":
        old_iso_url = None
        CI_PIPELINE_IID = os.getenv("CI_PIPELINE_IID", "0")
        date_stamp = job_timestamp.strftime("%Y%m%d")
        build_version = f"d{date_stamp}b{CI_PIPELINE_IID}"
        build_release_name = f"daily{date_stamp}build{CI_PIPELINE_IID}{debian_suite}"
        artifact_basename = f"grml-{flavor}-{build_release_name}-{arch}"
        job_properties = JobProperties(
            job_timestamp=job_timestamp,
            job_name=f"{build_grml_name}-{debian_suite}",
            arch=arch,
            classes=classes,
            debian_suite=debian_suite,
            version=build_version,
            release_name=build_release_name,
            grml_name=build_grml_name,
            iso_name=f"{artifact_basename}.iso",
            sources_name=f"{artifact_basename}-sources.tar",
            logs_name=f"{artifact_basename}-logs",
        )

    else:
        raise ValueError(f"unexpected {build_mode=}")

    print(f"I: {job_properties=}")
    print(f"I: {last_release_version=}")

    print_grml_live_version(grml_live_path)

    source_dir = Path(os.getcwd())
    cache_dir = source_dir / "cached"
    output_dir = source_dir / "results"
    print(f"I: {source_dir=}")
    print(f"I: {cache_dir=}")
    print(f"I: {output_dir=}")

    # avoid building on mounted volume
    tmp_root = Path(tempfile.gettempdir())
    tmp_dir = Path(tempfile.mkdtemp(dir=tmp_root))
    build_dir = Path(tempfile.mkdtemp(dir=tmp_root))

    # Do it now, as the next block needs curl installed.
    install_debian_dependencies()

    old_dpkg_list_previous_build = cache_dir / "dpkg.list"
    old_dpkg_list_last_release = download_old_dpkg_list_last_release(tmp_dir, last_release_version, flavor, arch)
    if old_iso_url is None:
        old_iso_path = None
    else:
        old_iso_path = download_old_iso(tmp_dir, old_iso_url)
    if skip_sources or old_iso_url is None:
        old_sources_path = None
    else:
        old_sources_path = download_old_sources(tmp_dir, old_iso_url)

    with results_mover(build_dir, output_dir):
        build(
            build_dir,
            old_dpkg_list_previous_build,
            old_dpkg_list_last_release,
            job_properties,
            grml_live_path,
            old_iso_path,
        )

        # Remove the sources *directory*, to not have the sources twice in the CI artifacts.
        grml_sources_directory = build_dir / "grml_sources"
        if grml_sources_directory.exists():
            print(f"I: Removing {grml_sources_directory}")
            shutil.rmtree(grml_sources_directory, ignore_errors=True)

        if old_sources_path:
            old_sources_path.rename(build_dir / job_properties.sources_name)

        # Copy dpkg.list from grml_logs into cache for next iteration.
        new_dpkg_list = get_dpkg_list_path_for_build(build_dir)
        old_dpkg_list_previous_build.parent.mkdir(exist_ok=True)
        shutil.copyfile(new_dpkg_list, old_dpkg_list_previous_build)

        (build_dir / "grml_logs").rename(build_dir / job_properties.logs_name)

        if upload_to_daily:
            upload_daily(job_properties.job_name, build_dir, job_properties.job_timestamp)

    print("I: Success.")

    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv.pop(0), sys.argv))
