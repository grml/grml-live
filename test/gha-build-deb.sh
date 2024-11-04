#!/bin/bash
# SPDX-License-Identifier: GPL-2.0-or-later
#
# Entrypoint for GitHub Actions to build a deb.

set -eu -o pipefail
set -x

if [ -z "${CI:-}" ] || [ -z "${GITHUB_RUN_NUMBER:-}" ]; then
  echo "Running outside of CI pipeline." >&2
  exit 1
fi

docker run --privileged -v "$(pwd)":/code --rm -i debian:"$HOST_RELEASE" \
    bash -c 'TERM='"$TERM"' cd /code && ./test/docker-build-deb.sh --autobuild '"$GITHUB_RUN_NUMBER"
