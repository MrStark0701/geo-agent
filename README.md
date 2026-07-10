# GEO Agent

Audits any website (or local HTML file) for GEO (Generative Engine Optimization) — visibility
in AI-generated answers (ChatGPT, Perplexity, Google AI Overviews, Claude, Copilot) — as
distinct from traditional search-ranking SEO.

Ships as a Claude Code agent (`agents/GeoAgent.md`) backed by a deterministic Python
check-engine (`engine/`). No composite score: every check reports pass / partial / fail / n/a
with a one-line reason and a concrete fix.

## Install

**Anyone (public mirror):**
```bash
git clone https://github.com/MrStark0701/geo-agent.git && bash geo-agent/install.sh
```

**AveoSoft internal (same content, private instance):**
```bash
git clone https://gitlab.aveosoft.com/TejasChauhan/geo-agent.git && bash geo-agent/install.sh
```

Either way it's the same one-line, two-command paste: `git clone` then `bash .../install.sh`.
`install.sh` reads everything from its own checkout — it works identically regardless of which
remote you cloned from, no separate re-fetch or auth step of its own. The GitLab instance is
login-gated (a bare `curl | bash` can't authenticate there, which is why this is `git clone`-based
rather than a raw `curl`), so use the GitHub mirror unless you specifically need the internal one.

This creates an isolated virtualenv at `~/.claude/geo-agent/`, installs the two dependencies
(`requests`, `beautifulsoup4`), and copies `GeoAgent.md` into `~/.claude/agents/`. No manual
activation or path setup needed.

## Use

In Claude Code, ask it to audit a site — e.g. "audit example.com's GEO" — and the `geo-agent`
agent takes over: runs the engine, adds cross-source corroboration via its own WebSearch, and
reports a per-check table.

## Manual engine use (no Claude Code required)

```bash
~/.claude/geo-agent/geo-audit https://example.com
~/.claude/geo-agent/geo-audit --file path/to/local.html
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
