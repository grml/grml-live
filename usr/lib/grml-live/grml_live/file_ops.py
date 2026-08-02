import itertools
import os
from pathlib import Path


def check_dir_usable_for_unshare(path: Path):
    if not path.exists():
        raise ValueError(f"Directory {path} does not exist")
    p = path
    while True:
        if not p.stat().st_mode & os.X_OK:
            raise ValueError(f"Directory {p} (parent of {path}) must be world-executable")
        if p == Path("/"):
            break
        p = p.parent


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
