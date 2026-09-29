# Image for the headless Claude register-extraction baseline.
# At runtime ONLY work/ is bind-mounted, so the container cannot see the host's
# /tmp, the hal_agent repos, or any other run -- a hard OS-level read jail
# (what bwrap/docker give that the in-process sandbox's deny-only reads cannot).
FROM debian:latest

RUN apt-get update \
 && apt-get install -y --no-install-recommends \
      curl ca-certificates jq python3 \
 && rm -rf /var/lib/apt/lists/*

# Claude Code (self-contained native install).
RUN curl -fsSL https://claude.ai/install.sh | bash \
 && ln -sf /root/.local/bin/claude /usr/local/bin/claude

WORKDIR /work
