import datetime
from pathlib import Path

import pytest

from .. import build_facts, minifai


@pytest.fixture
def sample_build_config():
    builder_programs = build_facts.BuilderPrograms(
        dpkg=Path("/usr/bin/dpkg"),
        mksquashfs=Path("/usr/bin/mksquashfs"),
        mmdebstrap=Path("/usr/bin/mmdebstrap"),
        xorriso=Path("/usr/bin/xorriso"),
    )
    work_directory = Path("/invalid/work_dir")
    output_directory = Path("/invalid/output_dir")
    grml_name = "testgrml"
    return build_facts.BuildConfiguration(
        grml_live_version="VERSION",
        cmdline=["grml-live"],
        fai_action=build_facts.FaiAction.DIRINSTALL,
        grml_live_action=build_facts.GrmlLiveAction.IMAGE_CREATE,
        arch="amd64",
        builder_programs=builder_programs,
        classes=["GRML_SMALL"],
        config_dir=Path("/invalid/config_dir"),
        output_directory=output_directory,
        work_directory=work_directory,
        grml_cd_dir=work_directory / "grml_cd",
        grml_cd_live_dir=work_directory / "grml_cd" / "live",
        grml_cd_squashfs_dir=work_directory / "grml_cd" / "live" / grml_name,
        grml_cd_squashfs_name=work_directory / "grml_cd" / "live" / grml_name / f"{grml_name}.squashfs",
        grml_chroot_dir=work_directory / "grml_chroot",
        grml_isos_dir=output_directory / "grml_isos",
        grml_logs_dir=output_directory / "grml_logs",
        source_image=None,
        extract_programs=None,
        distri_name=grml_name,
        distri_info="a totally valid distri",
        grml_name=grml_name,
        short_name=grml_name,
        grml_version="0.9.9",
        iso_name=f"{grml_name}_test.iso",
        iso_volid=f"{grml_name}_test",
        release_name=grml_name,
        release_info=f"{grml_name} 0.9.9 - Release Codename PYTEST",
        hostname="grml",
        username="grml",
        squashfs_name=f"{grml_name}.squashfs",
        boot_file=f"/conf/bootfile_{grml_name}_1234",
        is_release=True,
        date=datetime.date.today(),
        source_date_epoch=1234,
        wayback_date=None,
        debian_suite="unstable",
        bootstrap_mirror_url="http://deb.debian.org/debian/",
        secure_boot=False,
        chroot_install_src_directory=None,
        bootid=f"{grml_name}099",
        default_bootoptions="",
    )


def test__build_xorriso_cmdline(sample_build_config):
    assert minifai._build_xorriso_cmdline(sample_build_config) == [
        "/usr/bin/xorriso",
        "-as",
        "mkisofs",
        "-V",
        "testgrml_test",
        "-publisher",
        "grml-live | grml.org",
        "-l",
        "-r",
        "-J",
        "-b",
        "boot/grub/i386-pc/eltorito.img",
        "-no-emul-boot",
        "-boot-load-size",
        "4",
        "-boot-info-table",
        "--grub2-boot-info",
        "--grub2-mbr",
        "/invalid/work_dir/grml_cd/boot/grub/i386-pc/boot_hybrid.img",
        "-eltorito-alt-boot",
        "-e",
        "boot/efi.img",
        "-no-emul-boot",
        "-isohybrid-gpt-basdat",
        "-o",
        "/invalid/output_dir/grml_isos/testgrml_test.iso",
        "/invalid/work_dir/grml_cd/",
    ]
