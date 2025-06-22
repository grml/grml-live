# package_config parser and data structure

from pathlib import Path


class ClassFileParsingFailed(Exception):
    pass


class PackageList:
    def __init__(self, to_install=None, to_skip=None):
        self.to_install = to_install or {}
        self.to_skip = to_skip or {}

    def list_for_arch(self, arch: str):
        return self.list_of_arch("all") | self.list_of_arch(arch)

    def list_of_arch(self, arch: str):
        return set(self.to_install.get(arch, []))

    def skip_list_for_arch(self, arch: str):
        return self.skip_list_of_arch("all") | self.skip_list_of_arch(arch)

    def skip_list_of_arch(self, arch: str):
        return set(self.to_skip.get(arch, []))

    def as_apt_params(self, *, restrict_to_arch: str, exclude_from: "PackageList" = None) -> list[str]:
        """
        Get apt install parameters for the given architecture.

        Args:
            restrict_to_arch: Only include packages for this architecture and 'all'
            exclude_from: Optional PackageList to exclude packages from (uses skip_list_for_arch)
        """
        exclude_set = set()
        if exclude_from:
            exclude_set = exclude_from.skip_list_for_arch(restrict_to_arch)

        full_list = []
        for arch, packages in self.to_install.items():
            if arch == "all":
                full_list += [pkg for pkg in packages if pkg not in exclude_set]
            else:
                if arch != restrict_to_arch:
                    continue
                full_list += [pkg for pkg in packages if pkg not in exclude_set]
        return full_list

    def merge(self, other) -> None:
        """
        Merge another PackageList, where the later class decisions override earlier ones.
        This means:
        - If other.to_install has a package, it overrides any existing skip for that package
        - If other.to_skip has a package, it overrides any existing install for that package
        """
        # First handle install directives - they override existing skips
        for arch, packages in other.to_install.items():
            self.to_install.setdefault(arch, [])
            self.to_install[arch] = list(set(self.to_install[arch] + packages))

            # Remove these packages from skip lists (install overrides skip)
            for pkg in packages:
                if arch in self.to_skip and pkg in self.to_skip[arch]:
                    self.to_skip[arch].remove(pkg)
                if "all" in self.to_skip and pkg in self.to_skip["all"]:
                    self.to_skip["all"].remove(pkg)

        # Then handle skip directives - they override existing installs
        for arch, packages in other.to_skip.items():
            self.to_skip.setdefault(arch, [])
            for pkg in packages:
                # Add to skip list
                if pkg not in self.to_skip[arch]:
                    self.to_skip[arch].append(pkg)

                # Remove from install lists (skip overrides install)
                # Remove from the same architecture
                if arch in self.to_install and pkg in self.to_install[arch]:
                    self.to_install[arch].remove(pkg)
                if "all" in self.to_install and pkg in self.to_install["all"]:
                    self.to_install["all"].remove(pkg)

                # If this is a global skip (arch="all"), remove from all architecture-specific install lists
                if arch == "all":
                    for install_arch in list(self.to_install.keys()):
                        if install_arch != "all" and pkg in self.to_install[install_arch]:
                            self.to_install[install_arch].remove(pkg)

    def prune_skipped_packages(self, arch: str) -> None:
        """Remove packages marked for skipping from the install list for given architecture."""
        skip_set = self.skip_list_for_arch(arch)

        for package_arch in self.to_install:
            if package_arch == "all" or package_arch == arch:
                self.to_install[package_arch] = [pkg for pkg in self.to_install[package_arch] if pkg not in skip_set]


def parse_class_packages(conf_dir: Path, class_name: str) -> PackageList:
    """Parse FAI package_config for class class_name."""

    packagelist = conf_dir / "package_config" / class_name
    if not packagelist.exists():
        return PackageList()

    print(f"I: Parsing {packagelist}")

    arch = "all"
    packages = []
    mode = "install"  # Track whether we're in install or skip mode
    parsed = PackageList()

    for line in packagelist.read_text().splitlines():
        parts = line.split()

        for index, part in enumerate(parts):
            if part.startswith("#"):
                parts = parts[0:index]
                break

        if not parts:
            continue

        if parts[0] == "PACKAGES":
            # section header
            if len(parts) not in (2, 3):
                raise ValueError(f"package class file {packagelist} has invalid PACKAGES line: {line!r}")
            if parts[1] not in ("install", "skip"):
                raise ValueError(f"package class file {packagelist} PACKAGES line not understood: {line!r}")

            # save previously parsed packages
            if mode == "install":
                parsed.to_install.setdefault(arch, [])
                parsed.to_install[arch] += packages
            elif mode == "skip":
                parsed.to_skip.setdefault(arch, [])
                parsed.to_skip[arch] += packages

            mode = parts[1]
            if len(parts) == 3:
                arch = parts[2].lower()
            else:
                arch = "all"
            packages = []
            continue

        else:
            for part in parts:
                if part:
                    packages.append(part)

    # save the last section's packages
    if mode == "install":
        parsed.to_install.setdefault(arch, [])
        parsed.to_install[arch] += packages
    elif mode == "skip":
        parsed.to_skip.setdefault(arch, [])
        parsed.to_skip[arch] += packages

    return parsed
