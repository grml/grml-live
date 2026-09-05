import argparse
import dataclasses
import datetime
import os
import re
import shutil
import subprocess
import sys
import tempfile
import traceback
from pathlib import Path

from . import build_facts, file_ops, logkit, minifai, timing

VERSION = ""
_TRANS_UNSAFE_CHARS = str.maketrans("", "", ",./;- ")
# ECMA-119 demands [A-Z0-9_], but we also allow lowercase letters, '.' and '-'
# as they seem widely supported.
_RE_CD_LABEL_INVALID_CHARS = re.compile("[^A-Za-z0-9_\\-\\.]")
_CD_LABEL_MAXLEN = 32


@dataclasses.dataclass
class DefaultGrmlLivePaths:
    config_dir: Path
    local_help: Path

    @classmethod
    def create_for_install(cls):
        return cls(Path("/usr/share/grml-live/config"), Path("/usr/share/doc/grml-live"))

    @classmethod
    def create_for_source_checkout(cls, source_dir: Path):
        source_dir = source_dir.resolve()
        return cls(source_dir / "config", source_dir / "docs")


def resolve_programs(programs_class):
    construction_args = {}
    for field in dataclasses.fields(programs_class):
        program_name = field.name
        resolved = shutil.which(program_name)
        if not resolved:
            raise ValueError(f'Required program "{program_name}" not available in PATH')
        construction_args[field.name] = Path(resolved)
    return programs_class(**construction_args)


def arg_absolute_path(value: str) -> Path:
    return Path(value).resolve()


def arg_existing_absolute_path(value: str) -> Path:
    path = Path(value).resolve()
    if not path.exists():
        raise argparse.ArgumentTypeError("must exist")
    return path


def arg_key_str(value: str) -> str:
    """argparse "type" function for "key" strings - cannot be empty, cannot have whitespace"""
    if not value:
        raise argparse.ArgumentTypeError("must not be empty")
    if any(char.isspace() for char in value):
        raise argparse.ArgumentTypeError("must not contain whitespace")
    return value


def arg_isoname(value: str) -> str:
    """argparse "type" function for isoname"""
    value = arg_key_str(value)
    if not value.endswith(".iso"):
        raise argparse.ArgumentTypeError('must end in ".iso"')
    if "/" in value:
        raise argparse.ArgumentTypeError('must be a filename, not path (cannot contain "/")')
    return value


def source_date_epoch_datetime() -> datetime.datetime | None:
    env_value = os.getenv("SOURCE_DATE_EPOCH", "")
    if not env_value.strip():
        return None

    try:
        if not (env_value.isascii() and env_value.isdecimal()):
            raise ValueError("Non-digits not allowed")
        int_value = int(env_value)
        if int_value < 1:
            raise ValueError("Value must be positive")
        datetime_value = datetime.datetime.fromtimestamp(int_value, datetime.UTC)
    except (ValueError, OverflowError) as except_inst:
        raise ValueError(f"SOURCE_DATE_EPOCH {env_value!r} from environment is unparseable: {except_inst}") from None

    return datetime_value


class GrmlLiveHelpFormatter(argparse.ArgumentDefaultsHelpFormatter, argparse.RawDescriptionHelpFormatter):
    """Combines both formatter classes, and skips defaults on flags or empty defaults"""

    def _get_help_string(self, action):
        if action.nargs == 0 or action.default is None or action.default == "":
            return action.help
        return super()._get_help_string(action)


def create_argparser(
    default_paths: DefaultGrmlLivePaths, source_date_epoch_dt: datetime.datetime
) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        "grml-live",
        formatter_class=GrmlLiveHelpFormatter,
        add_help=False,
        description="Build tool for Grml(-based) Linux Live-ISOs",
        epilog=f"""
Usage examples:

  %(prog)s image-create
  %(prog)s image-create -c GRML_FULL my-grml-output-dir
  %(prog)s image-create -c GRML_FULL -i grml_0.0-1.iso -v 0.0-1 my-grml-output-dir
  %(prog)s image-create -c GRML_FULL -s stable -r grml-ftw my-grml-output-dir

More details:

  https://grml.org/grml-live/
  {default_paths.local_help}


Please send your bug reports and feedback to the grml-team: https://grml.org/bugs/
""",
    )

    parser.add_argument("-h", "--help", action="help", default=argparse.SUPPRESS, help=argparse.SUPPRESS)

    subparsers = parser.add_subparsers(required=True, help="subcommand help")
    parser_image_create = subparsers.add_parser("image-create", help="Run a complete build from scratch")
    parser_image_create.set_defaults(grml_live_action=build_facts.GrmlLiveAction.IMAGE_CREATE)
    parser_image_update = subparsers.add_parser("image-update", help="Update an existing ISO")
    parser_image_update.set_defaults(grml_live_action=build_facts.GrmlLiveAction.IMAGE_UPDATE)

    for subparser in (parser_image_create, parser_image_update):
        subparser.add_argument(
            "--boot-options", type=str, dest="default_bootoptions", default="", help="Add these boot options"
        )
        subparser.add_argument(
            "-c",
            type=arg_key_str,
            dest="classes",
            metavar="CLASS1,CLASS2",
            default="GRML_FULL",
            help="Classes to be used for building the ISO",
        )
        subparser.add_argument(
            "--distri-info",
            type=str,
            dest="distri_info",
            default="Grml - Live Linux for system administrators",
            help="Set DISTRI_INFO",
        )
        subparser.add_argument(
            "--distri-name", type=arg_key_str, dest="distri_name", default="grml", help="Set DISTRI_NAME"
        )
        subparser.add_argument("--hostname", type=arg_key_str, dest="hostname", default="grml", help="Set HOSTNAME")
        subparser.add_argument("--username", type=arg_key_str, dest="username", default="grml", help="Set USERNAME")
        subparser.add_argument(
            "-d",
            type=arg_key_str,
            dest="date",
            default=str(source_date_epoch_dt.strftime("%Y-%m-%d")),
            metavar="DATE",
            help="Use specified date instead of build time as date of release",
        )
        subparser.add_argument(
            "-D",
            type=arg_absolute_path,
            dest="config_dir",
            metavar="CONFIGDIR",
            default=default_paths.config_dir,
            help="Use specified configuration directory",
        )
        subparser.add_argument("-F", action="store_true", dest="force", help="Force execution without prompting")
        subparser.add_argument(
            "-g",
            type=arg_key_str,
            dest="grml_name",
            metavar="GRML_NAME",
            default="grml",
            help="Set the grml flavour name",
        )
        subparser.add_argument(
            "-i",
            type=arg_isoname,
            dest="iso_name",
            metavar="ISO_NAME",
            help="Set the name of the resulting ISO (and other build results)",
        )
        subparser.add_argument(
            "-I",
            type=arg_absolute_path,
            dest="chroot_install_src_directory",
            metavar="CHROOT_INSTALL_DIRECTORY",
            help="Directory which provides files that should become part of the chroot/ISO",
        )
        subparser.add_argument(
            "--on-error-shell",
            action="store_true",
            default=False,
            help="Start a shell on build failure",
        )
        subparser.add_argument(
            "-r",
            type=str,
            dest="release_name",
            metavar="RELEASE_NAME",
            default="grml-live rocks",
            help="Set the grml release name",
        )
        subparser.add_argument(
            "-R",
            dest="is_release",
            action="store_false",
            default=True,
            help="Skip applying the RELEASE class and cleanup",
        )
        subparser.add_argument(
            "-s",
            type=arg_key_str,
            dest="debian_suite",
            metavar="SUITE",
            default="testing",
            help="Debian suite/release, like: stable, testing, unstable",
        )
        subparser.add_argument("--secure-boot", action="store_true", help="Enable Secure Boot using Debian method")
        subparser.add_argument(
            "-v",
            type=arg_key_str,
            dest="grml_version",
            metavar="VERSION_NUMBER",
            default="0.0.1",
            help="Set the grml version number",
        )

    mirror_options = parser_image_create.add_mutually_exclusive_group()
    mirror_options.add_argument(
        "--bootstrap-mirror-url",
        type=arg_key_str,
        default="http://deb.debian.org/debian",
        help="Debian mirror URL for creating chroot",
    )
    mirror_options.add_argument(
        "-w",
        type=arg_key_str,
        dest="wayback_date",
        metavar="DATE",
        help="Wayback machine, build system using Debian archives from specified date",
    )

    parser_image_create.add_argument(
        "output_directory",
        type=arg_absolute_path,
        metavar="OUTPUT_DIRECTORY",
        default=str(Path.cwd() / "grml"),
        help="Build result will be stored in this directory",
    )

    parser_image_update.add_argument(
        "source_image",
        type=arg_absolute_path,
        metavar="SOURCE_IMAGE",
        help="Extract chroot contents from SOURCE_IMAGE ISO",
    )
    parser_image_update.add_argument(
        "output_directory",
        type=arg_absolute_path,
        metavar="OUTPUT_DIRECTORY",
        default=str(Path.cwd() / "grml"),
        help="Build result will be stored in this directory",
    )

    return parser


def show_build_config(build_config: build_facts.BuildConfiguration):
    logkit.info_header(f"grml-live [{build_config.grml_live_version}] Build Configuration:")

    print(f"""
    SOURCE_DATE_EPOCH: {build_config.source_date_epoch}
    Build mode:        {build_config.fai_action}
    FAI classes:       {",".join(build_config.classes)}
    Debian suite:      {build_config.debian_suite}
    Architecture:      {build_config.arch}
    Output directory:  {build_config.output_directory}
    Work directory:    {build_config.work_directory}""")

    print(f"""\n  Input:
    Config Space:      {build_config.config_dir}""")
    if build_config.grml_live_action == build_facts.GrmlLiveAction.IMAGE_CREATE:
        print(f"""    Bootstrap mirror:  {build_config.bootstrap_mirror_url}
    Wayback date:      {build_config.wayback_date}""")
    else:
        print(f"    Extract ISO:       {build_config.source_image}")

    print(f"""\n  Output identification:
    ISO Filename:      {build_config.iso_name}
    ISO Volume Label:  {build_config.iso_volid}
    Distri Name:       {build_config.distri_name}
    Distri Info:       "{build_config.distri_info}"
    Grml Name:         {build_config.grml_name}
    Release Name:      "{build_config.release_name}"
    Build date:        {build_config.date}
    Grml Version:      {build_config.grml_version}
    Boot identifier:   {build_config.bootid}
    Is Release Build:  {build_config.is_release}""")

    print(f"""\n  Features:
    Secure Boot:       {build_config.secure_boot}""")
    if build_config.chroot_install_src_directory:
        print(f"    Install files from directory to chroot:  {build_config.chroot_install_src_directory}")
    if build_config.default_bootoptions:
        print(f'    Adding default bootoptions: "{build_config.default_bootoptions}"')
    print()


def sanitize_env():
    # Clean up the process environment. To the benefit of our child processes.
    os.environ["LANG"] = "C"
    os.environ["LC_ALL"] = "C"
    for key in ["GRML_LIVE_VERSION", "TMPDIR"]:
        if key in os.environ:
            del os.environ[key]


def get_program_output(args, check: bool = True, **kwargs):
    return subprocess.run(args, check=check, capture_output=True, **kwargs).stdout.decode().strip()


def dpkg_architecture(builder_programs: build_facts.BuilderPrograms) -> str:
    return get_program_output([builder_programs.dpkg, "--print-architecture"])


def git_describe_always(cwd: Path) -> str:
    try:
        return get_program_output(["git", "describe", "--always"], cwd=cwd)
    except (OSError, subprocess.CalledProcessError):
        return "***UNKNOWN***"


def automatic_classes(input: str, arch: str, debian_suite: str, is_release: bool, secure_boot: bool) -> list[str]:
    # strip and ignore empty components
    classes = input.split(",")
    classes = [class_name for class_name in classes if class_name]
    if not classes:
        raise ValueError("At least one class must be given")
    for class_name in ["GRMLBASE", "SECURE_BOOT", "RELEASE", "AMD64", "ARM64", "I386"]:
        if class_name in classes:
            raise ValueError(f"Class {class_name} explicity requested. This is unsupported, remove it.")

    debian_class = f"DEBIAN_{debian_suite.upper()}"
    if debian_class == "DEBIAN_SID":
        # avoid having to maintain DEBIAN_UNSTABLE *and* DEBIAN_SID class files
        debian_class = "DEBIAN_UNSTABLE"

    classes = [debian_class, "GRMLBASE", *classes]

    if secure_boot:
        classes.append("SECURE_BOOT")
    if is_release:
        classes.append("RELEASE")

    classes.append(arch.upper())
    return classes


def strip_unsafe_chars(s: str) -> str:
    return s.translate(_TRANS_UNSAFE_CHARS)


def _build_iso_volid(grml_name: str, grml_version: str) -> str:
    # assumes grml_name and grml_version cannot contain whitespace,
    # currently checked by argparser.
    version = re.sub(_RE_CD_LABEL_INVALID_CHARS, "", grml_version)
    name = re.sub(_RE_CD_LABEL_INVALID_CHARS, "", grml_name)
    # build string in reversed order, so version gets to keep most of its
    # characters.
    base = f"{version} {name}"
    # snip to maximum length
    base = base[0:_CD_LABEL_MAXLEN]
    # now split and reverse, so name is first
    version, _, name = base.partition(" ")
    return f"{name}_{version}"  # must still fit into _CD_LABEL_MAXLEN


def _main(argv: list[str]) -> int:
    global VERSION
    VERSION = os.getenv("GRML_LIVE_VERSION", "?")
    tmpdir = os.getenv("TMPDIR", "/tmp")
    startup_dt = datetime.datetime.now(datetime.UTC)
    sanitize_env()

    try:
        source_date_epoch_dt = source_date_epoch_datetime()
        source_date_epoch_error = None
    except ValueError as except_inst:
        # Store error message, so parse_args can handle --help.
        source_date_epoch_dt = None
        source_date_epoch_error = str(except_inst)
    if not source_date_epoch_dt:
        # Use now, to get consistent date across everything.
        # NOTE: option -d is NOT converted to SOURCE_DATE_EPOCH, contrary to the old shell implementation.
        source_date_epoch_dt = startup_dt
    source_date_epoch = int(source_date_epoch_dt.timestamp())

    sysprefix = Path(__file__).resolve().parents[4]  # drop usr / lib / grml-live / main.py
    if (sysprefix / "grml-live").exists():
        # assume source checkout
        default_paths = DefaultGrmlLivePaths.create_for_source_checkout(sysprefix)
        # ask git about a version
        VERSION = git_describe_always(sysprefix)
    else:
        default_paths = DefaultGrmlLivePaths.create_for_install()

    args = create_argparser(default_paths, source_date_epoch_dt).parse_args(argv[1:])

    # after parse_args, so parse_args can handle --help.
    if os.geteuid() == 0:
        logkit.error("grml-live needs to run as non-root with working user namespaces")
        return 1
    if source_date_epoch_error:
        logkit.error(source_date_epoch_error)
        return 1

    try:
        builder_programs = resolve_programs(build_facts.BuilderPrograms)
        if args.grml_live_action == build_facts.GrmlLiveAction.IMAGE_UPDATE:
            extract_programs = resolve_programs(build_facts.ExtractPrograms)
        else:
            extract_programs = None
    except ValueError as except_inst:
        logkit.error(f"{except_inst!s}")
        return 1

    arch = dpkg_architecture(builder_programs)
    if arch not in build_facts.SUPPORTED_ARCHS:
        logkit.error(f"dpkg architecture {arch!s} not supported.")
        return 1

    short_name = strip_unsafe_chars(args.grml_name)

    if args.grml_live_action == build_facts.GrmlLiveAction.IMAGE_CREATE:
        bootstrap_mirror_url: str | None = args.bootstrap_mirror_url
        if args.wayback_date:
            bootstrap_mirror_url: str = f"http://snapshot.debian.org/archive/debian/{args.wayback_date}/"
            wayback_date = args.wayback_date
        else:
            wayback_date = None
    else:
        bootstrap_mirror_url: str | None = None
        wayback_date = None

    iso_name = args.iso_name
    if iso_name:
        iso_volid, _, _ = iso_name.rpartition(".iso")
        iso_volid = re.sub(_RE_CD_LABEL_INVALID_CHARS, "", iso_name)[0:_CD_LABEL_MAXLEN]
    else:
        iso_name = f"{args.grml_name}_{args.grml_version}.iso"
        iso_volid = _build_iso_volid(args.grml_name, args.grml_version)

    squashfs_name = f"{args.grml_name}.squashfs"

    output_directory: Path = args.output_directory
    work_directory_tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True, dir=tmpdir, prefix="gl")
    work_directory = Path(work_directory_tmp.name)
    work_directory.chmod(0o755)
    file_ops.create_dir_useable_for_unshare(work_directory)

    try:
        classes = automatic_classes(args.classes, arch, args.debian_suite, args.is_release, args.secure_boot)
    except ValueError as except_inst:
        logkit.error(f"{except_inst!s}")
        return 1

    # TODO: need fixing/removal when there are other actions than image-create and image-update
    fai_action = (
        build_facts.FaiAction.DIRINSTALL
        if args.grml_live_action == build_facts.GrmlLiveAction.IMAGE_CREATE
        else build_facts.FaiAction.SOFTUPDATE
    )

    # Once build_config exists, avoid reading anything directly from `args`.
    build_config = build_facts.BuildConfiguration(
        grml_live_version=VERSION,
        cmdline=argv,
        fai_action=fai_action,
        grml_live_action=args.grml_live_action,
        arch=arch,
        builder_programs=builder_programs,
        classes=classes,
        config_dir=args.config_dir,
        output_directory=output_directory,
        work_directory=work_directory,
        grml_cd_dir=work_directory / "grml_cd",
        grml_cd_live_dir=work_directory / "grml_cd" / "live",
        grml_cd_squashfs_dir=work_directory / "grml_cd" / "live" / args.grml_name,
        grml_cd_squashfs_name=work_directory / "grml_cd" / "live" / args.grml_name / squashfs_name,
        grml_chroot_dir=work_directory / "grml_chroot",
        grml_isos_dir=output_directory / "grml_isos",
        grml_logs_dir=output_directory / "grml_logs",
        source_image=args.source_image if args.grml_live_action == build_facts.GrmlLiveAction.IMAGE_UPDATE else None,
        extract_programs=extract_programs,
        distri_name=args.distri_name,
        distri_info=args.distri_info,
        grml_name=args.grml_name,
        short_name=short_name,
        grml_version=args.grml_version,
        iso_name=iso_name,
        iso_volid=iso_volid,
        release_name=args.release_name,
        release_info=f"{args.grml_name} {args.grml_version} - Release Codename {args.release_name}",
        hostname=args.hostname,
        username=args.username,
        squashfs_name=squashfs_name,
        boot_file=f"/conf/bootfile_{short_name}_{source_date_epoch}",
        is_release=args.is_release,
        date=args.date,
        source_date_epoch=source_date_epoch,
        wayback_date=wayback_date,
        debian_suite=args.debian_suite,
        bootstrap_mirror_url=bootstrap_mirror_url,
        secure_boot=args.secure_boot,
        chroot_install_src_directory=args.chroot_install_src_directory,
        bootid=strip_unsafe_chars(f"{args.grml_name}{args.grml_version}"),
        default_bootoptions=args.default_bootoptions,
    )

    if not build_config.config_dir.exists():
        logkit.error(
            f"Config directory {build_config.config_dir!s} does not exist. Set -D to a valid config directory.",
        )
        return 1

    try:
        file_ops.check_dir_usable_for_unshare(build_config.config_dir)
        file_ops.check_dir_usable_for_unshare(build_config.output_directory, missing_ok=True)
        if build_config.chroot_install_src_directory:
            file_ops.check_dir_usable_for_unshare(build_config.chroot_install_src_directory)

    except ValueError as except_inst:
        logkit.error(f"{except_inst!s}")
        return 1

    if not args.force:
        show_build_config(build_config)

    # Warnings go after build config printing, but before confirmation.
    if not (build_config.config_dir / "media-files" / "GRMLBASE" / "addons" / "arch").exists():
        logkit.warn('Boot addons not found. Consider installing package "grml-live-addons".')

    if "NO_ONLINE" not in build_config.classes:
        logkit.warn('Class "NO_ONLINE" NOT requested. Output will NOT be reproducible.')

    # Last minute checks before confirmation.
    # TODO: These checks should not trigger with the image-create/image-update actions;
    # later when we introduce chroot-... actions, we need the checks again.
    chroot_os_release = Path(build_config.grml_chroot_dir / "etc" / "os-release")
    if build_config.fai_action == build_facts.FaiAction.DIRINSTALL:
        if chroot_os_release.exists():
            logkit.error("the chroot already exists. Refusing to overwrite it. (Add -u/-b/-B option?)")
            return 20
        if build_config.source_image:
            logkit.error("using an existing ISO precludes building a new chroot. (Add -u/-b/-B option?)")
            return 20
    elif not build_config.source_image and not chroot_os_release.exists():
        logkit.error(
            "does not look like you have a working chroot. Updating/building not possible. (Drop -u/-b/-B option?)"
        )
        return 20
    elif build_config.source_image and chroot_os_release.exists():
        logkit.error("the chroot already exists. Refusing to overwrite it by extracting an ISO. (Remove -e option?)")
        return 20

    if not args.force:
        print()
        try:
            prompt_result = input("Check the build settings. (Use -F to skip this prompt.)\nContinue? [y/N] ")
        except EOFError:
            prompt_result = ""
            logkit.error("EOF received")
        if prompt_result.strip().upper() != "Y":
            logkit.info("Exiting as requested.")
            return 1

    # Now run the build.
    # Create grml_logs_dir (and its parent) first, so we can write the log!
    file_ops.create_dir_useable_for_unshare(build_config.grml_logs_dir)
    logfile = build_config.grml_logs_dir / "grml-live.log"

    logkit.info(f"Starting build, writing log to {logfile}.\n")
    with logkit.tee_output_to(logfile):
        logkit.info(f"grml-live command line: {' '.join(build_config.cmdline)}")
        logkit.info(f"grml-live started at: {startup_dt}")
        print()
        # write configuration into log
        show_build_config(build_config)
        os.environ["SOURCE_DATE_EPOCH"] = str(source_date_epoch)

        with timing.log_elapsed_time("Build run"):
            try:
                rc = minifai.build(build_config)
            except KeyboardInterrupt as except_inst:
                rc = 130
                logkit.error(f"build aborted: {except_inst}")
            except BaseException as except_inst:
                # Need BaseException to catch all exceptions, so they end up in the log
                rc = 1
                logkit.error(f"build failed with unhandled exception: {except_inst}")
                traceback.print_exc()
            finally:
                if (rc != 0) and args.on_error_shell:
                    logkit.error("build failed, spawning unshared(!) bash for you to inspect build files")
                    print(f"Work directory is: {build_config.work_directory}")
                    print(f"Chroot directory is: {build_config.grml_chroot_dir}")
                    print(f'Use "/usr/sbin/chroot {build_config.grml_chroot_dir}" to enter the chroot if needed')
                    try:
                        minifai.run_x(["/bin/bash", "-i"], unshared=True, cwd=work_directory)
                    except Exception as except_inst:
                        logkit.info(f"Sorry, the shell failed: {except_inst}")
                        traceback.print_exc()
                logkit.info(f"Cleaning up chroot: {build_config.grml_chroot_dir}")
                minifai.chroot_delete(build_config.grml_chroot_dir)
                logkit.info(f"Cleaning up work_directory: {work_directory}")
                work_directory_tmp.cleanup()

        if rc == 0:
            logkit.info("Successfully finished execution.")
        else:
            # Write final status to both stdout and stderr
            logkit.error(f"Execution failed with rc={rc}")
            print(f"E: Execution failed with rc={rc}")

    return rc


def main() -> int:
    return _main(sys.argv)


if __name__ == "__main__":
    sys.exit(main())
