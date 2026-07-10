"""Check: freshness and language signals (rubric item 8, freshness signals).

Ported from the reference's audit_signals.py.
"""

from __future__ import annotations

from dataclasses import dataclass

from .schema import SchemaFacts
from ..models import CheckResult


@dataclass
class SignalsFacts:
    has_lang: bool = False
    lang_value: str = ""
    has_rss: bool = False
    has_freshness: bool = False
    freshness_date: str = ""


def collect_signals(soup, schema_facts: SchemaFacts) -> SignalsFacts:
    facts = SignalsFacts()
    if soup is None:
        return facts

    html_tag = soup.find("html")
    if html_tag:
        lang_val = (html_tag.get("lang") or "").strip()
        if lang_val:
            facts.has_lang = True
            facts.lang_value = lang_val

    rss_link = soup.find("link", attrs={"type": lambda t: t and ("rss" in t.lower() or "atom" in t.lower())})
    if rss_link:
        facts.has_rss = True

    for s in schema_facts.raw_schemas:
        date_mod = s.get("dateModified") or s.get("datePublished")
        if date_mod:
            facts.has_freshness = True
            facts.freshness_date = str(date_mod)
            break

    if not facts.has_freshness:
        meta_mod = soup.find("meta", attrs={"property": "article:modified_time"})
        if meta_mod and (meta_mod.get("content") or "").strip():
            facts.has_freshness = True
            facts.freshness_date = meta_mod["content"].strip()

    return facts


def grade_signals(facts: SignalsFacts) -> CheckResult:
    if not facts.has_lang:
        return CheckResult(
            check="signals",
            status="fail",
            reason="no lang attribute on <html>",
            fix='Add lang="en" (or the appropriate language code) to the <html> tag.',
        )

    if facts.has_rss or facts.has_freshness:
        extras = []
        if facts.has_rss:
            extras.append("RSS/Atom feed")
        if facts.has_freshness:
            extras.append(f"freshness date ({facts.freshness_date})")
        return CheckResult(
            check="signals",
            status="pass",
            reason=f"lang attribute present, plus {' and '.join(extras)}",
            fix="",
        )

    return CheckResult(
        check="signals",
        status="partial",
        reason="lang attribute present but no RSS feed or visible freshness/last-updated date",
        fix="Add a visible last-updated date (dateModified in schema or article:modified_time meta tag).",
    )
