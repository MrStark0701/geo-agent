# GEO Agent

Audits any website (or local HTML file) for GEO (Generative Engine Optimization) — visibility
in AI-generated answers (ChatGPT, Perplexity, Google AI Overviews, Claude, Copilot) — as
distinct from traditional search-ranking SEO.

Ships as a Claude Code agent (`agents/GeoAgent.md`) backed by a deterministic Python
check-engine (`engine/`). No composite score: every check reports pass / partial / fail / n/a
with a one-line reason and a concrete fix.

## Install

**Project-scoped: run this from inside the project you want the agent in.** Each project gets
its own self-contained copy — own venv, own engine, no shared global state with other projects.

```bash
cd ~/your-project
curl -fsSL https://raw.githubusercontent.com/MrStark0701/geo-agent/main/bootstrap.sh | bash
```
True single command: downloads a GitHub archive of `main` via `curl`+`tar` into a tmp dir, then
runs `install.sh` from there. Only needs `curl`, `tar`, and `python3` — no git required.

**If you'd rather use git, or want to inspect the source first:**
```bash
cd ~/your-project
git clone https://github.com/MrStark0701/geo-agent.git /tmp/geo-agent-src && bash /tmp/geo-agent-src/install.sh
```

Both paths write into **the directory you ran the command from** (`$(pwd)` at install time, not
wherever the source came from): `./.claude/agents/GeoAgent.md` (Claude Code auto-discovers
project-scoped agents here — check it into your project's own repo if your team wants to share
it) and `./.claude/geo-agent/` (its own isolated virtualenv + engine, `requests`+`beautifulsoup4`
installed only there). Run the installer again in a different project directory to install a
separate, independent copy there.

Caveat worth knowing: the venv is not guaranteed portable if you later move/rename the project
directory (Python venvs can embed absolute paths) — if that happens, just re-run the installer
from the new location rather than expecting a copied `.venv/` to keep working.

## Use

In Claude Code, ask it to audit a site — e.g. "audit example.com's GEO" — and the `geo-agent`
agent takes over: runs the engine, adds cross-source corroboration via its own WebSearch, and
reports a per-check table.

## Manual engine use (no Claude Code required)

Run from the project root you installed into:
```bash
.claude/geo-agent/geo-audit https://example.com
.claude/geo-agent/geo-audit --file path/to/local.html
```

Prints one JSON object: fetch metadata plus a `checks` array
(`{"check", "status", "reason", "fix"}` per check).

## What's checked

robots.txt / llms.txt AI-crawler accessibility, JSON-LD structured data, meta tags, content
quality (word count, heading hierarchy, front-loading), question-shaped headings, freshness
signals, speculative AI-discovery endpoints, negative citability signals (thin content,
keyword stuffing, boilerplate ratio), brand/entity (E-E-A-T) signals, and an 8-category
cloaking/prompt-injection detector (hidden text, invisible Unicode, monochrome text,
micro-fonts, and more). Cross-source corroboration is performed by the agent itself via
WebSearch, not the engine (it needs live web search, which the engine deliberately doesn't do).

## License

MIT (see `LICENSE`). Portions of `engine/` are ported or closely derived from
[Auriti-Labs/geo-optimizer-skill](https://github.com/Auriti-Labs/geo-optimizer-skill) (MIT) —
see `NOTICE` and `THIRD_PARTY_LICENSES/`.
