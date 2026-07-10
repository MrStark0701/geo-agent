#!/usr/bin/env bash
set -euo pipefail

# Project-scoped install: everything lands under the CURRENT WORKING DIRECTORY's .claude/, not
# the home directory. Run this from inside the project you want the agent available in - each
# project gets its own self-contained copy (own venv, own engine), no shared global state.
#
# SCRIPT_DIR (source of the files to copy FROM) and PROJECT_DIR (the target to install INTO) are
# deliberately different things: SCRIPT_DIR is wherever this script itself lives (a git clone or
# bootstrap.sh's extracted tmpdir); PROJECT_DIR is the caller's cwd, unaffected by either of
# those - neither `git clone` nor bootstrap.sh changes directory before invoking this script.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(pwd)"
INSTALL_DIR="$PROJECT_DIR/.claude/geo-agent"
VENV_DIR="$INSTALL_DIR/.venv"
AGENTS_DIR="$PROJECT_DIR/.claude/agents"

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

# 5. Wrapper script so the agent's Bash calls never need manual venv activation. Uses
#    PYTHONPATH (not `cd`) to make the `engine` package importable regardless of the caller's
#    cwd - `cd`-ing into INSTALL_DIR first would silently break relative --file paths in
#    local-file mode, since they'd resolve against the wrong directory.
cat > "$INSTALL_DIR/geo-audit" <<EOF
#!/usr/bin/env bash
export PYTHONPATH="$INSTALL_DIR\${PYTHONPATH:+:\$PYTHONPATH}"
exec "$VENV_DIR/bin/python3" -m engine.cli "\$@"
EOF
chmod +x "$INSTALL_DIR/geo-audit"

# 6. Install the agent definition into THIS project's .claude/agents/ (Claude Code auto-discovers
#    project-scoped agents here - no global registration needed, and it's checked into the
#    project's own git repo if the team wants to share it).
mkdir -p "$AGENTS_DIR"
cp "$SCRIPT_DIR/agents/GeoAgent.md" "$AGENTS_DIR/GeoAgent.md"

# 7. Smoke test - imports/module load only, zero network calls, so this doesn't depend on
#    internet reachability beyond the install steps already completed above.
"$INSTALL_DIR/geo-audit" --self-test >/dev/null 2>&1 \
  && echo "GEO agent installed in $PROJECT_DIR/.claude/. In Claude Code, ask it to audit a site." \
  || echo "Install finished but self-test failed - check $INSTALL_DIR/geo-audit manually."
