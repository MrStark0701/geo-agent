"""Check: meta tags (title, description, canonical, noai, Open Graph).

Ported from the reference's audit_meta.py.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..models import CheckResult


@dataclass
class MetaFacts:
    has_title: bool = False
    title_text: str = ""
    has_description: bool = False
    description_text: str = ""
    has_canonical: bool = False
    has_noai: bool = False
    noai_value: str = ""
    has_og_title: bool = False
    has_og_description: bool = False
    has_og_image: bool = False


def collect_meta(soup) -> MetaFacts:
    facts = MetaFacts()
    if soup is None:
        return facts

    title_tag = soup.find("title")
    if title_tag and title_tag.text.strip():
        facts.has_title = True
        facts.title_text = title_tag.text.strip()

    desc = soup.find("meta", attrs={"name": "description"})
    if desc and (desc.get("content") or "").strip():
        facts.has_description = True
        facts.description_text = desc["content"].strip()

    canonical = soup.find("link", attrs={"rel": "canonical"})
    if canonical and canonical.get("href"):
        facts.has_canonical = True

    robots_meta = soup.find("meta", attrs={"name": lambda n: n and n.lower() == "robots"})
    if robots_meta:
        content = (robots_meta.get("content") or "").lower()
        if "noai" in content or "noimageai" in content:
            facts.has_noai = True
            facts.noai_value = robots_meta.get("content", "")

    if soup.find("meta", attrs={"property": "og:title"}, content=True):
        facts.has_og_title = True
    if soup.find("meta", attrs={"property": "og:description"}, content=True):
        facts.has_og_description = True
    if soup.find("meta", attrs={"property": "og:image"}, content=True):
        facts.has_og_image = True

    return facts


def grade_meta(facts: MetaFacts) -> CheckResult:
    if not facts.has_title or facts.has_noai:
        reason = "missing <title>" if not facts.has_title else f"noai directive present: {facts.noai_value}"
        fix = "Add a descriptive <title> tag." if not facts.has_title else "Remove the noai/noimageai robots directive to allow AI use of this content."
        return CheckResult(check="meta", status="fail", reason=reason, fix=fix)

    missing = []
    if not facts.has_description:
        missing.append("meta description")
    if not facts.has_canonical:
        missing.append("canonical link")
    if not (facts.has_og_title and facts.has_og_description):
        missing.append("Open Graph tags")

    if not missing:
        return CheckResult(check="meta", status="pass", reason="title, description, canonical, and OG tags all present", fix="")

    if len(missing) <= 1:
        return CheckResult(
            check="meta",
            status="partial",
            reason=f"missing: {', '.join(missing)}",
            fix=f"Add {' and '.join(missing)}.",
        )

    return CheckResult(
        check="meta",
        status="fail" if len(missing) >= 3 else "partial",
        reason=f"missing: {', '.join(missing)}",
        fix=f"Add {', '.join(missing)}.",
    )
