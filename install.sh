#!/usr/bin/env bash
set -euo pipefail

# Remote-agnostic by design: this script reads engine/, agents/GeoAgent.md, and requirements.txt
# from ITS OWN checkout directory rather than re-cloning from a hardcoded remote URL. That means
# the exact same script works whether the user cloned from the internal, login-gated GitLab
# instance or the public GitHub mirror - no "which remote am I on" logic needed, and no second
# network fetch for source that's already sitting right next to this script.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INSTALL_DIR="$HOME/.claude/geo-agent"
VENV_DIR="$INSTALL_DIR/.venv"
AGENTS_DIR="$HOME/.claude/agents"

for required in "$SCRIPT_DIR/requirements.txt" "$SCRIPT_DIR/engine" "$SCRIPT_DIR/agents/GeoAgent.md"; do
  [ -e "$required" ] || { echo "error: $required not found - run this script from within a full clone of the repo, not standalone."; exit 1; }
done

# 1. python3 present + >= 3.9
command -v python3 >/dev/null 2>&1 || { echo "python3 required"; exit 1; }
python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3,9) else 1)' \
  || { echo "python3 >= 3.9 required"; exit 1; }

# 2. venv module present (some minimal Linux distros ship python3 without it)
python3 -c "import venv" 2>/dev/null || { echo "python3 'venv' module missing (try: apt install python3-venv)"; exit 1; }

# 3. Create venv (idempotent - skip if already healthy) + install pinned deps
mkdir -p "$INSTALL_DIR"
[ -x "$VENV_DIR/bin/python3" ] || python3 -m venv "$VENV_DIR"
"$VENV_DIR/bin/pip" install --quiet --upgrade pip
"$VENV_DIR/bin/pip" install --quiet -r "$SCRIPT_DIR/requirements.txt"

# 4. Install the engine
rm -rf "$INSTALL_DIR/engine"
cp -R "$SCRIPT_DIR/engine" "$INSTALL_DIR/engine"

# 5. Wrapper script so the agent's Bash calls never need manual venv activation
cat > "$INSTALL_DIR/geo-audit" <<EOF
#!/usr/bin/env bash
exec "$VENV_DIR/bin/python3" -m engine.cli "\$@"
EOF
chmod +x "$INSTALL_DIR/geo-audit"

# 6. Install the agent definition
mkdir -p "$AGENTS_DIR"
cp "$SCRIPT_DIR/agents/GeoAgent.md" "$AGENTS_DIR/GeoAgent.md"

# 7. Smoke test - imports/module load only, zero network calls, so this doesn't depend on
#    internet reachability beyond the install steps already completed above.
"$INSTALL_DIR/geo-audit" --self-test >/dev/null 2>&1 \
  && echo "GEO agent installed. In Claude Code, ask it to audit a site." \
  || echo "Install finished but self-test failed - check $INSTALL_DIR/geo-audit manually."
