#!/bin/bash
# SPDX-License-Identifier: GPL-2.0-or-later
#
# Entrypoint for GitHub Actions to build an ISO with a minimal setup,
# just to validate grml-live itself.

set -euxo pipefail

cat >build-gha-ci-test-config <<EOT
---
last_release: "2024.02"
EOT

# Install as little Debian packages as possible,
# we do not want to test *Debian*.
cat > etc/grml/fai/config/package_config/GRML_GHACI <<EOT
PACKAGES install AMD64
linux-image-amd64

PACKAGES install ARM64
linux-image-arm64
EOT

# Note: file ownership inside docker is "wrong", and then git will fail.
# As a workaround we set safe.directory to ignore the ownership issues.

docker run -i --rm --volume "${PWD}:/source" -e SKIP_SOURCES=1 -e DO_DAILY_UPLOAD=0 -w /source debian:"$HOST_RELEASE" bash -c \
    "apt-get update -qq && apt-get satisfy -q -y --no-install-recommends 'git, ca-certificates' && git config --global --add safe.directory /source && /source/build-driver/build /source daily /source/build-gha-ci-test-config ghaci amd64 testing"

sudo chmod -R a+rX results
