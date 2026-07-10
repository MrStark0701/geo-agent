#!/usr/bin/env bash
set -euo pipefail

# True single-command installer for users who don't have (or don't want to use) git.
#
# Usage:
#   curl -fsSL https://raw.githubusercontent.com/MrStark0701/geo-agent/main/bootstrap.sh | bash

REPO_ARCHIVE_URL="https://github.com/MrStark0701/geo-agent/archive/refs/heads/main.tar.gz"

command -v curl >/dev/null 2>&1 || { echo "curl required"; exit 1; }
command -v tar >/dev/null 2>&1 || { echo "tar required"; exit 1; }

TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT

# GitHub's auto-generated branch archive - always reflects current `main`, no build/release
# step to keep in sync. --strip-components=1 drops the "geo-agent-main/" wrapper dir it adds.
curl -fsSL "$REPO_ARCHIVE_URL" | tar -xz -C "$TMP" --strip-components=1

# Hand off to the real installer, which is remote-agnostic (reads engine/, agents/GeoAgent.md,
# and requirements.txt from its own directory) - it doesn't know or care that this copy came
# from a curl+tar extraction rather than `git clone`.
bash "$TMP/install.sh"
