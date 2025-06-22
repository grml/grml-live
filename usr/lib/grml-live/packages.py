#!/usr/bin/env python3
#
# Package list handling for grml-live minifai
#

from pathlib import Path


class ClassFileParsingFailed(Exception):
    pass


class PackageList(dict):
    def list_for_arch(self, arch: str):
        return self.list_of_arch("all") | self.list_of_arch(arch)

    def list_of_arch(self, arch: str):
        return set(self.get(arch, []))

    def as_apt_params(self, *, restrict_to_arch: str) -> list[str]:
        full_list = []
        for arch, packages in self.items():
            if arch == "all":
                full_list += packages
            else:
                if arch != restrict_to_arch:
                    continue
                full_list += [f"{package}" for package in packages]
        return full_list

    def merge(self, other) -> None:
        for arch, packages in other.items():
            self.setdefault(arch, [])
            self[arch] = list(set(self[arch] + packages))


def parse_class_packages(conf_dir: Path, class_name: str) -> PackageList:
    """Parse FAI package_config for class class_name."""

    packagelist = conf_dir / "package_config" / class_name
    if not packagelist.exists():
        return PackageList({})

    print(f"I: Parsing {packagelist}")

    arch = "all"
    packages = []
    parsed = PackageList({})
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
            if parts[1] != "install":
                raise ValueError(f"package class file {packagelist} PACKAGES line not understood: {line!r}")

            # save previously parsed packages
            parsed.setdefault(arch, [])
            parsed[arch] += packages

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

    parsed.setdefault(arch, [])
    parsed[arch] += packages
    return parsed
