# GEO Agent

Audits any website (or local HTML file / pasted copy) for GEO (Generative Engine Optimization) —
visibility in AI-generated answers (ChatGPT, Perplexity, Google AI Overviews, Claude, Copilot) —
as distinct from traditional search-ranking SEO.

A single, self-contained Claude Code agent (`agents/GeoAgent.md`) — no bundled code, no
dependencies, no install step beyond copying one file. It performs every check itself using
`WebFetch`/`WebSearch`/`Read`. No composite score: every check reports pass / partial / fail / n/a
with a one-line reason and a concrete fix.

## Install

Run from inside the project you want the agent available in:

```bash
curl -fsSL https://raw.githubusercontent.com/MrStark0701/geo-agent/main/install.sh | bash
```

That's the whole install: it downloads `GeoAgent.md` into `./.claude/agents/` (the directory you
ran the command from). Claude Code auto-discovers project-scoped agents there — no restart, no
registration step. Check it into your project's own repo if your team wants to share it. Run the
command again in a different project directory to install a separate copy there.

No Python, no venv, no other dependency — `curl` is the only requirement.

**If you'd rather just grab the file directly:**
```bash
mkdir -p .claude/agents
curl -fsSL https://raw.githubusercontent.com/MrStark0701/geo-agent/main/agents/GeoAgent.md -o .claude/agents/GeoAgent.md
```

## Use

In Claude Code, ask it to audit a site — e.g. "audit example.com's GEO" — and the `geo-agent`
agent takes over: fetches the site itself, runs through the full check list, adds cross-source
corroboration via its own `WebSearch`, and reports a per-check table.

## What's checked

robots.txt / llms.txt AI-crawler accessibility, JSON-LD structured data, meta tags, content
quality, question-shaped headings, freshness signals, speculative AI-discovery endpoints,
negative citability signals (thin content, keyword stuffing, boilerplate), brand/entity (E-E-A-T)
signals, and a cloaking/hidden-text detector. Cross-source corroboration is performed via
`WebSearch` — checking whether independent third-party sources actually corroborate the site's
claims, something no static checker can do on its own.

## License

MIT (see `LICENSE`). `agents/GeoAgent.md`'s check rubric was informed by
[Auriti-Labs/geo-optimizer-skill](https://github.com/Auriti-Labs/geo-optimizer-skill) (MIT) — see
`NOTICE` and `THIRD_PARTY_LICENSES/`.

## About `engine/`

This repo also contains a deterministic Python check-engine (`engine/`) from an earlier iteration
of this project, where the agent shelled out to bundled code instead of doing every check itself.
It's not part of the current install and isn't required for anything above — kept in the repo as
a reference for a possible future direction, not because it's needed today.
