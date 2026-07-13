<div align="center">

# 🛰️ GEO Agent

### Is your website invisible to ChatGPT, Perplexity, and Google AI Overviews?

**GEO Agent audits any site for _Generative Engine Optimization_ — how likely AI answer engines are to cite it — and hands you the exact fixes.**

Not SEO. Not "rank #1 on Google." This is about being the source an AI _quotes_ when someone asks it a question.

![Single file](https://img.shields.io/badge/footprint-1_markdown_file-blue)
![No dependencies](https://img.shields.io/badge/dependencies-none-brightgreen)
![License](https://img.shields.io/badge/license-MIT-lightgrey)
![Claude Code](https://img.shields.io/badge/runs_in-Claude_Code-8A2BE2)

</div>

---

## 🎯 The problem we built this to solve

Search is quietly moving from **10 blue links** to **one AI-written answer**. People ask ChatGPT, Perplexity, Claude, or Google's AI Overview a question and get a paragraph with a handful of cited sources — and never scroll a results page.

That breaks a hidden assumption behind 20 years of SEO:

> Ranking #1 on Google does **not** mean an AI will cite you. AI answer engines pick sources by a **different rubric** — clean structure, citable claims, machine-readable data, crawler access, corroboration — and most sites have never been checked against it.

So the real question isn't _"where do I rank?"_ It's **_"when an AI answers a question in my space, does it quote me — or my competitor?"_** Nobody was auditing for that. Traditional SEO tools measure the old game. **GEO Agent measures the new one.**

---

## 💡 Why an _agent_, and not just a script

The first version of this project was a Python engine — regex, parsers, exact element counts. It worked, but it was dead weight: it needed a venv, dependencies, an install step, and it could only ever do what its code hard-coded.

We threw it out and rebuilt the whole thing as **one self-contained Claude Code agent** — a single markdown file. That flip is the point:

| Old engine (retired) | GEO Agent (now) |
|---|---|
| Bundled Python + venv + pip install | **One `.md` file. Zero dependencies.** |
| Fixed regex checks | **The AI model fetches, reads, and _judges_ the page** |
| Couldn't verify claims against the wider web | **Uses live `WebSearch` to check third-party corroboration** |
| Install, wire up, maintain | **Drop it in `.claude/agents/` — it just works** |

The agent doesn't run someone else's code — **it _is_ the checker.** It fetches the real page, reads what's actually there, and makes calibrated calls the way an expert reviewer would, then tells you plainly when something is approximate rather than exact.

---

## ⚙️ How it works

```
        You: "audit example.com's GEO"
                    │
                    ▼
     ┌──────────────────────────────┐
     │          GEO Agent           │
     │  (single markdown file, runs │
     │     inside Claude Code)      │
     └──────────────────────────────┘
        │           │            │
   WebFetch     WebSearch       Read
   the page   corroborate    local file
        │           │            │
        ▼           ▼            ▼
   ┌────────────────────────────────┐
   │  12 checks · pass/partial/fail │
   │  each with a reason + a fix    │
   └────────────────────────────────┘
                    │
                    ▼
   A per-check report + top 3 ranked fixes
        (no vanity score — ever)
```

1. **~3 fetches, not 30.** One rich `WebFetch` on the homepage pulls everything the checks need at once (title/meta, JSON-LD, headings, freshness, _and_ hidden-text detection), plus `/robots.txt` and `/llms.txt`.
2. **The model judges, not a regex.** Each check is an expert judgment call against a specific rubric — with honesty rules that force it to say "approximate" when it hasn't counted exactly.
3. **It looks outside the page too.** A `WebSearch` corroboration step checks whether independent sources (Wikipedia, reviews, forums) actually back up the site's claims — something no static scanner can do.
4. **No composite score, by design.** You get an honest per-check breakdown and the 3 highest-impact fixes — not a feel-good number that hides what's broken.

---

## 🔍 Demonstration — what an audit actually looks like

> **You:** `audit acme-widgets.com's GEO`
>
> **GEO Agent:** _fetching homepage, robots.txt, llms.txt… running 12 checks… corroborating via web search…_

### GEO Audit — https://acme-widgets.com

| Check | Status | Reason | Fix |
|---|---|:---:|---|
| **robots** | 🟡 partial | Crawlers allowed only via bare `*` wildcard; `OAI-SearchBot`, `ClaudeBot`, `PerplexityBot` not named | Add explicit `User-agent` allow rules for the three citation bots |
| **llms_txt** | 🔴 fail | No `/llms.txt` found _(speculative signal — weight low)_ | Add a short markdown `llms.txt` describing the site + key links |
| **schema** | 🟡 partial | `Organization` JSON-LD present but thin (name + url only) | Add `sameAs`, `logo`, `description`, `founder` fields |
| **meta** | 🟢 pass | Title, description, canonical and OG tags all present | — |
| **content** | 🟢 pass | H1 + real H2/H3 hierarchy, ~900 words, stats cited | — |
| **question_shaped_headings** | 🔴 fail | Headings are taglines ("Our Technology"), not questions | Reframe as "What is a smart widget?", "How does X work?" |
| **signals** | 🟡 partial | `<html lang>` set, but no visible last-updated date or feed | Expose `dateModified` in schema; add an RSS feed |
| **ai_discovery** | ⚪ n/a | Emerging `/.well-known/ai.txt` convention — low priority | Optional; skip until adoption is confirmed |
| **negative_signals** | 🟡 partial | Page leans on "Buy now" CTAs; no author attribution | Add a byline / `Person` schema; balance promo vs. substance |
| **brand_entity** | 🔴 fail | No `sameAs` links to Wikipedia/LinkedIn/Crunchbase | Link the brand's authoritative profiles from the footer |
| **injection** | 🟢 pass | No hidden text or AI-directed instructions found | — |
| **corroboration** _(agent)_ | 🟡 partial | Brand appears on its own site + one directory; no independent reviews | Earn third-party mentions (reviews, comparison articles) |

**Top 3 fixes, ranked by impact:**
1. **Name the citation bots in `robots.txt`** — a wildcard is not a guarantee; `OAI-SearchBot`/`ClaudeBot`/`PerplexityBot` feed live AI-answer citations.
2. **Rewrite headings as real questions** — AI engines match the phrasing users actually type; taglines don't.
3. **Build entity authority** — add `sameAs` profile links + earn independent corroboration so engines trust the brand as a source.

> _The table above is an illustrative example of the output shape. Run it on your own site for real numbers._

---

## 📋 What gets checked

| # | Check | What it asks |
|---|---|---|
| 1 | `robots` | Are the AI **citation** crawlers (OAI-SearchBot, ClaudeBot, PerplexityBot) allowed — by name, not just `*`? |
| 2 | `llms_txt` | Is there a well-formed `/llms.txt`? _(weak, speculative signal)_ |
| 3 | `schema` | Is there rich JSON-LD (Organization/WebSite/FAQ/Product), or just a thin stub? |
| 4 | `meta` | Title, description, canonical, OG tags — and no `noai` directive blocking AI use |
| 5 | `content` | Real H1→H2→H3 hierarchy, enough substance, concrete claims and citations |
| 6 | `question_shaped_headings` | Do headings match the questions people ask an AI? |
| 7 | `signals` | Language attribute + freshness (last-updated date, RSS feed) |
| 8 | `ai_discovery` | Emerging `ai.txt` / `ai/*.json` endpoints _(low priority)_ |
| 9 | `negative_signals` | Thin content, keyword stuffing, promo overload, no author, dead links |
| 10 | `brand_entity` | E-E-A-T: consistent brand, `sameAs` links, About/Team page |
| 11 | `injection` | Cloaking / hidden text / prompt-injection aimed at AI readers |
| 12 | `corroboration` | Do independent third-party sources back the site's claims? _(live web search)_ |

---

## 🚀 Install

Run from **inside the project** you want the agent available in:

```bash
curl -fsSL https://raw.githubusercontent.com/MrStark0701/geo-agent/main/install.sh | bash
```

That's the whole install — it drops `GeoAgent.md` into `./.claude/agents/`, where Claude Code auto-discovers it. No restart, no registration. Check it into your repo to share it with your team. Run it again in another project to install a separate copy.

**No Python, no venv, no dependency — `curl` is the only requirement.**

Prefer to grab the file directly?

```bash
mkdir -p .claude/agents
curl -fsSL https://raw.githubusercontent.com/MrStark0701/geo-agent/main/agents/GeoAgent.md -o .claude/agents/GeoAgent.md
```

## ▶️ Use

In Claude Code, just ask:

- `audit stripe.com's GEO`
- `is my landing page cited-ready? here's the file: ./index.html`
- `audit acme.com's GEO with apply_mode — draft the rewritten headings too`

The `geo-agent` takes over: fetches the site, runs all 12 checks, corroborates via web search, and returns the table + ranked fixes. Point it at a **live URL**, a **local HTML file**, or **pasted copy** — domain-only checks come back `n/a` (not a false failure) when there's no live site.

## 📄 License

MIT (see `LICENSE`). `agents/GeoAgent.md`'s check rubric was informed by
[Auriti-Labs/geo-optimizer-skill](https://github.com/Auriti-Labs/geo-optimizer-skill) (MIT) — see
`NOTICE` and `THIRD_PARTY_LICENSES/`.
