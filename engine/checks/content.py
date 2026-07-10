"""Check: content quality (rubric items 1 & 2 as mechanical proxies, plus item 3 directly).

Ported from the reference's audit_content.py: H1/heading structure, word/number density,
external links, front-loading. PLUS an addition not in the reference: a question-shaped-heading
detector (interrogative words or a literal "?"), closing the rubric gap the reference's checks
didn't cover - "are H2/H3s phrased as the literal question a user would type into an AI chat."
"""

from __future__ import annotations

import copy
import re
from dataclasses import dataclass, field
from urllib.parse import urlparse

from ..models import CheckResult

_NUMBER_RE = re.compile(r"\b\d+[%€$£]|\b\d+\.\d+|\b\d{3,}\b")
_QUESTION_WORDS = ("who", "what", "when", "where", "why", "how", "which", "does", "is", "can", "should", "will")
_QUESTION_RE = re.compile(r"^\s*(?:" + "|".join(_QUESTION_WORDS) + r")\b", re.IGNORECASE)


@dataclass
class ContentFacts:
    has_h1: bool = False
    h1_text: str = ""
    heading_count: int = 0
    word_count: int = 0
    numbers_count: int = 0
    has_numbers: bool = False
    external_links_count: int = 0
    has_links: bool = False
    has_heading_hierarchy: bool = False
    has_lists_or_tables: bool = False
    has_front_loading: bool = False
    headings_h2_h3: list[str] = field(default_factory=list)
    question_shaped_headings: list[str] = field(default_factory=list)


def collect_content(soup, url: str, soup_clean=None) -> ContentFacts:
    facts = ContentFacts()
    if soup is None:
        return facts

    h1 = soup.find("h1")
    if h1:
        facts.has_h1 = True
        facts.h1_text = h1.text.strip()

    headings = soup.find_all(["h1", "h2", "h3", "h4"])
    facts.heading_count = len(headings)

    if soup_clean is None:
        soup_clean = copy.deepcopy(soup)
        for tag in soup_clean(["script", "style"]):
            tag.decompose()

    body_text = soup_clean.get_text(separator=" ", strip=True)
    numbers = _NUMBER_RE.findall(body_text)
    facts.numbers_count = len(numbers)
    facts.has_numbers = len(numbers) >= 3

    words = body_text.split()
    facts.word_count = len(words)

    base_domain = urlparse(url).netloc if url else ""
    all_links = soup.find_all("a", href=True)
    if base_domain:
        external = [a for a in all_links if a["href"].startswith("http") and base_domain not in a["href"]]
    else:
        external = [a for a in all_links if a["href"].startswith("http")]
    facts.external_links_count = len(external)
    facts.has_links = bool(external)

    h2_tags = soup_clean.find_all("h2")
    h3_tags = soup_clean.find_all("h3")
    facts.has_heading_hierarchy = bool(h2_tags and h3_tags)

    facts.has_lists_or_tables = bool(soup_clean.find_all(["ul", "ol", "table"]))

    if words:
        threshold_30 = max(len(words) * 30 // 100, 1)
        first_30pct = words[:threshold_30]
        if len(first_30pct) >= 50 and any(re.search(r"\d", w) for w in first_30pct):
            facts.has_front_loading = True

    for tag in h2_tags + h3_tags:
        text = tag.get_text(strip=True)
        if not text:
            continue
        facts.headings_h2_h3.append(text)
        if "?" in text or _QUESTION_RE.match(text):
            facts.question_shaped_headings.append(text)

    return facts


def grade_content(facts: ContentFacts) -> CheckResult:
    if not facts.has_h1 or facts.word_count < 100:
        reason = "no H1 found" if not facts.has_h1 else f"very thin content ({facts.word_count} words)"
        return CheckResult(
            check="content",
            status="fail",
            reason=reason,
            fix="Add an H1 and at least 300 words of substantive content.",
        )

    missing = []
    if facts.word_count < 300:
        missing.append(f"more content ({facts.word_count}/300 words)")
    if not facts.has_heading_hierarchy:
        missing.append("H2/H3 heading hierarchy")
    if not (facts.has_numbers or facts.has_links):
        missing.append("concrete stats or citation links")

    if not missing:
        detail = ""
        if not facts.question_shaped_headings:
            detail = " (note: no question-shaped headings found - see the separate reason below)"
        return CheckResult(
            check="content",
            status="pass",
            reason=f"H1 present, {facts.word_count} words, heading hierarchy and citable content present{detail}",
            fix="",
        )

    return CheckResult(
        check="content",
        status="partial",
        reason=f"H1 present but thin/unstructured (missing: {', '.join(missing)})",
        fix=f"Add {', '.join(missing)}.",
    )


def grade_question_headings(facts: ContentFacts) -> CheckResult:
    """Rubric item 3: are H2/H3s phrased as literal questions a user would type into an AI chat."""
    if not facts.headings_h2_h3:
        return CheckResult(
            check="question_shaped_headings",
            status="fail",
            reason="no H2/H3 headings found to evaluate",
            fix="Add H2/H3 headings, and phrase at least some as direct questions "
            "(e.g. 'How does X work?' rather than 'Our Technology').",
        )

    ratio = len(facts.question_shaped_headings) / len(facts.headings_h2_h3)
    if ratio >= 0.3:
        return CheckResult(
            check="question_shaped_headings",
            status="pass",
            reason=f"{len(facts.question_shaped_headings)}/{len(facts.headings_h2_h3)} headings are question-shaped",
            fix="",
        )
    if facts.question_shaped_headings:
        return CheckResult(
            check="question_shaped_headings",
            status="partial",
            reason=f"only {len(facts.question_shaped_headings)}/{len(facts.headings_h2_h3)} headings are question-shaped",
            fix="Rephrase more H2/H3 headings as the literal question a user would ask "
            "(e.g. 'What is X?', 'How do I do Y?').",
        )
    return CheckResult(
        check="question_shaped_headings",
        status="fail",
        reason="no headings are phrased as questions",
        fix="Rephrase key H2/H3 headings as literal questions a user would type into an AI chat.",
    )
