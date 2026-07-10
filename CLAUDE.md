# geo-agent — Project Instructions

## What this project is

**Goal:** audit ANY website and assess its GEO (Generative Engine Optimization) — its visibility
in AI-generated answers (ChatGPT, Perplexity, Google AI Overviews, Claude, Copilot), as distinct
from traditional search-ranking SEO.

**How we get there (confirmed 2026-07-08):**
1. **Reference existing agents** (esp. `geo-optimizer-skill`) — learn from the best.
2. **Improve on them** — our own checks, our KPI framework, our output philosophy.
3. **Build our OWN custom GEO agent** — we own the code, not a thin wrapper around someone else's.
4. **Build our OWN GEO MCP server** — so the capability is usable across any platform/project.

This is an **ownership** goal, not an adopt goal. Existing MIT-licensed tools are the base/reference
to fork-and-improve or reimplement from — not the final deliverable. `GEO-Agent-Plan.md` holds the
original design; the audit rubric there is our starting spec.

## Status

**BUILD COMPLETE (2026-07-10), locally. Not yet published.** Agent + engine fully implemented,
verified against pilotdeck.co and a local-file test, per the approved plan at
`~/.claude/plans/can-you-write-a-inherited-valiant.md`.

**PIVOT (2026-07-10): MCP is deferred. Building a Claude Code AGENT instead.** The earlier "hard
requirement: MCP server" is SUPERSEDED for now — MCP is still the eventual cross-tool goal (don't
delete that ambition) but is explicitly out of scope for this build phase.

**What's built (all in this repo, matches the approved plan's file tree exactly):**
- `engine/` — 11 checks (robots, llms_txt, schema, meta, content [+ question-shaped-headings
  addition], signals, ai_discovery, negative_signals, brand_entity, injection [full 8-category
  cloaking/prompt-injection port]), `http_client.py` (timeout/retry/size-cap/URL-scheme guard),
  `orchestrator.py` (two input modes: live URL or `--file`/`--stdin` local HTML), `cli.py`
  (`--self-test`). No composite score anywhere; 4-value status enum `pass/partial/fail/n/a`.
- `agents/GeoAgent.md` — PascalCase filename + `name: geo-agent`, matching existing
  `~/.claude/agents/` convention. Drives the engine via Bash, performs cross-source
  corroboration itself via WebSearch (the one rubric check the engine can't do), read-only by
  default.
- `install.sh` — single-command installer: venv + `pip install requests beautifulsoup4`, pulls
  source from GitHub's auto-generated branch archive (no hand-maintained tarball), copies agent
  + engine into place. `requirements.txt`, `LICENSE`, `THIRD_PARTY_LICENSES/`, `NOTICE`,
  `README.md`, `.gitignore` all written.
- Uses a local `.build-venv/` (gitignored) for testing — separate from the reference `.venv/`
  from the 2026-07-08 eval, which still holds the original `geo-optimizer-skill` install.

**Verification results:**
- `engine/cli.py https://pilotdeck.co` — no composite score, all 11 checks present, hidden-text
  finding reproduced **exactly** (57 CSS-hidden-text elements, matching the 2026-07-08 reference
  eval finding) via the `injection` check.
- `engine/cli.py --file <local.html>` — `robots`/`llms_txt`/`ai_discovery` correctly return
  `n/a` with "no live URL provided"; all 8 other checks ran normally. Confirms the restored
  input-flexibility from the plan's gap audit.
- URL-scheme guard confirmed rejecting `file://`; timeout (15s) and size-cap (5 MiB) constants
  set as specified.
- `--self-test` passes (imports/module load only, zero network calls).

**Hosting target CHANGED (2026-07-10, later same session): `gitlab.aveosoft.com/TejasChauhan/geo-agent`,
NOT GitHub.** Confirmed accessible via `git` (credential already cached in this machine's
keychain, local git identity is `tejas.c@aveosoft.com`) — repo exists but is currently empty
(just GitLab's auto-generated placeholder README, one commit). This is a private, login-gated
instance (confirmed: even the homepage blocks unauthenticated `WebFetch`) — a real design
consequence, not just a URL swap:
- `install.sh` rewritten to `git clone` the repo instead of `curl`-ing raw files/an archive from
  GitHub. `git clone` transparently uses whatever credential (SSH key or cached HTTPS cred) the
  installing user already has — `curl` does NOT participate in git's credential-helper protocol,
  so a bare `curl | bash` bootstrap can't authenticate here even for install.sh itself.
- Install instruction is now `git clone <repo> && bash geo-agent/install.sh` (two chained
  commands, one line) instead of a single `curl | bash` pipe — the honest shape for a
  login-gated instance, not a compromise we're hiding. README.md updated to match.
- Dry-run tested (throwaway install dirs, real GitLab repo): clone+auth succeeds; only fails
  past that point because nothing's been pushed yet (repo has just the placeholder README) —
  confirms the mechanism works, not just the code compiles.

## PUSHED to GitLab (2026-07-10) — build was live there first

Local repo initialized on top of the remote's existing history (checked out `origin/main`,
restored our own `README.md` over the placeholder, did not discard/force-push the original
"Initial commit"). Committed as `5ad21b6` on `main`, pushed and confirmed via `git ls-remote`.
`.claude/` added to `.gitignore` before staging (local session config, not project content).

Full end-to-end install verified against the live GitLab repo (throwaway install dirs, real
network): clone, venv, deps, engine (11 checks), agent install, self-test, and a real audit
through the installed wrapper against pilotdeck.co all worked — 11 checks, no score field.

## Public GitHub mirror added (2026-07-10, same session)

User asked what happens if someone OUTSIDE AveoSoft wants to use this — answer: they can't,
`gitlab.aveosoft.com` requires login for anyone, even to view a "public" project. Fix: mirror to
`https://github.com/MrStark0701/geo-agent` (planned as the target back on 2026-07-08, before the
GitLab pivot — now actually used for this purpose).

**Real bug found and fixed before mirroring:** `install.sh` originally hardcoded a `git clone`
of the GitLab URL *inside itself* — pushing that same script to GitHub verbatim would have had
GitHub users' installs try to re-clone from GitLab internally (broken, since they can't
authenticate there). Fixed: rewrote `install.sh` to be **remote-agnostic** — it reads
`engine/`, `agents/GeoAgent.md`, and `requirements.txt` from its OWN checkout directory
(`$(dirname "${BASH_SOURCE[0]}")`) instead of re-cloning from any hardcoded URL. Same script now
works identically regardless of which remote was cloned from, with one fewer network round-trip.
README.md updated to show both install commands (GitHub for "anyone", GitLab for internal).

**GitHub auth chain (for reference):** `gh` CLI was installed but not logged in; this machine's
SSH key authenticates to github.com under an anonymized identity, not obviously the target
account — did NOT proceed on that ambiguity. User ran `gh auth login --hostname github.com
--git-protocol https --web` themselves (device-code browser flow) → confirmed logged in as
`MrStark0701` with `repo` scope. Then `gh auth setup-git` to make plain `git` (not just `gh`)
use that credential too.

**Target repo already existed, was Private.** `MrStark0701/geo-agent` was pre-created (empty,
one-line placeholder README, single "Initial commit") but set to Private — which would have
reproduced the exact GitLab problem (login required) for external users. Confirmed with user
before changing anything; they said make it Public. Flipped via
`gh repo edit --visibility public --accept-visibility-change-consequences`, confirmed via
`gh repo view --json visibility` → `PUBLIC`.

**Mid-push snag:** an attempted `git checkout -b github-main github/main` (to build the mirror
push on top of GitHub's own existing commit, same non-destructive pattern as the GitLab push)
failed with "local changes would be overwritten" for `CLAUDE.md`/`README.md`/`install.sh` — at
that point these had uncommitted edits (the remote-agnostic install.sh fix + dual-path README)
sitting on top of the already-pushed `5ad21b6` GitLab commit. The failed checkout discarded
those uncommitted edits back to `5ad21b6`'s versions (root cause unclear — git normally refuses
this exact conflict non-destructively rather than discarding, but empirically the working tree
reverted). **Lesson for next time: commit local edits to `main` BEFORE attempting any branch
switch for a second remote, not after** — redid the install.sh/README.md edits from memory and
committed immediately this time, avoiding a second uncommitted-changes-across-branch-switch.

**Reference eval (2026-07-08):** installed `geo-optimizer-skill 4.15.0` in `.venv/`, confirmed its
`geo-mcp` server serves 12 tools over stdio, and ran `geo audit` on pilotdeck.co (score 76/"good",
1s). Findings: it is genuinely specific (not boilerplate), already distinguishes `OAI-SearchBot`
from `GPTBot` (a fix we'd flagged), emits clean per-check `passed` JSON (so no-score is trivial to
honor), and runs ~10 extended checks beyond our 8 (cloaking/hidden-text, RAG-chunk readiness,
per-platform citation estimate, trust-stack, content-decay). It's the strongest reference/base.
Raw audit JSON: `/tmp/pilotdeck-geo.json` (regenerate with the venv when needed).

**Open decision (next):** fork-and-extend `geo-optimizer-skill` vs. build fresh using it +
`Canonry/aeo-audit` as references. See "Build approach" below.

## Key files

- `GEO-Agent-Plan.md` — the full design: decisions, audit rubric (8 checks), agent file draft,
  companion-skill plan, rollout steps. This is the spec of "what good looks like."
- `CLAUDE.md` — this file.

## Settled design decisions

- **Delivery form (current phase):** a Claude Code AGENT + bundled Python engine, installed via
  a single shell command. MCP server is deferred (was the prior "hard requirement" — see Status
  2026-07-10 pivot), not abandoned.
- **Ownership:** we build and own the agent + engine (and, later, the MCP). Existing MIT tools
  are reference/base to improve on, not the shipped product.
- **Write access:** read-only by default; explicit apply/rewrite is an opt-in per call. The
  audit tools return diffs/snippets; the caller applies them.
- **No scoring (output preference).** Don't want a 0–100 composite score. Consume structured
  per-check pass/partial/fail + one-line reason + concrete fix. Ignore/omit any composite score.
- **Batch/fan-out** (audit many pages, roll up common fixes) is deferred until needed.

## Build approach (open — decide next)

Two routes to "our own agent + our own MCP", both legal (targets are MIT):

- **Route A — fork & extend `geo-optimizer-skill`.** Start from its codebase (18 CLI commands, 12
  MCP tools, ~1,720 tests, mature MCP layer). Rebrand, strip the score from human output, add our
  KPI framework + Share-of-Voice measurement, tune checks. Fastest to a working owned MCP; we
  inherit tested plumbing. Cost: we adopt their architecture and carry their code.
- **Route B — build fresh, use it + `Canonry/aeo-audit` as references.** Design our own check
  engine + MCP from our `GEO-Agent-Plan.md` rubric, borrowing ideas (not code) from the references.
  Most control and cleanest ownership story; most work; we re-earn the test coverage they already have.

**DECIDED (2026-07-08): Route A — fork & extend `geo-optimizer-skill`.** Reaches a cross-tool GEO
MCP fastest, improving from a known-good MIT baseline. Our fork = base + no-score output + KPI
framework + per-engine AI Share of Voice + tuning.

**Firecrawl evaluation (2026-07-08):** Firecrawl is a web-data API (scrape/crawl/map/search/extract/
interact/agent) — NOT an AI-visibility/citation tracker. It CANNOT do per-engine AI Share of Voice
(it never queries ChatGPT/Perplexity's answer engine). BUT it's a strong fit for our fork's
**fetch/crawl/corroboration layer** (JS rendering, schema extraction, "audit any site," sitemap
batch, and the web-search corroboration check) — an upgrade over geo-optimizer-skill's raw
httpx+BeautifulSoup fetch. It ships an MCP server + Claude Code skill. Use it there.

**Measurement half — how it actually works:** send a prompt panel to each engine's own API and parse
the answer for brand mentions + citations. Plan:
- **v1: Perplexity Sonar API** — native citations array, one key, low cost. Single measured engine.
- **v2: OpenAI / Gemini** (web-search enabled) then **Google AIO** via SERP scraping (Firecrawl/SerpAPI, fragile).
- Alternative (rejected for now — cuts against "build our own"): integrate a dedicated AI-visibility
  REST API (LLM Pulse, Otterly).

**v1 scope (proposed):** full audit (Firecrawl-powered) + Perplexity-only AI Share of Voice.
Real measurement, one engine, minimal key/cost surface. CONFIRM before building.

## Delivery architecture (decided 2026-07-08) — "free where it can be"

Three capability tiers, priced by what they actually need:

| Tier | What | Cost |
|---|---|---|
| **Audit** (8+ checks, Firecrawl fetch) | Pure HTTP + parsing, NO LLM | **Free, every platform, zero key** (proven: pilotdeck.co audited keyless) |
| **Reasoning/synthesis** over results | The HOST model does it | **Free** — see "no sampling" below |
| **Measurement** (AI Share of Voice) | Query the target engines directly | **Paid** (Sonar) or fragile-free (scrape/cookies) — NEVER host-derivable |

- **Dual packaging over one core:** ship a **Claude Code skill/agent** (host = Claude drives it, free,
  like last30days) AND an **MCP server** (for Cursor/Gemini/etc.).
- **NO MCP sampling.** MCP `sampling/createMessage` (the only way a server could "borrow the host's
  model") is DEPRECATED as of protocol 2026-07-28 (SEP-2577); spec says integrate provider APIs
  directly. So we do NOT architect the MCP to pull Cursor's/Gemini's model.
- **How the host model stays free anyway:** design MCP tools to be MECHANICAL; the host model is
  already the caller, so it reasons BETWEEN tool calls and feeds its own web search in. "In Claude
  it uses Claude, in Cursor it uses Cursor" is achieved by tool design, not by sampling.
- **Why measurement is never free via host:** Cursor's GPT / Gemini answering a prompt is NOT
  ChatGPT.com / Perplexity.com answering with their retrieval + citations. SoV must hit the actual
  target engines. Independent of which host drives us.
- **Patterns borrowed from last30days** (reviewed its source 2026-07-08): (1) never-raise fallback
  ladder with explicit quality tiers (host-native > paid > keyless); (2) "the model is the provider"
  — offload web search/reasoning to the host model. Both belong in our fork.

## Resume here (next session)

**Build is DONE locally (2026-07-10) — see Status above for full detail.** What's left is
entirely publishing/go-ahead, not more coding:
1. **Confirm you want `MrStark0701/geo-agent` created as a public repo, then push this content
   to `main`.** Nothing has been pushed yet — explicit go-ahead needed first (standing rule on
   public/hard-to-reverse actions).
2. Once pushed: run `install.sh` for real (fresh shell, not this checkout) to verify the
   curl-archive-venv-copy flow end-to-end, per the plan's verification section.
3. MCP / Firecrawl / Perplexity-SoV work (below) stays PARKED until there's a reason to revisit —
   the agent+engine is the whole v1 now, not a stepping stone we're rushing past.

Reference env from the 2026-07-08 eval is untouched and still useful for comparison: `.venv/` has
`geo-optimizer-skill 4.15.0` + `[mcp]`; `geo-mcp` serves 12 tools; raw pilotdeck.co audit at
`/tmp/pilotdeck-geo.json`. The NEW build's own test env is `.build-venv/` (gitignored).

**Side issue to surface:** pilotdeck.co has 57 hidden-text (`display:none`) elements flagged as a
cloaking/penalty risk — pass to whoever owns the site, separate from this project. (Confirmed
again independently by the new engine's `injection` check during 2026-07-10 verification —
same count, 57.)

**Everything below this point (Route A/B, Firecrawl, Perplexity SoV, delivery-architecture tiers)
describes the FUTURE MCP phase, not the completed agent build above — kept for when that phase
resumes, not because it's unfinished business from today.**

## GEO domain essentials

**The audit rubric is leading indicators (proxies for citability):** direct-answer structure,
citable claims, question-shaped headings, structured data (JSON-LD), AI-crawler accessibility,
E-E-A-T signals, cross-source corroboration, freshness. Full definitions in `GEO-Agent-Plan.md §3`.

**Real GEO also needs lagging/outcome KPIs** — measured by actually querying the engines, which
a static rubric can't produce. The one every 2026 source converges on is **AI Share of Voice
(per engine)**: % of a defined prompt panel where you're cited vs. competitors. Also: citation
rate, citation velocity, brand sentiment in AI answers, branded-search lift.

**Two fixes flagged for the rubric (not yet applied):**
1. Distinguish crawler bots: `GPTBot` = OpenAI *training*; `OAI-SearchBot` = the bot that feeds
   *ChatGPT search citations* (missing from the plan, high value). `PerplexityBot`, `ClaudeBot`,
   `Google-Extended`, `Applebot-Extended` cover the rest.
2. `llms.txt` is a proposed convention with limited/unconfirmed honoring by major engines — keep
   the check but weight it low and label it speculative.

**Measurement reality (2026):** ChatGPT and Perplexity share only ~11% of cited domains, so
measure per engine, never a blended number. Citation is winner-take-most (top brand ~31% of a
sector's citations). Content structure matters: sequential H2>H3>H4 shows ~2.8x citation lift;
83% of commercial-query citations are from pages updated within 12 months.

## Reference implementations (learn from / borrow from — MIT)

Evaluated 2026-07-08. These are references and potential fork bases, NOT the shipped product:

- **`Auriti-Labs/geo-optimizer-skill`** (MIT, ~566★) — the strongest base. 8 core + ~10 extended
  checks, 12 MCP tools, mature test suite, live-engine `citations` for the measurement half.
  Best Route-A fork target.
- **`Canonry/aeo-audit`** (MIT) — 16-factor technical AEO audit; good reference for check logic.
- **`TheSmokeDev/geo-skills`** (MIT) — lighter, read-only skill design; reference for output shape.
- Measurement-half references: `AI2HU/gego`, `WorkSmartAI-alt/ai-visibility-monitor`.
- Deeper engine reference: `Advance-Labs/aeo-toolkit`.

Our differentiators to build in: no-score output, explicit leading+lagging KPI framework, per-engine
AI Share of Voice, and tuning for our own use (auditing any site, callable from our automation).
