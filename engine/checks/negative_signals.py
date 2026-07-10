"""Check: negative signals that reduce AI citability.

Ported from the reference's audit_negative.py: CTA density, popups, thin content, broken
links, keyword stuffing, missing author signal, boilerplate ratio, mixed signals.
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field

from .content import ContentFacts
from .meta import MetaFacts
from .schema import SchemaFacts
from .. import shared
from ..models import CheckResult
from ..shared import flatten_graph

_CTA_RE = re.compile(
    r"\b(buy now|sign up|subscribe|get started|free trial|order now|"
    r"act now|limited time|don.t miss|hurry)\b",
    re.IGNORECASE,
)
_POPUP_CLASSES = ["modal", "popup", "overlay", "interstitial", "lightbox", "cookie-banner"]
_POPUP_DATA_ATTRS = ["data-modal", "data-popup", "data-overlay"]
_STOP_WORDS = {
    "the", "a", "an", "is", "are", "was", "were", "be", "been", "and", "or", "but", "in", "on",
    "at", "to", "for", "of", "with", "it", "this", "that", "not", "no", "as", "by", "from",
}
_WORD_RE = re.compile(r"\b[a-zA-Z]{4,}\b")
_COMPLEX_H1_PATTERNS = ["guide", "tutorial", "how to", "complete", "definitive", "everything"]
_BIG_PROMISE_WORDS = ["complete", "ultimate", "comprehensive", "everything", "in-depth"]


@dataclass
class NegativeSignalsFacts:
    checked: bool = False
    cta_count: int = 0
    cta_density_high: bool = False
    popup_indicators: list[str] = field(default_factory=list)
    has_popup_signals: bool = False
    is_thin_content: bool = False
    broken_links_count: int = 0
    has_broken_links: bool = False
    has_keyword_stuffing: bool = False
    stuffed_word: str = ""
    stuffed_density: float = 0.0
    has_author_signal: bool = False
    boilerplate_ratio: float = 0.0
    boilerplate_high: bool = False
    has_mixed_signals: bool = False
    mixed_signal_detail: str = ""
    signals_found: int = 0
    severity: str = "clean"


def collect_negative_signals(
    soup, content_facts: ContentFacts, meta_facts: MetaFacts, schema_facts: SchemaFacts
) -> NegativeSignalsFacts:
    facts = NegativeSignalsFacts()
    if soup is None:
        return facts
    facts.checked = True

    text = soup.get_text(separator=" ", strip=True)

    # 1. CTA density
    cta_matches = _CTA_RE.findall(text)
    facts.cta_count = len(cta_matches)
    word_count = content_facts.word_count or max(len(text.split()), 1)
    if facts.cta_count > 5 or (facts.cta_count / word_count > 0.01):
        facts.cta_density_high = True

    # 2. Popup/interstitial
    for cls in _POPUP_CLASSES:
        if soup.find_all(attrs={"class": lambda c, _cls=cls: c and _cls in str(c).lower()}):
            facts.popup_indicators.append(cls)
    for attr in _POPUP_DATA_ATTRS:
        if soup.find(attrs={attr: True}):
            facts.popup_indicators.append(attr)
    facts.has_popup_signals = bool(facts.popup_indicators)

    # 3. Thin content
    if content_facts.word_count < shared.CONTENT_MIN_WORDS:
        h1 = content_facts.h1_text.lower() if content_facts.h1_text else ""
        if any(p in h1 for p in _COMPLEX_H1_PATTERNS) or content_facts.heading_count >= 3:
            facts.is_thin_content = True

    # 4. Broken/empty links
    broken = 0
    for a_tag in soup.find_all("a", href=True):
        href = a_tag["href"].strip()
        if href in ("", "#", "javascript:void(0)", "javascript:;", "javascript:void(0);"):
            broken += 1
    facts.broken_links_count = broken
    facts.has_broken_links = broken > 3

    # 5. Keyword stuffing
    words = _WORD_RE.findall(text.lower())
    if len(words) > 50:
        freq = Counter(w for w in words if w not in _STOP_WORDS)
        total = len(words)
        for word, count in freq.most_common(3):
            density = count / total
            if density > shared.KEYWORD_STUFFING_THRESHOLD and count >= 5:
                facts.has_keyword_stuffing = True
                facts.stuffed_word = word
                facts.stuffed_density = round(density * 100, 1)
                break

    # 6. Missing author signal
    for raw_schema in schema_facts.raw_schemas:
        for s in flatten_graph(raw_schema):
            s_type = s.get("@type", "")
            s_type = s_type[0] if isinstance(s_type, list) and s_type else s_type
            if s_type == "Person" or s.get("author"):
                facts.has_author_signal = True
                break
        if facts.has_author_signal:
            break
    if not facts.has_author_signal and (
        soup.find("a", rel="author") or soup.find(attrs={"class": lambda c: c and "author" in str(c).lower()})
    ):
        facts.has_author_signal = True

    # 7. Boilerplate ratio
    main_content = soup.find("main") or soup.find("article") or soup.find(attrs={"role": "main"})
    total_text_len = len(text)
    if main_content and total_text_len > 0:
        main_text_len = len(main_content.get_text(separator=" ", strip=True))
        facts.boilerplate_ratio = round(1.0 - (main_text_len / total_text_len), 2)
    elif total_text_len > 0:
        nav_footer_len = sum(
            len(tag.get_text(separator=" ", strip=True)) for tag in soup.find_all(["nav", "footer", "header"])
        )
        if nav_footer_len > 0:
            facts.boilerplate_ratio = round(nav_footer_len / total_text_len, 2)
    facts.boilerplate_high = facts.boilerplate_ratio > shared.BOILERPLATE_RATIO_THRESHOLD

    # 8. Mixed signals
    h1 = content_facts.h1_text.lower() if content_facts.h1_text else ""
    if any(w in h1 for w in _BIG_PROMISE_WORDS) and content_facts.word_count < shared.MIXED_SIGNALS_WORD_THRESHOLD:
        facts.has_mixed_signals = True
        facts.mixed_signal_detail = f"H1 promises depth but only {content_facts.word_count} words"

    negatives = [
        facts.cta_density_high,
        facts.has_popup_signals,
        facts.is_thin_content,
        facts.has_broken_links,
        facts.has_keyword_stuffing,
        not facts.has_author_signal,
        facts.boilerplate_high,
        facts.has_mixed_signals,
    ]
    facts.signals_found = sum(negatives)
    if facts.signals_found >= 4:
        facts.severity = "high"
    elif facts.signals_found >= 2:
        facts.severity = "medium"
    elif facts.signals_found >= 1:
        facts.severity = "low"
    else:
        facts.severity = "clean"

    return facts


def grade_negative_signals(facts: NegativeSignalsFacts) -> CheckResult:
    if not facts.checked:
        return CheckResult(check="negative_signals", status="fail", reason="could not analyze page content", fix="")

    reasons = []
    fixes = []
    if facts.cta_density_high:
        reasons.append(f"{facts.cta_count} CTAs (excessive)")
        fixes.append("reduce promotional CTA density")
    if facts.has_popup_signals:
        reasons.append(f"popup/modal indicators ({', '.join(facts.popup_indicators)})")
        fixes.append("remove or reduce popups/modals that obscure content")
    if facts.is_thin_content:
        reasons.append("thin content relative to what the H1 promises")
        fixes.append("expand content to match the H1's promised depth")
    if facts.has_broken_links:
        reasons.append(f"{facts.broken_links_count} broken/empty links")
        fixes.append("fix or remove broken/empty href links")
    if facts.has_keyword_stuffing:
        reasons.append(f"keyword stuffing ('{facts.stuffed_word}' at {facts.stuffed_density}% density)")
        fixes.append("reduce repetition of over-used keywords")
    if not facts.has_author_signal:
        reasons.append("no author/Person schema signal")
        fixes.append("add author attribution (rel=author, Person schema, or byline)")
    if facts.boilerplate_high:
        reasons.append(f"high boilerplate ratio ({facts.boilerplate_ratio})")
        fixes.append("increase substantive content relative to nav/footer/header")
    if facts.has_mixed_signals:
        reasons.append(facts.mixed_signal_detail)
        fixes.append("either expand content or tone down the H1's promised depth")

    if facts.severity == "clean":
        return CheckResult(check="negative_signals", status="pass", reason="no negative citability signals detected", fix="")

    status = "fail" if facts.severity == "high" else "partial"
    return CheckResult(
        check="negative_signals",
        status=status,
        reason=f"{facts.signals_found} negative signal(s) found ({facts.severity}): {'; '.join(reasons)}",
        fix="; ".join(fixes),
    )
