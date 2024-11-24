#!/usr/bin/env python3
import os
import subprocess
import sys
import re
from dataclasses import dataclass, field
from pathlib import Path


SECTION_SEPARATOR = f"{'-' * 72}\n"


@dataclass
class GitPackageChanges:
    package: str
    range: str
    old_version: str | None
    git_changes: list[str]


@dataclass
class Changes:
    # These are single items per package.
    debian_packages_removed: list[str] = field(default_factory=list)
    debian_packages_added: list[str] = field(default_factory=list)
    debian_packages_changed: list[str] = field(default_factory=list)
    our_packages_removed: list[str] = field(default_factory=list)
    # This contains tuples.
    our_packages_changed: list[GitPackageChanges] = field(default_factory=list)


class Listener:
    def __init__(self):
        self.failed = False

    def error(self, message: str):
        raise NotImplementedError

    def info(self, message: str):
        raise NotImplementedError

    def warn(self, message: str):
        raise NotImplementedError


class CliListener(Listener):
    def error(self, message: str):
        self.failed = True
        sys.stderr.write(f"E: {message}\n")

    def info(self, message: str):
        sys.stdout.write(f"I: {message}\n")

    def warn(self, message: str):
        sys.stdout.write(f"W: {message}\n")


def parse_package_list(s: str) -> dict[str, str]:
    """Returned dictionary is dict[package: str, version: str]."""
    package_dict = {}
    for line in s.split("\n"):
        match = re.match(r"^ii\s+(\S+)\s+(\S+)\s", line)
        if match:
            package_dict[match[1]] = match[2]
    return package_dict


def git_repo_clone_and_update(local_git_path: Path, remote_url: str):
    # Disable any input prompting from git.
    env = dict(os.environ) | {"GIT_TERMINAL_PROMPT": "0"}

    if not local_git_path.exists():
        git_command = ["git", "clone", "--bare", "--single-branch", remote_url, str(local_git_path)]
        subprocess.run(git_command, env=env)
        if not local_git_path.exists():
            raise Exception("Repository not found after git clone")

    # update repo, in case it existed already (cache).
    subprocess.run(
        ["git", "remote", "set-url", "origin", remote_url],
        cwd=local_git_path,
        env=env,
    )
    subprocess.run(
        ["git", "remote", "update", "--prune"],
        cwd=local_git_path,
        env=env,
    ).check_returncode()


def git_get_changes(local_git_path: Path, range) -> list[str]:
    """Get git log --online output. On failure, None is returned."""

    result = subprocess.run(
        ["git", "log", "--oneline", range],
        cwd=local_git_path,
        capture_output=True,
    )

    if result.returncode != 0:
        git_changes = []
    else:
        git_changes = result.stdout.decode().splitlines()

    return git_changes


def generate_git_package_changes(
    package: str, old_version: str | None, version: str, git_url_base: str, git_repo_workspace: Path, listener: Listener
) -> GitPackageChanges | None:
    """Generate changelog for a package that we believe is in our git."""

    listener.info(f"Generating changes list for package {package}, Version {old_version} -> {version}")

    try:
        # clone repo
        git_url = f"{git_url_base}/{package}"
        gitpath = git_repo_workspace / f"{package}.git"
        git_repo_clone_and_update(gitpath, git_url)

        if old_version:
            range = f"v{old_version}..v{version}"
        else:
            range = f"v{version}"

        git_changes = git_get_changes(gitpath, range)

        return GitPackageChanges(package, range, old_version, git_changes)
    except Exception as e:
        listener.warn(f"Generating change report for package {package} failed: {e}")
        return None


def collect_changes(
    dpkg_list_new: Path,
    dpkg_list_old: Path,
    package_prefix: str,
    git_url_base: str,
    git_repo_workspace: Path,
    listener: Listener,
) -> Changes | None:
    git_repo_workspace.mkdir(parents=True, exist_ok=True)

    if not dpkg_list_new.exists():
        listener.error(f"Could not read package list {dpkg_list_new}")
        return None

    packages = parse_package_list(dpkg_list_new.read_text())
    packages_old = {}
    try:
        packages_old = parse_package_list(dpkg_list_old.read_text())
    except Exception as e:
        listener.info(f"While parsing old package list: {e}")

    # These are single items per package.
    changes = Changes()

    # Process removed packages first.
    for package in set(packages_old) - set(packages):
        if re.match(f"^{package_prefix}", package):
            changes.our_packages_removed.append(package)
        else:
            changes.debian_packages_removed.append(package)

    # Process changed and added packages.
    for package, version in packages.items():
        old_version = packages_old.get(package)
        if old_version and old_version == version:
            continue  # version did not change, do not add to changelog.

        if re.match(f"^{package_prefix}", package):
            change = generate_git_package_changes(
                package, old_version, version, git_url_base, git_repo_workspace, listener
            )
            if change:
                changes.our_packages_changed.append(change)
        else:
            # Debian-originated package, just show versions
            if old_version:
                changes.debian_packages_changed.append(f"{package} {old_version} -> {version}")
            else:
                changes.debian_packages_added.append(f"{package} {version}")

    return changes


def format_changelog(
    job_name: str,
    build_id: str,
    changes: Changes,
) -> str:
    def changes_to_lines(changes):
        return "\n    ".join(changes).strip()

    changelog_parts = [
        SECTION_SEPARATOR,
        f"Generated by CI for job {job_name} {build_id}\n",
        SECTION_SEPARATOR,
    ]

    for package in changes.our_packages_removed:
        changelog_parts += [
            f"Package {package}: Removed.\n",
            SECTION_SEPARATOR,
        ]

    for change in changes.our_packages_changed:
        if change.git_changes:
            changes_formatted = changes_to_lines(change.git_changes)
        else:
            changes_formatted = "(failed)"

        changelog_parts += [
            f"Package {change.package}: {change.range} {'(new)' if not change.old_version else ''}\n",
            f"    {changes_formatted}\n",
            SECTION_SEPARATOR,
        ]

    changelog_parts += [
        "Changes to Debian package list:\n",
        "  Added:\n",
        f"    {changes_to_lines(changes.debian_packages_added)}\n",
        "  Changed:\n",
        f"    {changes_to_lines(changes.debian_packages_changed)}\n",
        "  Removed:\n",
        f"    {changes_to_lines(changes.debian_packages_removed)}\n",
        SECTION_SEPARATOR,
    ]

    return "".join(changelog_parts)


def main() -> int:
    if len(sys.argv) != 9:
        print(
            f"Usage: {sys.argv[0]} output_filename dpkg_list_new dpkg_list_old package_prefix git_url_base git_repo_workspace job_name build_id"
        )
        return 2

    listener = CliListener()
    output_filename = Path(sys.argv[1])

    changes = collect_changes(
        Path(sys.argv[2]), Path(sys.argv[3]), sys.argv[4], sys.argv[5], Path(sys.argv[6]), listener
    )
    if changes is not None:
        text = format_changelog(sys.argv[7], sys.argv[8], changes)
        output_filename.write_text(text)
    else:
        listener.error("Failed to collect changes")

    if listener.failed:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
