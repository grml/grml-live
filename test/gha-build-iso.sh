#!/bin/bash
# SPDX-License-Identifier: GPL-2.0-or-later
#
# Entrypoint for GitHub Actions to build an ISO with a minimal setup,
# just to validate grml-live itself.

set -euxo pipefail

MODE=$1

# Install as few Debian packages as possible,
# we do not want to test *Debian*.
cat > config/package_config/GRML_GHACI <<EOT
PACKAGES install
vim-tiny

PACKAGES install AMD64
linux-image-amd64

PACKAGES install ARM64
linux-image-arm64
EOT

cat >build-gha-ci-test-config-initial <<EOT
---
last_release: "2024.12"
EOT

run_build() {
    local config_filename
    config_filename=$1
    local build_mode
    build_mode=$2
    local results_directory
    results_directory=$3

    docker run -i --rm --volume "${PWD}:/source" -e SKIP_SOURCES=1 -e DO_DAILY_UPLOAD=0 -w /source debian:"$HOST_RELEASE" \
        bash -c \
        "apt-get update -qq && apt-get satisfy -q -y --no-install-recommends 'git, ca-certificates' \
        && git config --global --add safe.directory /source \
        && /source/build-driver/build /source ${build_mode} /source/${config_filename} ghaci amd64 testing"

    sudo chmod -R a+rX results
    sudo mv results "${results_directory}"
}


if [ "$MODE" = "initial" ]; then

    # Note: file ownership inside docker is "wrong", and then git will fail.
    # As a workaround we set safe.directory to ignore the ownership issues.

    run_build build-gha-ci-test-config-initial daily results-initial

elif [ "$MODE" = "build-only-twice" ]; then
    INPUT_ISO=$(ls results-initial/grml_isos/grml*iso)
    cat >build-gha-ci-test-config-build-only-first <<EOT
---
last_release: "2024.12"
debian_suite: testing
release_version: "ci-bo-first"
release_name: CI1
base_iso:
    ghaci:
        amd64: "file:///source/$INPUT_ISO"
EOT

    run_build build-gha-ci-test-config-build-only-first release results-build-only-first

    INPUT_ISO=$(ls results-build-only-first/grml_isos/grml*iso)
    cat >build-gha-ci-test-config-build-only-second <<EOT
---
last_release: "2024.12"
debian_suite: testing
release_version: "ci-bo-second"
release_name: CI2
base_iso:
    ghaci:
        amd64: "file:///source/$INPUT_ISO"
EOT

    run_build build-gha-ci-test-config-build-only-second release results-build-only-second

else
    echo "E: unsupported \$MODE $MODE"
    exit 1
fi
