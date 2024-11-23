#!/usr/bin/env python3
import paramiko
import pathlib
import sys
from stat import S_ISDIR


def sftp_isdir(sftp, path: str):
    try:
        return S_ISDIR(sftp.stat(path).st_mode)
    except IOError:
        return False


def sftp_rm_r(sftp, remote_dir: str):
    files = sftp.listdir(remote_dir)
    remote_path = pathlib.Path(remote_dir)

    for f in files:
        filepath = (remote_path / f).as_posix()
        if sftp_isdir(sftp, filepath):
            sftp_rm_r(sftp, filepath)
        else:
            sftp.remove(filepath)

    sftp.rmdir(remote_dir)


def upload_dir(sftp, local_dir: pathlib.Path, remote_dir: str):
    remote_root = pathlib.Path(remote_dir)
    seen = set()
    for local_path in local_dir.rglob("*"):
        if not local_path.is_file():
            continue

        relative_path = local_path.relative_to(local_dir)
        remote_path = remote_root / relative_path

        for parent in reversed(remote_path.parents):
            parent = parent.as_posix()
            if parent in seen:
                continue
            try:
                sftp.stat(parent)
            except FileNotFoundError:
                sftp.mkdir(parent)
            seen.add(parent)

        print("Uploading", local_path, "to", remote_path)
        sftp.put(local_path.as_posix(), remote_path.as_posix())


def main():
    keyfile = sys.argv[1]
    # user@remote.host:/grml64-small_sid
    remote_site_and_path = sys.argv[2]
    # /tmp/builddir
    local_dir = pathlib.Path(sys.argv[3])
    # grml64-small_sid
    job_name = sys.argv[4]
    # 2024-11-09_01_31_01
    stamped_dirname = sys.argv[5]

    remote_site = remote_site_and_path.split(":")[0]
    remote_path = remote_site_and_path.split(":")[1]
    remote_host = remote_site.split("@")[1]
    remote_user = remote_site.split("@")[0]

    pkey = paramiko.Ed25519Key.from_private_key_file(keyfile)

    transport = paramiko.Transport((remote_host, 22))
    transport.connect(username=remote_user, pkey=pkey)

    sftp = paramiko.SFTPClient.from_transport(transport)
    assert sftp is not None

    versions = [path for path in sorted(sftp.listdir(remote_path)) if not path.endswith("/latest")]
    for version in versions[:-14]:
        print("Removing old version", version)
        sftp_rm_r(sftp, f"{remote_path}/{version}")

    remote_stamped = f"{remote_path}/{stamped_dirname}"
    upload_dir(sftp, local_dir, remote_stamped)

    remote_latest = f"{remote_path}/latest"
    try:
        sftp.mkdir(remote_latest)
    except IOError:
        pass

    real_iso_name = next(local_dir.glob("grml_isos/*iso")).name
    real_checksum_name = next(local_dir.glob("grml_isos/*iso.sha256")).name
    latest_iso_name = f"{job_name}_latest.iso"
    latest_checksum_name = f"{job_name}_latest.iso.sha256"

    for symlink, real in [
        (latest_iso_name, real_iso_name),
        (latest_checksum_name, real_checksum_name),
    ]:
        remote_symlink = f"{remote_latest}/{symlink}"
        remote_real = f"../{stamped_dirname}/grml_isos/{real}"
        print("Updating symlink", remote_symlink, "to", remote_real)
        try:
            sftp.unlink(remote_symlink)
        except FileNotFoundError:
            pass
        sftp.symlink(remote_real, remote_symlink)

    sftp.close()
    transport.close()


if __name__ == "__main__":
    main()
