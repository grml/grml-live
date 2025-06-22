"""
Compact tests for the packages module with full coverage.
"""

import pytest
from pathlib import Path
from packages import PackageList, parse_class_packages, ClassFileParsingFailed


@pytest.fixture
def package_config_dir(tmp_path):
    """Create a temporary package_config directory."""
    config_dir = tmp_path / "package_config"
    config_dir.mkdir()
    return tmp_path, config_dir


def create_package_file(package_config_dir, class_name, content):
    """Helper to create a package config file."""
    package_file = package_config_dir / class_name
    package_file.write_text(content)
    return package_file


def test_packagelist_initialization_and_basic_methods():
    """Test PackageList initialization and basic access methods."""
    # Test empty initialization
    pl_empty = PackageList()
    assert pl_empty.to_install == {}
    assert pl_empty.to_skip == {}

    # Test initialization with data
    install_data = {"all": ["vim", "gcc"], "amd64": ["build-essential"]}
    skip_data = {"all": ["unwanted"], "amd64": ["old-pkg"]}
    pl = PackageList(install_data, skip_data)
    assert pl.to_install == install_data
    assert pl.to_skip == skip_data

    # Test list methods
    assert pl.list_of_arch("all") == {"vim", "gcc"}
    assert pl.list_of_arch("amd64") == {"build-essential"}
    assert pl.list_of_arch("i386") == set()

    # Test combined list (all + arch)
    assert pl.list_for_arch("amd64") == {"vim", "gcc", "build-essential"}
    assert pl.list_for_arch("i386") == {"vim", "gcc"}

    # Test skip methods
    assert pl.skip_list_of_arch("all") == {"unwanted"}
    assert pl.skip_list_of_arch("amd64") == {"old-pkg"}
    assert pl.skip_list_for_arch("amd64") == {"unwanted", "old-pkg"}
    assert pl.skip_list_for_arch("i386") == {"unwanted"}


@pytest.mark.parametrize(
    "arch,expected_packages",
    [
        ("amd64", {"vim", "gcc", "build-essential"}),
        ("i386", {"vim", "gcc", "gcc-multilib"}),
    ],
)
def test_packagelist_as_apt_params_basic(arch, expected_packages):
    """Test as_apt_params basic functionality for different architectures."""
    pl = PackageList({"all": ["vim", "gcc"], "amd64": ["build-essential"], "i386": ["gcc-multilib"]})

    params = pl.as_apt_params(restrict_to_arch=arch)
    assert set(params) == expected_packages


@pytest.mark.parametrize(
    "arch,expected_packages",
    [
        ("amd64", {"vim"}),  # gcc and build-essential excluded
        ("i386", {"vim", "gcc-multilib"}),  # only gcc excluded
    ],
)
def test_packagelist_as_apt_params_with_exclusions(arch, expected_packages):
    """Test as_apt_params with exclusions for different architectures."""
    pl = PackageList({"all": ["vim", "gcc"], "amd64": ["build-essential"], "i386": ["gcc-multilib"]})
    exclude_list = PackageList({}, {"all": ["gcc"], "amd64": ["build-essential"]})

    params = pl.as_apt_params(restrict_to_arch=arch, exclude_from=exclude_list)
    assert set(params) == expected_packages

    # Verify original is unchanged
    assert pl.to_install == {"all": ["vim", "gcc"], "amd64": ["build-essential"], "i386": ["gcc-multilib"]}


def test_packagelist_merge_scenarios():
    """Test merge method with various conflict scenarios."""
    # Test 1: Basic merge without conflicts + duplicate handling
    pl1 = PackageList({"all": ["vim"]}, {"all": ["unwanted"]})
    pl2 = PackageList({"amd64": ["gcc"]}, {"amd64": ["old"]})
    pl1.merge(pl2)
    assert set(pl1.to_install["all"]) == {"vim"}
    assert set(pl1.to_install["amd64"]) == {"gcc"}
    assert set(pl1.to_skip["all"]) == {"unwanted"}
    assert set(pl1.to_skip["amd64"]) == {"old"}

    # Test duplicate handling
    pl1b = PackageList({"all": ["vim"], "amd64": ["gcc"]})
    pl2b = PackageList({"all": ["vim"], "amd64": ["gcc"]})
    pl1b.merge(pl2b)
    assert pl1b.to_install["all"] == ["vim"]  # No duplicates
    assert pl1b.to_install["amd64"] == ["gcc"]

    # Test 2: Install overrides skip
    pl3 = PackageList({"all": ["vim"]}, {"all": ["gcc"]})
    pl4 = PackageList({"all": ["gcc"]}, {})
    pl3.merge(pl4)
    assert "gcc" in pl3.to_install["all"]
    assert "gcc" not in pl3.to_skip["all"]

    # Test 3: Skip overrides install
    pl5 = PackageList({"all": ["gcc"]}, {})
    pl6 = PackageList({}, {"all": ["gcc"]})
    pl5.merge(pl6)
    assert "gcc" not in pl5.to_install.get("all", [])
    assert "gcc" in pl5.to_skip["all"]

    # Test 4: Complex scenario with multiple packages and architectures
    pl7 = PackageList({"all": ["vim", "gcc"]}, {"all": ["make"]})
    pl8 = PackageList({"all": ["make", "git"], "amd64": ["build-essential"]}, {"all": ["gcc"], "amd64": ["old"]})
    pl7.merge(pl8)
    assert set(pl7.to_install["all"]) == {"vim", "make", "git"}
    assert set(pl7.to_install["amd64"]) == {"build-essential"}
    assert set(pl7.to_skip["all"]) == {"gcc"}
    assert set(pl7.to_skip["amd64"]) == {"old"}

    # Test 5: Architecture-specific override
    pl9 = PackageList({}, {"all": ["linux-image-amd64"]})
    pl10 = PackageList({"amd64": ["linux-image-amd64"]}, {})
    pl9.merge(pl10)
    assert "linux-image-amd64" in pl9.to_install["amd64"]
    assert "linux-image-amd64" not in pl9.to_skip.get("all", [])

    # Test 6: Skip removes from both arch-specific and "all" install lists
    pl11 = PackageList({"all": ["gcc"], "amd64": ["gcc"]}, {})
    pl12 = PackageList({}, {"amd64": ["gcc"]})
    pl11.merge(pl12)
    assert "gcc" not in pl11.to_install.get("all", [])  # Removed from "all"
    assert "gcc" not in pl11.to_install.get("amd64", [])  # Removed from "amd64"
    assert "gcc" in pl11.to_skip["amd64"]


def test_packagelist_merge_global_skip_overrides_arch_install():
    """Test that global skip removes packages from arch-specific install lists (GRML_GHACI_CLOUD scenario)."""
    # Simulate GRML_GHACI: installs linux-image-amd64 for AMD64
    ghaci = PackageList({"all": ["vim-tiny"], "amd64": ["linux-image-amd64"]}, {})

    # Simulate GRML_GHACI_CLOUD: skips linux-image-amd64 globally, installs cloud variant
    ghaci_cloud = PackageList({"amd64": ["linux-image-cloud-amd64"]}, {"all": ["linux-image-amd64"]})

    # Merge them
    ghaci.merge(ghaci_cloud)

    # linux-image-amd64 should be removed from amd64 install list due to global skip
    assert "linux-image-amd64" not in ghaci.to_install.get("amd64", [])
    assert "linux-image-cloud-amd64" in ghaci.to_install["amd64"]
    assert "linux-image-amd64" in ghaci.to_skip["all"]
    assert "vim-tiny" in ghaci.to_install["all"]

    # Final apt params should not include the skipped package
    install_list = ghaci.as_apt_params(restrict_to_arch="amd64")
    assert "linux-image-amd64" not in install_list
    assert "linux-image-cloud-amd64" in install_list
    assert "vim-tiny" in install_list


@pytest.mark.parametrize(
    "arch,expected_all,expected_arch_specific",
    [
        ("amd64", {"vim", "make"}, {"build-essential"}),  # gcc removed from all, gcc-doc from amd64
        ("i386", {"vim", "make"}, {"build-essential", "gcc-doc"}),  # gcc removed from all, amd64 unchanged
    ],
)
def test_packagelist_prune_skipped_packages(arch, expected_all, expected_arch_specific):
    """Test prune_skipped_packages method for different architectures."""
    pl = PackageList(
        {"all": ["vim", "gcc", "make"], "amd64": ["build-essential", "gcc-doc"]}, {"all": ["gcc"], "amd64": ["gcc-doc"]}
    )

    pl.prune_skipped_packages(arch)

    assert set(pl.to_install["all"]) == expected_all
    assert set(pl.to_install["amd64"]) == expected_arch_specific


def test_packagelist_prune_skipped_packages_cross_arch():
    """Test that prune_skipped_packages only affects the target architecture."""
    pl = PackageList(
        {"all": ["vim"], "amd64": ["gcc"], "i386": ["gcc"]},
        {"amd64": ["gcc"]},  # Only skip gcc for amd64
    )
    pl.prune_skipped_packages("amd64")
    assert pl.to_install["all"] == ["vim"]
    assert pl.to_install["amd64"] == []
    assert pl.to_install["i386"] == ["gcc"]  # Unchanged


def test_parse_class_packages_comprehensive(package_config_dir):
    """Test parsing package config files with all features."""
    conf_dir, pkg_config_dir = package_config_dir

    # Test 1: Non-existent file
    result = parse_class_packages(conf_dir, "NONEXISTENT")
    assert isinstance(result, PackageList)
    assert result.to_install == {}
    assert result.to_skip == {}

    # Test 2: Comprehensive config with installs, skips, comments, and multiple architectures
    create_package_file(
        pkg_config_dir,
        "COMPREHENSIVE",
        """# Configuration with everything
PACKAGES install
vim
git  # Version control

PACKAGES install amd64
gcc
build-essential

PACKAGES skip
unwanted-global
deprecated  # Old package

PACKAGES skip amd64
gcc-old

PACKAGES install i386
gcc-multilib
""",
    )

    result = parse_class_packages(conf_dir, "COMPREHENSIVE")
    assert isinstance(result, PackageList)
    assert set(result.to_install["all"]) == {"vim", "git"}
    assert set(result.to_install["amd64"]) == {"gcc", "build-essential"}
    assert set(result.to_install["i386"]) == {"gcc-multilib"}
    assert set(result.to_skip["all"]) == {"unwanted-global", "deprecated"}
    assert set(result.to_skip["amd64"]) == {"gcc-old"}

    # Test 3: Multiple packages per line
    create_package_file(
        pkg_config_dir,
        "MULTILINE",
        """PACKAGES install
vim git python3
build-essential gcc make
""",
    )

    result = parse_class_packages(conf_dir, "MULTILINE")
    assert set(result.to_install["all"]) == {"vim", "git", "python3", "build-essential", "gcc", "make"}


@pytest.mark.parametrize(
    "config_content,expected_error",
    [
        (
            """PACKAGES invalid
vim
""",
            "PACKAGES line not understood",
        ),
        (
            """PACKAGES install extra unexpected
vim
""",
            "invalid PACKAGES line",
        ),
    ],
)
def test_parse_class_packages_invalid_config(package_config_dir, config_content, expected_error):
    """Test parsing invalid package config files."""
    conf_dir, pkg_config_dir = package_config_dir

    create_package_file(pkg_config_dir, "INVALID", config_content)

    with pytest.raises(ValueError, match=expected_error):
        parse_class_packages(conf_dir, "INVALID")


def test_real_world_scenario(package_config_dir):
    """Test a realistic scenario similar to GRML_GHACI_CLOUD."""
    conf_dir, pkg_config_dir = package_config_dir

    # Simulate base class
    create_package_file(
        pkg_config_dir,
        "BASE",
        """PACKAGES install
vim
git
linux-image-amd64
""",
    )

    # Simulate CI optimization class
    create_package_file(
        pkg_config_dir,
        "CI_OPTIMIZED",
        """PACKAGES skip
linux-image-amd64

PACKAGES install amd64
linux-image-cloud-amd64
""",
    )

    # Parse both and merge in order
    base_list = parse_class_packages(conf_dir, "BASE")
    ci_list = parse_class_packages(conf_dir, "CI_OPTIMIZED")

    base_list.merge(ci_list)

    # Verify final result
    install_amd64 = base_list.as_apt_params(restrict_to_arch="amd64")
    assert "vim" in install_amd64
    assert "git" in install_amd64
    assert "linux-image-amd64" not in install_amd64  # Skipped
    assert "linux-image-cloud-amd64" in install_amd64  # Cloud version installed
