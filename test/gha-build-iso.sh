#!/bin/bash
# SPDX-License-Identifier: GPL-2.0-or-later
#
# Entrypoint for GitHub Actions to build an ISO with a minimal setup,
# just to validate grml-live itself.

set -euxo pipefail

MODE=$1

if [ -z "${ARCH:-}" ]; then
    echo "E: ARCH environment variable must be set"
    exit 1
fi

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

    docker run -i --rm --volume "${PWD}:/source" -e SKIP_SOURCES=1 -e DO_DAILY_UPLOAD=0 -e EXTRA_CLASSES="${EXTRA_CLASSES:-}" -w /source debian:"$HOST_RELEASE" \
        bash -c \
        "apt-get update -qq && apt-get satisfy -q -y --no-install-recommends 'git, ca-certificates' \
        && git config --global --add safe.directory /source \
        && /source/build-driver/build /source ${build_mode} /source/${config_filename} ghaci $ARCH testing"

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
        $ARCH: "file:///source/$INPUT_ISO"
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
        $ARCH: "file:///source/$INPUT_ISO"
EOT

    run_build build-gha-ci-test-config-build-only-second release results-build-only-second

else
    echo "E: unsupported \$MODE $MODE"
    exit 1
fi
