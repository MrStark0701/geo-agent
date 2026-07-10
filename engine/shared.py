"""Shared constants and helpers used by multiple check modules.

Bot registry trimmed from the reference's ~26 entries to the ~10 that matter for GEO (training
vs. citation-bot distinction was already flagged as a needed fix before this project started -
see CLAUDE.md). Thresholds and small helpers below are ported close to verbatim from the
reference repo (Auriti-Labs/geo-optimizer-skill, MIT) - see NOTICE for the full list of what's
a close port vs. original code.
"""

from __future__ import annotations

# ─── AI bot registry (trimmed) ────────────────────────────────────────────────

AI_BOTS: dict[str, str] = {
    "GPTBot": "OpenAI (ChatGPT training)",
    "OAI-SearchBot": "OpenAI (ChatGPT search citations)",
    "ChatGPT-User": "OpenAI (ChatGPT on-demand fetch)",
    "anthropic-ai": "Anthropic (Claude training)",
    "ClaudeBot": "Anthropic (Claude citations)",
    "PerplexityBot": "Perplexity AI (index builder)",
    "Google-Extended": "Google (Gemini training)",
    "Applebot-Extended": "Apple (AI training)",
    "Bingbot": "Microsoft (Bing/Copilot search)",
    "CCBot": "Common Crawl (used by many AI labs)",
}

# Search-tier bots that directly cite sources in AI answers - the ones that matter most for
# GEO, distinct from training-only crawlers like GPTBot/anthropic-ai/Google-Extended.
CITATION_BOTS: set[str] = {"OAI-SearchBot", "ClaudeBot", "PerplexityBot"}

# ─── Schema.org thresholds ─────────────────────────────────────────────────────

SCHEMA_JSONLD_MAX_BYTES = 512 * 1024  # skip scripts larger than 512 KiB
SCHEMA_RAW_SCHEMAS_CAP = 50  # max raw schemas stored per page

SCHEMA_RICHNESS_HIGH = 5  # avg >= 5 attrs -> rich (3)
SCHEMA_RICHNESS_MED = 4  # avg >= 4 attrs -> medium (2)
SCHEMA_RICHNESS_LOW = 3  # avg >= 3 attrs -> minimal (1)

ARTICLE_TYPES: frozenset[str] = frozenset(
    {"Article", "BlogPosting", "NewsArticle", "TechArticle", "ScholarlyArticle"}
)

SCHEMA_ORG_REQUIRED: dict[str, list[str]] = {
    "website": ["@context", "@type", "url", "name"],
    "webpage": ["@context", "@type", "url", "name"],
    "organization": ["@context", "@type", "name", "url"],
    "person": ["@context", "@type", "name"],
    "faqpage": ["@context", "@type", "mainEntity"],
    "article": ["@context", "@type", "headline", "author"],
    "breadcrumblist": ["@context", "@type", "itemListElement"],
    "product": ["@context", "@type", "name", "description"],
    "localbusiness": ["@context", "@type", "name", "address"],
    "webapplication": ["@context", "@type", "name", "url"],
}

# ─── Content / negative-signals thresholds ────────────────────────────────────

CONTENT_MIN_WORDS = 300
KEYWORD_STUFFING_THRESHOLD = 0.025
BOILERPLATE_RATIO_THRESHOLD = 0.6
MIXED_SIGNALS_WORD_THRESHOLD = 1000

# ─── AI-discovery endpoint thresholds ──────────────────────────────────────────

AI_DISCOVERY_SUMMARY_NAME_MIN_LEN = 3
AI_DISCOVERY_SUMMARY_DESC_MIN_LEN = 20
AI_DISCOVERY_FAQ_QUESTION_MIN_LEN = 10
AI_DISCOVERY_FAQ_ANSWER_MIN_LEN = 20
AI_DISCOVERY_SERVICE_NAME_MIN_LEN = 3

# ─── Brand-entity constants ─────────────────────────────────────────────────────

KG_PILLAR_DOMAINS: set[str] = {"wikipedia.org", "wikidata.org", "linkedin.com", "crunchbase.com"}

ABOUT_LINK_PATTERNS: list[str] = ["/about", "/team", "/company", "/mission", "/our-story", "/who-we-are"]

BRAND_LEGAL_SUFFIXES: frozenset[str] = frozenset(
    {
        "inc", "inc.", "incorporated", "ltd", "ltd.", "limited", "llc", "l.l.c.",
        "corp", "corp.", "corporation", "gmbh", "g.m.b.h.", "s.r.l.", "srl",
        "s.p.a.", "spa", "s.a.", "sa", "ag", "co", "co.", "plc", "pty", "pty.",
    }
)

# ─── Prompt-injection / cloaking thresholds ────────────────────────────────────

PROMPT_INJECTION_MAX_SAMPLES = 3
PROMPT_INJECTION_SAMPLE_MAX_LEN = 150
PROMPT_INJECTION_UNICODE_THRESHOLD = 5
PROMPT_INJECTION_COMMENT_MAX_LEN = 500
PROMPT_INJECTION_COMMENT_KEYWORDS = ["prompt:", "instruction:", "context:", "system:", "ai:", "llm:"]
MICROFONT_SIZE_THRESHOLD_PX = 2.0


# ─── Shared helpers ─────────────────────────────────────────────────────────────


def flatten_graph(raw_schema: dict) -> list[dict]:
    """Extract schemas from @graph if present, otherwise return as a single-item list."""
    if isinstance(raw_schema, dict) and "@graph" in raw_schema:
        graph = raw_schema["@graph"]
        return list(graph) if isinstance(graph, list) else [graph]
    return [raw_schema] if isinstance(raw_schema, dict) else []


def normalize_brand_name(name: str) -> str:
    """Normalize a brand name for comparison by stripping a trailing legal suffix.

    The suffix must appear as a standalone trailing token (preceded by a space) - it is not
    removed when it appears mid-name (e.g. "The Inc. Company" is unchanged).
    """
    normalized = name.strip().lower().rstrip(",")
    for suffix in BRAND_LEGAL_SUFFIXES:
        if normalized.endswith(" " + suffix):
            return normalized[: -(len(suffix) + 1)].strip()
    return normalized
