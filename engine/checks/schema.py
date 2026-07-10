"""Check: JSON-LD structured data (rubric item 4, structured data).

Ported from the reference's audit_schema.py. Operates only on the already-parsed `soup` - runs
identically in URL mode and local-file mode (schema validity doesn't depend on a live domain).
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Any

from .. import shared
from ..models import CheckResult

_logger = logging.getLogger(__name__)

_GENERIC_KEYS = {"@context", "@type", "@id"}


@dataclass
class SchemaFacts:
    found_types: list[str] = field(default_factory=list)
    raw_schemas: list[dict[str, Any]] = field(default_factory=list)
    has_website: bool = False
    has_organization: bool = False
    has_faq: bool = False
    has_article: bool = False
    has_product: bool = False
    has_sameas: bool = False
    sameas_urls: list[str] = field(default_factory=list)
    has_date_modified: bool = False
    schema_richness_score: int = 0
    incomplete_schema_types: list[str] = field(default_factory=list)
    schema_missing_fields: dict[str, list[str]] = field(default_factory=dict)
    json_parse_errors: int = 0


def collect_schema(soup) -> SchemaFacts:
    facts = SchemaFacts()
    if soup is None:
        return facts

    scripts = soup.find_all("script", attrs={"type": "application/ld+json"})
    for script in scripts:
        raw = script.string or script.get_text()
        if not raw or not raw.strip():
            continue
        if len(raw) > shared.SCHEMA_JSONLD_MAX_BYTES:
            _logger.debug("JSON-LD too large (%d bytes), skipping", len(raw))
            continue
        try:
            data = json.loads(raw)
        except (json.JSONDecodeError, TypeError) as exc:
            _logger.debug("Invalid JSON-LD ignored: %s", exc)
            facts.json_parse_errors += 1
            continue

        if isinstance(data, dict) and "@graph" in data:
            root_context = data.get("@context")
            raw_items = data["@graph"] if isinstance(data["@graph"], list) else [data["@graph"]]
            schemas = []
            for item in raw_items:
                if isinstance(item, dict) and root_context and "@context" not in item:
                    item = {**item, "@context": root_context}
                schemas.append(item)
        elif isinstance(data, list):
            schemas = data
        else:
            schemas = [data]

        for schema_obj in schemas:
            if not isinstance(schema_obj, dict):
                continue
            if len(facts.raw_schemas) < shared.SCHEMA_RAW_SCHEMAS_CAP:
                facts.raw_schemas.append(schema_obj)

            schema_type = schema_obj.get("@type", "unknown")
            types = schema_type if isinstance(schema_type, list) else [schema_type]
            for t in types:
                facts.found_types.append(t)
                if t == "WebSite":
                    facts.has_website = True
                elif t == "FAQPage":
                    facts.has_faq = True
                elif t in shared.ARTICLE_TYPES:
                    facts.has_article = True
                elif t == "Organization":
                    facts.has_organization = True
                elif t == "Product":
                    facts.has_product = True

            same_as = schema_obj.get("sameAs", [])
            if isinstance(same_as, str):
                same_as = [same_as]
            if same_as:
                facts.has_sameas = True
                facts.sameas_urls.extend(same_as[:10])

            if schema_obj.get("dateModified"):
                facts.has_date_modified = True

    attr_counts = [
        len([k for k in schema_obj if k not in _GENERIC_KEYS]) for schema_obj in facts.raw_schemas
    ]
    if attr_counts:
        avg = sum(attr_counts) / len(attr_counts)
        if avg >= shared.SCHEMA_RICHNESS_HIGH:
            facts.schema_richness_score = 3
        elif avg >= shared.SCHEMA_RICHNESS_MED:
            facts.schema_richness_score = 2
        elif avg >= shared.SCHEMA_RICHNESS_LOW:
            facts.schema_richness_score = 1

    for schema_obj in facts.raw_schemas:
        schema_type_raw = schema_obj.get("@type", "unknown")
        types_to_check = schema_type_raw if isinstance(schema_type_raw, list) else [schema_type_raw]
        for t in types_to_check:
            t_lower = str(t).lower()
            if t_lower in shared.SCHEMA_ORG_REQUIRED:
                missing = [f for f in shared.SCHEMA_ORG_REQUIRED[t_lower] if f not in schema_obj]
                if missing and t not in facts.incomplete_schema_types:
                    facts.schema_missing_fields[t] = missing
                    facts.incomplete_schema_types.append(t)

    return facts


def grade_schema(facts: SchemaFacts) -> CheckResult:
    if not facts.raw_schemas:
        return CheckResult(
            check="schema",
            status="fail",
            reason="no JSON-LD structured data found",
            fix="Add Organization and WebSite JSON-LD schema at minimum; add FAQPage/Article/"
            "Product schema where relevant.",
        )

    if facts.json_parse_errors and not facts.found_types:
        return CheckResult(
            check="schema",
            status="fail",
            reason=f"{facts.json_parse_errors} JSON-LD script(s) found but all failed to parse",
            fix="Validate JSON-LD syntax (e.g. with Google's Rich Results Test).",
        )

    if (facts.has_website or facts.has_organization) and facts.schema_richness_score >= 2:
        reason = f"rich JSON-LD present (types: {', '.join(sorted(set(facts.found_types)))})"
        fix = ""
        if facts.incomplete_schema_types:
            first = facts.incomplete_schema_types[0]
            fix = f"Add missing fields to {first} schema: {', '.join(facts.schema_missing_fields[first])}."
        return CheckResult(check="schema", status="pass", reason=reason, fix=fix)

    reason = f"JSON-LD present but generic or thin (types: {', '.join(sorted(set(facts.found_types))) or 'none valid'})"
    fix = "Add more attributes to existing schema (aim for 5+ relevant fields per type)."
    if facts.incomplete_schema_types:
        first = facts.incomplete_schema_types[0]
        fix = f"Add missing fields to {first} schema: {', '.join(facts.schema_missing_fields[first])}."
    return CheckResult(check="schema", status="partial", reason=reason, fix=fix)
