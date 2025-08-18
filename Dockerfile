FROM debian:trixie

# Build arguments for version, git commit, and dependencies
ARG GRML_LIVE_VERSION
ARG GIT_COMMIT
ARG DEPENDS
ARG RECOMMENDS

RUN apt-get update && \
    PACKAGES="$DEPENDS${RECOMMENDS:+, $RECOMMENDS}, netbase, git, python3-yaml" && \
    apt-get satisfy -y "$PACKAGES" && \
    rm -rf /var/lib/apt/lists/*

# Copy grml-live checkout to /opt/grml-live
COPY . /opt/grml-live

# Create directory for optional grml-live-grml checkout
RUN mkdir -p /opt/grml-live-grml

# Update version in grml-live script
RUN if [ -n "$GRML_LIVE_VERSION" ]; then \
    sed -i "/^GRML_LIVE_VERSION=/c\\GRML_LIVE_VERSION='$GRML_LIVE_VERSION'" /opt/grml-live/grml-live; \
    fi

# Add git commit and version as labels
LABEL org.opencontainers.image.revision="$GIT_COMMIT" \
    grml-live.version="$GRML_LIVE_VERSION"

# Copy entrypoint script
COPY entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

# Set working directory
WORKDIR /workspace

# Set entrypoint
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
CMD ["help"]
