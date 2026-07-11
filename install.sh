#!/usr/bin/env bash
set -euo pipefail

# The agent is a single self-contained markdown file - no engine, no dependencies, nothing else
# to install. This script just fetches that one file into the CURRENT project's .claude/agents/.
# Run it from inside whatever project you want the agent available in.

AGENT_URL="https://raw.githubusercontent.com/MrStark0701/geo-agent/main/agents/GeoAgent.md"
AGENTS_DIR="$(pwd)/.claude/agents"

command -v curl >/dev/null 2>&1 || { echo "curl required"; exit 1; }

mkdir -p "$AGENTS_DIR"
curl -fsSL "$AGENT_URL" -o "$AGENTS_DIR/GeoAgent.md"

# Sanity-check the download actually landed a real agent file, not an empty/error response.
grep -q "^name: geo-agent" "$AGENTS_DIR/GeoAgent.md" 2>/dev/null \
  || { echo "error: download looked wrong - check $AGENTS_DIR/GeoAgent.md manually"; exit 1; }

echo "GEO agent installed: $AGENTS_DIR/GeoAgent.md"
echo "In Claude Code, ask it to audit a site's GEO."
