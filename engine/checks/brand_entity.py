"""Check: brand/entity identity signals (rubric item 6, E-E-A-T signals).

Ported from the reference's audit_brand.py: name consistency, Knowledge-Graph pillar links,
about/contact presence, hreflang, geo schema, FAQ depth, recent-articles signal.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field

from .content import ContentFacts
from .meta import MetaFacts
from .schema import SchemaFacts
from .. import shared
from ..models import CheckResult
from ..shared import flatten_graph, normalize_brand_name

_NAME_SEPARATORS = (" — ", " - ", " | ", " · ")


def _first_segment(text: str) -> str:
    for sep in _NAME_SEPARATORS:
        if sep in text:
            return text.split(sep)[0].strip()
    return text.strip()


@dataclass
class BrandEntityFacts:
    names_found: list[str] = field(default_factory=list)
    brand_name_consistent: bool = False
    kg_pillar_urls: list[str] = field(default_factory=list)
    has_wikipedia: bool = False
    has_wikidata: bool = False
    has_linkedin: bool = False
    has_crunchbase: bool = False
    kg_pillar_count: int = 0
    has_about_link: bool = False
    has_contact_info: bool = False
    hreflang_count: int = 0
    has_hreflang: bool = False
    has_geo_schema: bool = False
    faq_depth: int = 0
    has_recent_articles: bool = False


def collect_brand_entity(
    soup, schema_facts: SchemaFacts, meta_facts: MetaFacts, content_facts: ContentFacts
) -> BrandEntityFacts:
    facts = BrandEntityFacts()
    if soup is None:
        return facts

    names = []
    h1 = soup.find("h1")
    if h1 and h1.get_text(strip=True):
        names.append(_first_segment(h1.get_text(strip=True)))
    if meta_facts.title_text:
        names.append(_first_segment(meta_facts.title_text))
    og_title = soup.find("meta", property="og:title")
    if og_title and og_title.get("content"):
        names.append(_first_segment(og_title["content"]))
    for raw_schema in schema_facts.raw_schemas:
        for s in flatten_graph(raw_schema):
            s_type = s.get("@type", "")
            s_type = s_type[0] if isinstance(s_type, list) and s_type else s_type
            if s_type == "Organization" and s.get("name"):
                names.append(s["name"])

    facts.names_found = [n for n in names if n][:10]
    if len(names) >= 2:
        freq = Counter(normalize_brand_name(n) for n in names)
        _, most_common_count = freq.most_common(1)[0]
        facts.brand_name_consistent = most_common_count >= 2

    for url in schema_facts.sameas_urls:
        url_lower = url.lower()
        for domain in shared.KG_PILLAR_DOMAINS:
            if domain in url_lower:
                facts.kg_pillar_urls.append(url)
                if "wikipedia.org" in url_lower:
                    facts.has_wikipedia = True
                elif "wikidata.org" in url_lower:
                    facts.has_wikidata = True
                elif "linkedin.com" in url_lower:
                    facts.has_linkedin = True
                elif "crunchbase.com" in url_lower:
                    facts.has_crunchbase = True
                break
    facts.kg_pillar_count = sum([facts.has_wikipedia, facts.has_wikidata, facts.has_linkedin, facts.has_crunchbase])

    for a_tag in soup.find_all("a", href=True):
        href = a_tag["href"].lower()
        if any(p in href for p in shared.ABOUT_LINK_PATTERNS):
            facts.has_about_link = True
            break

    for raw_schema in schema_facts.raw_schemas:
        for s in flatten_graph(raw_schema):
            s_type = s.get("@type", "")
            s_type = s_type[0] if isinstance(s_type, list) and s_type else s_type
            if s_type == "Organization" and (s.get("address") or s.get("telephone") or s.get("email") or s.get("contactPoint")):
                facts.has_contact_info = True
            elif s_type == "Person" and (s.get("jobTitle") or s.get("hasCredential") or s.get("alumniOf")):
                facts.has_contact_info = True

    hreflang_tags = soup.find_all("link", attrs={"rel": "alternate", "hreflang": True})
    facts.hreflang_count = len(hreflang_tags)
    facts.has_hreflang = facts.hreflang_count > 0

    for raw_schema in schema_facts.raw_schemas:
        for s in flatten_graph(raw_schema):
            s_type = s.get("@type", "")
            s_type = s_type[0] if isinstance(s_type, list) and s_type else s_type
            if s_type == "LocalBusiness" or s.get("areaServed") or (s_type == "Organization" and s.get("address")):
                facts.has_geo_schema = True
                break

    for raw_schema in schema_facts.raw_schemas:
        for s in flatten_graph(raw_schema):
            s_type = s.get("@type", "")
            s_type = s_type[0] if isinstance(s_type, list) and s_type else s_type
            if s_type == "FAQPage":
                main_entity = s.get("mainEntity", [])
                if isinstance(main_entity, list):
                    facts.faq_depth += len(main_entity)

    facts.has_recent_articles = schema_facts.has_date_modified and (
        schema_facts.has_article or any(t in ("BlogPosting", "NewsArticle") for t in schema_facts.found_types)
    )

    return facts


def grade_brand_entity(facts: BrandEntityFacts) -> CheckResult:
    signals = [facts.brand_name_consistent, facts.kg_pillar_count > 0, facts.has_about_link]
    present = sum(signals)

    if present == 3:
        return CheckResult(
            check="brand_entity",
            status="pass",
            reason=f"brand name consistent, {facts.kg_pillar_count} Knowledge-Graph pillar link(s), about page linked",
            fix="",
        )

    missing = []
    if not facts.brand_name_consistent:
        missing.append("consistent brand naming across H1/title/OG/schema")
    if facts.kg_pillar_count == 0:
        missing.append("a sameAs link to Wikipedia, Wikidata, LinkedIn, or Crunchbase")
    if not facts.has_about_link:
        missing.append("an About/Team/Company page link")

    status = "partial" if present >= 1 else "fail"
    return CheckResult(
        check="brand_entity",
        status=status,
        reason=f"missing: {', '.join(missing)}",
        fix=f"Add {', '.join(missing)}.",
    )
