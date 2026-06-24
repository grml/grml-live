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

    export SKIP_SOURCES=1
    export DO_DAILY_UPLOAD=0
    export EXTRA_CLASSES="${EXTRA_CLASSES:-}"
    export GITHUB_PR_NUMBER="${GITHUB_PR_NUMBER:-}"
    sudo apt-get update -qq
    sudo apt-get satisfy -q -y --no-install-recommends 'git, ca-certificates, debian-archive-keyring'
    if [ "$(cat /proc/sys/kernel/apparmor_restrict_unprivileged_userns || true)" == "1" ]; then
        # workaround unshare restrictions on Ubuntu 24.04. Symptom seen:
        # "unshare: cannot change root filesystem propagation: Permission denied"
        echo "W: turning off apparmor_restrict_unprivileged_usern to avoid unshare failure"
        echo 0 | sudo tee /proc/sys/kernel/apparmor_restrict_unprivileged_userns
    fi

    # Processes in usernamespace must be able to chdir() to all parent directories
    # so they can read the files in grml-live/config.
    sudo chmod a+rX /home/runner

    ./build-driver/build "${PWD}" "${build_mode}" "${PWD}"/"${config_filename}" ghaci "${ARCH}" testing

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
release_version: "${GITHUB_PR_NUMBER:+pr$GITHUB_PR_NUMBER-}ci1"
release_name: "${GITHUB_PR_NUMBER:+PR$GITHUB_PR_NUMBER }CI1"
base_iso:
    ghaci:
        $ARCH: "file://${PWD}/${INPUT_ISO}"
EOT

    run_build build-gha-ci-test-config-build-only-first release results-build-only-first

    INPUT_ISO=$(ls results-build-only-first/grml_isos/grml*iso)
    cat >build-gha-ci-test-config-build-only-second <<EOT
---
last_release: "2024.12"
debian_suite: testing
release_version: "${GITHUB_PR_NUMBER:+pr$GITHUB_PR_NUMBER-}ci2"
release_name: "${GITHUB_PR_NUMBER:+PR$GITHUB_PR_NUMBER }CI2"
base_iso:
    ghaci:
        $ARCH: "file://${PWD}/${INPUT_ISO}"
EOT

    run_build build-gha-ci-test-config-build-only-second release results-build-only-second

else
    echo "E: unsupported \$MODE $MODE"
    exit 1
fi
