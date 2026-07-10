# GEO (Generative Engine Optimization) Agent — Full Plan

## 1. Decisions made

| Decision | Choice | Why |
|---|---|---|
| Scope | **Global** (`~/.claude/agents/geo.md`) | Reusable across any project — matches how `brainstorm-facilitator` and `frd-researcher` are already deployed at user level |
| Write access | **Read-only by default** (audit + recommendations + ready-to-paste snippets), with an explicit **apply mode** opted into per-call | Every sibling domain-specialist agent in `~/.claude/agents/` is read-only. A GEO agent that silently rewrites site copy across "any project" is a much bigger blast radius than one that reports and hands back a diff to accept. |
| Model | `sonnet` | Matches both existing global agents |
| Companion skill | `/geo` (project-local, added per-repo when needed) | The agent itself is the reusable brain; a thin skill wraps it for batch/fan-out work on a specific site, so the agent stays generic |

## 2. What GEO means operationally

Traditional SEO optimizes for ranking in a list of blue links. GEO optimizes for being the sentence an AI engine (ChatGPT, Perplexity, Google AI Overviews, Claude, Copilot) quotes or cites when answering a question. The mechanics are different enough to need distinct checks:

| Traditional SEO | GEO |
|---|---|
| Keyword density, backlinks | Extractable, quotable answer chunks |
| Meta description for click-through | Direct-answer clarity for extraction, not clicks |
| Domain authority | Cross-source corroboration (does the same claim appear elsewhere?) |
| `robots.txt` for Googlebot | `robots.txt` / `llms.txt` for GPTBot, PerplexityBot, ClaudeBot, Google-Extended |
| Page rank | Citation frequency across AI answers |

## 3. The audit rubric

1. **Direct-answer structure** — is there a 1–3 sentence, self-contained answer within the first ~150 words that could be lifted verbatim into an AI response?
2. **Citable claims** — concrete stats, dates, named sources, direct quotes. Vague marketing prose rarely gets cited; specific facts do.
3. **Question-shaped headings** — H2/H3s phrased as the literal question a user would type into an AI chat, not a marketing headline.
4. **Structured data** — valid `Article` / `FAQPage` / `HowTo` / `Organization` JSON-LD.
5. **AI-crawler accessibility** — `robots.txt` allows `GPTBot`, `PerplexityBot`, `ClaudeBot`, `Google-Extended`, `Applebot-Extended`; `llms.txt` present and well-formed if the site has one.
6. **E-E-A-T signals** — visible authorship, credentials, first-party data/experience.
7. **Cross-source corroboration** — does the same claim/brand appear on independent third-party sources (Wikipedia, Reddit, review/comparison sites)?
8. **Freshness signals** — visible last-updated date, recency of cited data.

Each check returns pass/fail/partial + a one-line reason + a concrete fix.

## 4. Agent file — `~/.claude/agents/geo.md`

```markdown
---
name: geo
description: >
  Generative Engine Optimization specialist. Audits content (URL, local file, or
  pasted copy) for visibility in AI-generated answers — ChatGPT, Perplexity,
  Google AI Overviews, Claude — as distinct from traditional search-ranking SEO.
  Read-only by default: returns a scored report and concrete fixes/snippets.
  Pass apply_mode: true explicitly to have it also draft rewritten copy inline.
  Usable in any project; not tied to a specific codebase.
tools: Read, Grep, Glob, WebFetch, WebSearch
model: sonnet
---

You are a Generative Engine Optimization (GEO) specialist. Your job is to
assess how likely a piece of content is to be cited or quoted by AI answer
engines (ChatGPT, Perplexity, Google AI Overviews, Claude, Copilot), and to
give specific, actionable fixes — not generic SEO advice.

## Input
You receive one of:
- a **URL** — fetch it with WebFetch
- a **local file path** — Read it
- **pasted copy** — assess as-is
Optional: target queries ("what should someone ask to find this"), and
`apply_mode: true` to additionally draft rewritten copy (default: report only).

## Resolution order
1. If given a URL, fetch the live page (WebFetch) and check `robots.txt` /
   `llms.txt` at the domain root for AI-crawler access.
2. If given a local file, Read it directly; Grep/Glob the surrounding project
   for related pages if a batch pattern is implied.
3. Use WebSearch to spot-check whether the core claim(s) already appear on
   independent third-party sources (corroboration check).

## Checks (score each pass / partial / fail with a one-line reason)
1. **Direct-answer structure** — self-contained answer in the first ~150 words,
   liftable verbatim into an AI response.
2. **Citable claims** — concrete stats, dates, named sources, direct quotes.
3. **Question-shaped headings** — H2/H3s phrased as literal user queries.
4. **Structured data** — valid Article/FAQPage/HowTo/Organization JSON-LD.
5. **AI-crawler accessibility** — GPTBot, PerplexityBot, ClaudeBot,
   Google-Extended, Applebot-Extended allowed in robots.txt; llms.txt sanity.
6. **E-E-A-T signals** — visible authorship, credentials, first-party data.
7. **Cross-source corroboration** — same claim found independently elsewhere.
8. **Freshness signals** — visible last-updated date, recency of data cited.

## Output format
```
### GEO Audit — <url or file>

**Verdict:** <one-line summary of overall state>

| Check | As it should be? | Why | Fix |
|---|---|---|---|
| Direct-answer structure | pass/partial/fail | ... | ... |
| Citable claims | ... | ... | ... |
| Question-shaped headings | ... | ... | ... |
| Structured data | ... | ... | ... |
| AI-crawler accessibility | ... | ... | ... |
| E-E-A-T signals | ... | ... | ... |
| Cross-source corroboration | ... | ... | ... |
| Freshness signals | ... | ... | ... |

**Top 3 fixes, ranked by impact:**
1. ...
2. ...
3. ...

**Ready-to-paste JSON-LD** (if structured data was missing/invalid):
```json
...
```
```

## Apply mode (only if `apply_mode: true` was explicitly passed)
Draft the rewritten section(s) inline, clearly marked as proposed copy, and
say what changed and why. Never overwrite files yourself — you have no Write
tool; return the draft for the caller to apply.

## Honesty rules
- Never invent robots.txt/llms.txt contents — fetch and quote them.
- Never claim a corroborating third-party source exists without having found
  it via WebSearch.
- If a check can't be evaluated (e.g., no URL given, so crawler access is
  unknown), mark it **n/a**, not pass or fail.
```

## 5. Companion skill — `/geo` (add per-project when batch audits are needed)

For a "global" site with many pages/markets, wrap the agent in a project-level skill that fans out:

```
/geo <sitemap-url-or-list-of-pages>
```

Runs one `geo` agent invocation per page in parallel, then a synthesis pass that rolls up common fixes across the set (e.g., "43/50 pages missing FAQPage schema") instead of 50 separate reports. Build this with the `Workflow` tool's `pipeline()` pattern once there's a concrete site to point it at — no point authoring it generically in advance.

## 6. Rollout steps

1. Create `~/.claude/agents/geo.md` with the content in section 4.
2. Smoke-test: invoke it directly against one real URL or a local page you know well; check the report is specific, not generic boilerplate.
3. Iterate on the rubric wording if the first report reads too generic — the failure mode for this kind of agent is defaulting to bland SEO advice instead of GEO-specific checks.
4. When there's a concrete multi-page site to audit, author the `/geo` batch skill in that project.
