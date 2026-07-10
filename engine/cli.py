"""Entrypoint: `python -m engine.cli <url>` or `--file <path>` / `--stdin`.

Prints exactly one JSON object to stdout (fetch metadata + checks list) and nothing else -
diagnostics go to stderr only, so the agent's Bash-output parsing stays trivial. `--self-test`
verifies imports/module wiring with zero network calls, so install.sh's exit-code gate doesn't
depend on internet reachability beyond the install steps already completed.

Top-level try/except here is a last-resort safety net only - each check module guards itself
early per the resilience pattern in orchestrator.py; this is belt-and-suspenders, not the
primary defense.
"""

from __future__ import annotations

import argparse
import json
import sys


def _self_test() -> int:
    try:
        from . import orchestrator  # noqa: F401
        from .checks import ai_discovery, brand_entity, content, injection, llms_txt, meta, negative_signals, robots, schema, signals  # noqa: F401
    except Exception as exc:  # pragma: no cover - defensive
        print(f"self-test import failure: {exc}", file=sys.stderr)
        return 1
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="geo-audit", description="Audit a website's GEO readiness.")
    parser.add_argument("url", nargs="?", help="URL to audit (live mode)")
    parser.add_argument("--file", help="Path to a local HTML file to audit (no live URL required)")
    parser.add_argument("--stdin", action="store_true", help="Read HTML from stdin")
    parser.add_argument("--self-test", action="store_true", help="Verify install with zero network calls")
    args = parser.parse_args(argv)

    if args.self_test:
        return _self_test()

    if not args.url and not args.file and not args.stdin:
        print("error: provide a URL, --file <path>, or --stdin", file=sys.stderr)
        return 2

    try:
        from . import orchestrator

        if args.file:
            with open(args.file, encoding="utf-8", errors="replace") as f:
                html = f.read()
            result = orchestrator.run_audit(html=html)
        elif args.stdin:
            html = sys.stdin.read()
            result = orchestrator.run_audit(html=html)
        else:
            result = orchestrator.run_audit(url=args.url)

        print(json.dumps(result.to_dict(), indent=2))
        return 0
    except Exception as exc:  # last-resort safety net, not the primary defense (see module docstring)
        print(json.dumps({"error": f"unexpected engine failure: {exc}", "checks": []}))
        print(f"engine error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
