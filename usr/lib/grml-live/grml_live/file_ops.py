import itertools
import os
import stat
from pathlib import Path


def _self_and_parents(path: Path) -> tuple[Path, ...]:
    """path followed by all of its parents, deepest first."""
    return (path, *path.parents)


def check_dir_usable_for_unshare(path: Path, missing_ok: bool = False):
    if not missing_ok and not path.is_dir():
        raise ValueError(f"Directory {path} does not exist")
    for p in _self_and_parents(path):
        try:
            mode = p.stat().st_mode
        except FileNotFoundError:
            continue
        if not mode & stat.S_IXOTH:
            where = f"{p}" if p == path else f"{p} (parent of {path})"
            raise ValueError(f"Directory {where} must be world-executable")


def create_dir_useable_for_unshare(path: Path):
    for p in reversed(_self_and_parents(path)):
        if not p.exists():
            p.mkdir()
            p.chmod(p.stat().st_mode | stat.S_IXOTH)
    check_dir_usable_for_unshare(path)


def clamp_to_source_date_epoch(root_dir: Path | str):
    source_date_epoch = os.environ["SOURCE_DATE_EPOCH"]
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
