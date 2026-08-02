import argparse
import dataclasses
import datetime
import os
import shutil
import subprocess
import sys
import traceback
from pathlib import Path

from . import build_facts, file_ops, logkit, minifai, timing

VERSION = ""
_TRANS_UNSAFE_CHARS = str.maketrans("", "", ",./;- ")


@dataclasses.dataclass
class DefaultGrmlLivePaths:
    config_dir: Path  # fai space

    @classmethod
    def create_for_install(cls):
        return cls(Path("/usr/share/grml-live/config"))

    @classmethod
    def create_for_source_checkout(cls, source_dir: Path):
        source_dir = source_dir.resolve()
        return cls(source_dir / "config")


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


def arg_key_str(value: str) -> str:
    """argparse "type" function for "key" strings - cannot be empty, cannot have whitespace"""
    if not value:
        raise argparse.ArgumentTypeError("must not be empty")
    if any(char.isspace() for char in value):
        raise argparse.ArgumentTypeError("must not contain whitespace")
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
        description="Build tool for Grml(-based) Linux Live-ISOs",
        epilog="""
Usage examples:

  %(prog)s
  %(prog)s -c GRML_FULL -o /dev/shm/grml
  %(prog)s -c GRML_FULL -i grml_0.0-1.iso -v 0.0-1
  %(prog)s -c GRML_FULL -s stable -r 'grml-ftw'

More details:

  man grml-live
  /usr/share/doc/grml-live/grml-live.html
  http://grml.org/grml-live/

Please send your bug reports and feedback to the grml-team: http://grml.org/bugs/
""",
    )

    parser.add_argument(
        "--boot-options", type=str, dest="default_bootoptions", default="", help="Add these boot options"
    )
    parser.add_argument(
        "-c",
        type=arg_key_str,
        dest="classes",
        metavar="CLASS1,CLASS2",
        default="GRML_FULL",
        help="classes to be used for building the ISO",
    )

    parser.add_argument(
        "--distri-info",
        type=str,
        dest="distri_info",
        default="Grml - Live Linux for system administrators",
        help="Set DISTRI_INFO",
    )
    parser.add_argument("--distri-name", type=arg_key_str, dest="distri_name", default="grml", help="Set DISTRI_NAME")
    parser.add_argument("--hostname", type=arg_key_str, dest="hostname", default="grml", help="Set HOSTNAME")
    parser.add_argument("--username", type=arg_key_str, dest="username", default="grml", help="Set USERNAME")

    parser.add_argument(
        "-d",
        type=arg_key_str,
        dest="date",
        default=str(source_date_epoch_dt.strftime("%Y-%m-%d")),
        metavar="DATE",
        help="use specified date instead of build time as date of release",
    )
    parser.add_argument(
        "-D",
        type=arg_absolute_path,
        dest="config_dir",
        metavar="CONFIGDIR",
        default=default_paths.config_dir,
        help="use specified configuration directory",
    )
    parser.add_argument(
        "-e",
        type=arg_absolute_path,
        dest="extract_iso_name",
        metavar="EXTRACT_ISO_NAME",
        help="extract ISO and squashfs contents from iso_name",
    )
    parser.add_argument("-F", action="store_true", dest="force", help="force execution without prompting")
    parser.add_argument(
        "-g",
        type=arg_key_str,
        dest="grml_name",
        metavar="GRML_NAME",
        default="grml",
        help="set the grml flavour name",
    )
    parser.add_argument(
        "-i",
        type=arg_key_str,
        dest="iso_name",
        metavar="ISO_NAME",
        help="set the name of the resulting ISO (and other build results)",
    )
    parser.add_argument(
        "-I",
        type=arg_absolute_path,
        dest="chroot_install_src_directory",
        metavar="CHROOT_INSTALL_DIRECTORY",
        help="directory which provides files that should become part of the chroot/ISO",
    )
    parser.add_argument(
        "-o",
        type=arg_absolute_path,
        dest="output_directory",
        metavar="OUTPUT_DIRECTORY",
        default=str(Path.cwd() / "grml"),
        help="main output directory of the build process",
    )
    parser.add_argument(
        "-r",
        type=str,
        dest="release_name",
        metavar="RELEASE_NAME",
        default="grml-live rocks",
        help="set the grml release name",
    )
    parser.add_argument(
        "-R",
        dest="is_release",
        action="store_false",
        default=True,
        help="skip applying the RELEASE class and cleanup",
    )
    parser.add_argument(
        "-s",
        type=arg_key_str,
        dest="debian_suite",
        metavar="SUITE",
        default="testing",
        help="Debian suite/release, like: stable, testing, unstable",
    )
    parser.add_argument("--secure-boot", action="store_true", help="Enable Secure Boot using Debian method")
    parser.add_argument(
        "-v",
        type=arg_key_str,
        dest="grml_version",
        metavar="VERSION_NUMBER",
        default="0.0.1",
        help="set the grml version number",
    )

    mirror_options = parser.add_mutually_exclusive_group()
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
        help="wayback machine, build system using Debian archives from specified date",
    )

    build_type_options = parser.add_argument_group("build mode (expert only)").add_mutually_exclusive_group()
    parser.set_defaults(fai_action=build_facts.FaiAction.DIRINSTALL)
    build_type_options.add_argument(
        "-b",
        action="store_const",
        dest="fai_action",
        const=build_facts.FaiAction.RECONFIGURE,
        help="build from an existing chroot",
    )
    build_type_options.add_argument(
        "-B",
        action="store_const",
        dest="fai_action",
        const=build_facts.FaiAction.REBUILD,
        help="build from an existing chroot without running scripts",
    )
    build_type_options.add_argument(
        "-u",
        action="store_const",
        dest="fai_action",
        const=build_facts.FaiAction.SOFTUPDATE,
        help="update and build from an existing chroot",
    )
    build_type_options.add_argument(
        "-q", action="store_const", dest="fai_action", const=build_facts.FaiAction.REBUILD_MEDIA, help="skip mksquashfs"
    )

    return parser


def show_build_config(build_config: build_facts.BuildConfiguration):
    print(f"""grml-live [{build_config.grml_live_version}] Build Configuration:

    SOURCE_DATE_EPOCH: {build_config.source_date_epoch}
    FAI classes:       {",".join(build_config.classes)}
    Debian suite:      {build_config.debian_suite}
    Bootstrap mirror:  {build_config.bootstrap_mirror_url}
    Wayback date:      {build_config.wayback_date}
    Architecture:      {build_config.arch}
    Output directory:  {build_config.output_directory}""")
    if build_config.fai_action != build_facts.FaiAction.DIRINSTALL:
        print(f"    Build mode:        {build_config.fai_action}")

    print(f"""\n  Input files:
    Config Space:      {build_config.config_dir}""")
    if build_config.extract_iso_name:
        print(f"    Extract ISO:       {build_config.extract_iso_name}")

    print(f"""\n  Output identification:
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


def _main(argv: list[str]) -> int:
    global VERSION
    VERSION = os.getenv("GRML_LIVE_VERSION", "?")
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
    if args.fai_action in (build_facts.FaiAction.REBUILD, build_facts.FaiAction.REBUILD_MEDIA) and args.is_release:
        print("I: turning off release build treatments")
        args.is_release = False

    # after parse_args, so parse_args can handle --help.
    if os.geteuid() == 0:
        print("E: grml-live needs to run as non-root with working user namespaces", file=sys.stderr)
        return 1
    if source_date_epoch_error:
        print(f"E: {source_date_epoch_error}", file=sys.stderr)
        return 1

    try:
        builder_programs = resolve_programs(build_facts.BuilderPrograms)
        if args.extract_iso_name:
            extract_programs = resolve_programs(build_facts.ExtractPrograms)
        else:
            extract_programs = None
    except ValueError as except_inst:
        print(f"E: {except_inst!s}", file=sys.stderr)
        return 1

    arch = dpkg_architecture(builder_programs)
    if arch not in build_facts.SUPPORTED_ARCHS:
        print(f"E: dpkg architecture {arch!s} not supported.", file=sys.stderr)
        return 1

    short_name = strip_unsafe_chars(args.grml_name)

    bootstrap_mirror_url = args.bootstrap_mirror_url
    if args.wayback_date:
        bootstrap_mirror_url = f"http://snapshot.debian.org/archive/debian/{args.wayback_date}/"

    iso_name = args.iso_name
    if not iso_name:
        iso_name = f"{args.grml_name}_{args.grml_version}.iso"

    try:
        classes = automatic_classes(args.classes, arch, args.debian_suite, args.is_release, args.secure_boot)
    except ValueError as except_inst:
        print(f"E: {except_inst}", file=sys.stderr)
        return 1

    # Once build_config exists, avoid reading anything directly from `args`.
    build_config = build_facts.BuildConfiguration(
        grml_live_version=VERSION,
        cmdline=argv,
        fai_action=args.fai_action,
        arch=arch,
        builder_programs=builder_programs,
        classes=classes,
        config_dir=args.config_dir,
        output_directory=args.output_directory,
        grml_cd_dir=args.output_directory / "grml_cd",
        grml_chroot_dir=args.output_directory / "grml_chroot",
        grml_logs_dir=args.output_directory / "grml_logs",
        extract_iso_name=args.extract_iso_name,
        extract_programs=extract_programs,
        distri_name=args.distri_name,
        distri_info=args.distri_info,
        grml_name=args.grml_name,
        short_name=short_name,
        grml_version=args.grml_version,
        iso_name=iso_name,
        release_name=args.release_name,
        release_info=f"{args.grml_name} {args.grml_version} - Release Codename {args.release_name}",
        hostname=args.hostname,
        username=args.username,
        squashfs_name=f"{args.grml_name}.squashfs",
        boot_file=f"/conf/bootfile_{short_name}_{source_date_epoch}",
        is_release=args.is_release,
        date=args.date,
        source_date_epoch=source_date_epoch,
        wayback_date=args.wayback_date,
        debian_suite=args.debian_suite,
        bootstrap_mirror_url=bootstrap_mirror_url,
        secure_boot=args.secure_boot,
        chroot_install_src_directory=args.chroot_install_src_directory,
        bootid=strip_unsafe_chars(f"{args.grml_name}{args.grml_version}"),
        default_bootoptions=args.default_bootoptions,
    )

    if not build_config.config_dir.exists():
        print(
            f"E: Config directory {build_config.config_dir!s} does not exist. Set -D to a valid config directory.",
            file=sys.stderr,
        )
        return 1

    try:
        file_ops.check_dir_usable_for_unshare(build_config.config_dir)
        file_ops.check_dir_usable_for_unshare(build_config.output_directory, missing_ok=True)
        if build_config.chroot_install_src_directory:
            file_ops.check_dir_usable_for_unshare(build_config.chroot_install_src_directory)
    except ValueError as except_inst:
        print(f"E: {except_inst}", file=sys.stderr)
        return 1

    if not args.force:
        show_build_config(build_config)

    # Warnings go after build config printing, but before confirmation.
    if not (build_config.config_dir / "media-files" / "GRMLBASE" / "addons" / "arch").exists():
        print('W: Boot addons not found. Consider installing package "grml-live-addons".')

    if "NO_ONLINE" not in build_config.classes:
        print('W: Class "NO_ONLINE" NOT requested. Output will NOT be reproducible.')

    # Last minute checks before confirmation.
    chroot_os_release = Path(build_config.grml_chroot_dir / "etc" / "os-release")
    if build_config.fai_action == build_facts.FaiAction.DIRINSTALL:
        if chroot_os_release.exists():
            print("E: the chroot already exists. Refusing to overwrite it. (Add -u/-b/-B option?)", file=sys.stderr)
            return 20
        if build_config.extract_iso_name:
            print("E: using an existing ISO precludes building a new chroot. (Add -u/-b/-B option?)", file=sys.stderr)
            return 20
    elif not build_config.extract_iso_name and not chroot_os_release.exists():
        print(
            "E: does not look like you have a working chroot. Updating/building not possible. (Drop -u/-b/-B option?)",
            file=sys.stderr,
        )
        return 20
    elif build_config.extract_iso_name and chroot_os_release.exists():
        print(
            "E: the chroot already exists. Refusing to overwrite it by extracting an ISO. (Remove -e option?)",
            file=sys.stderr,
        )
        return 20

    if not args.force:
        print()
        try:
            prompt_result = input("Check the build settings. (Use -F to skip this prompt.)\nContinue? [y/N] ")
        except EOFError:
            prompt_result = ""
            print("E: EOF received", file=sys.stderr)
        if prompt_result.strip().upper() != "Y":
            print("Exiting as requested.")
            return 1

    # Now run the build.
    # Create grml_logs_dir (and its parent) first, so we can write the log!
    file_ops.create_dir_useable_for_unshare(build_config.grml_logs_dir)
    logfile = build_config.grml_logs_dir / "grml-live.log"

    print(f"\nI: Starting build, writing log to {logfile}.\n")
    with logkit.tee_output_to(logfile):
        print(f"I: grml-live command line: {' '.join(build_config.cmdline)}")
        print(f"I: grml-live started at: {startup_dt}")
        # write configuration into log
        show_build_config(build_config)
        os.environ["SOURCE_DATE_EPOCH"] = str(source_date_epoch)

        with timing.log_elapsed_time("Build run"):
            try:
                rc = minifai.build(build_config)
            except KeyboardInterrupt as except_inst:
                rc = 130
                print(f"E: build aborted: {except_inst}", file=sys.stderr)
            except BaseException as except_inst:
                # Need BaseException to catch all exceptions, so they end up in the log
                rc = 1
                print(f"E: build failed with unhandled exception: {except_inst}", file=sys.stderr)
                traceback.print_exc()

        if rc == 0:
            print("Successfully finished execution.")
        else:
            # Write final status to both stdout and stderr
            print(f"E: Execution failed with rc={rc}", file=sys.stderr)
            print(f"E: Execution failed with rc={rc}")

    return rc


def main() -> int:
    return _main(sys.argv)


if __name__ == "__main__":
    sys.exit(main())
