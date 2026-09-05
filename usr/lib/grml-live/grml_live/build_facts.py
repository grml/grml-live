from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

SUPPORTED_ARCHS = ["amd64", "arm64"]


@dataclass(kw_only=True, frozen=True)
class BuilderPrograms:
    dpkg: Path
    mksquashfs: Path
    mmdebstrap: Path
    xorriso: Path


@dataclass(kw_only=True, frozen=True)
class ExtractPrograms:
    osirrox: Path
    unsquashfs: Path


class FaiAction(StrEnum):
    DIRINSTALL = "dirinstall"
    SOFTUPDATE = "softupdate"
    RECONFIGURE = "reconfigure"
    REBUILD = "rebuild"
    REBUILD_MEDIA = "rebuild_media"


class GrmlLiveAction(StrEnum):
    # Further actions will be provided later.
    IMAGE_CREATE = "image-create"
    IMAGE_UPDATE = "image-update"


@dataclass(kw_only=True, frozen=True)
class BuildConfiguration:
    grml_live_version: str
    cmdline: list[str]
    fai_action: FaiAction
    grml_live_action: GrmlLiveAction
    arch: str
    builder_programs: BuilderPrograms
    classes: list[str]
    config_dir: Path
    output_directory: Path
    work_directory: Path
    grml_cd_dir: Path
    grml_cd_live_dir: Path
    grml_cd_squashfs_dir: Path
    grml_cd_squashfs_name: Path
    grml_chroot_dir: Path
    grml_isos_dir: Path
    grml_logs_dir: Path
    source_image: Path | None
    extract_programs: ExtractPrograms | None
    distri_name: str
    distri_info: str
    grml_name: str
    short_name: str
    grml_version: str
    iso_name: str
    iso_volid: str
    release_name: str
    release_info: str
    hostname: str
    username: str
    squashfs_name: str
    boot_file: str
    is_release: bool
    date: str
    source_date_epoch: int | None
    wayback_date: str | None
    debian_suite: str
    bootstrap_mirror_url: str | None
    secure_boot: bool
    chroot_install_src_directory: Path | None
    bootid: str
    default_bootoptions: str
