#!/bin/bash

set -e

# Set default grml-live path
GRML_LIVE_PATH="/opt/grml-live"

# Add grml-live to PATH
export PATH="$GRML_LIVE_PATH:$PATH"

# Check if user provided custom grml-live-grml checkout
if [ -d "/opt/grml-live-grml" ] && [ "$(ls -A /opt/grml-live-grml 2>/dev/null)" ]; then
    echo "Using custom grml-live-grml checkout from /opt/grml-live-grml"
    export GRML_LIVE_GRML_PATH="/opt/grml-live-grml"
fi

# Function to show help
show_help() {
    cat << EOF
grml-live Docker Container

Usage:
  docker run [docker-options] <image> <command> [args...]

Commands:
  grml-live [args...]     Run grml-live with specified arguments
  build [args...]         Run build-driver/build with specified arguments
  help                    Show this help message

Examples:
  # Run grml-live (mount output directory)
  docker run --rm -v "\$PWD:/workspace" \\
    <image> grml-live -f GRMLBASE -o /workspace/output

  # Run build-driver (mount workspace for config and output)
  docker run --rm -v "\$PWD:/workspace" \\
    <image> build daily /workspace/config/daily full arm64 testing

  # Mount custom grml-live checkout
  docker run --rm -v "\$PWD:/workspace" \\
    -v /path/to/grml-live:/opt/grml-live \\
    <image> grml-live [args...]

  # Mount custom grml-live-grml checkout
  docker run --rm -v "\$PWD:/workspace" \\
    -v /path/to/grml-live:/opt/grml-live \\
    -v /path/to/grml-live-grml:/opt/grml-live-grml \\
    <image> grml-live [args...]

EOF
}

# Parse the first argument and execute accordingly
case "$1" in
    "grml-live")
        shift
        exec grml-live "$@"
        ;;
    "build")
        shift
        exec "$GRML_LIVE_PATH/build-driver/build" "/opt/grml-live" "$@"
        ;;
    "help"|"--help"|"-h")
        show_help
        ;;
    "")
        show_help
        ;;
    *)
        echo "Unknown command: $1"
        echo ""
        show_help
        exit 1
        ;;
esac
