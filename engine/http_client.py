"""Shared fetch layer for every outbound request the engine makes.

Hardening added during the plan's gap audit (none of this existed in the reference's fetch
layer, which both design reports flagged as a real gap): explicit timeout, a light retry on
connection/timeout errors, a hard response-size cap (stream-read, not buffered), and a
URL-scheme guard applied uniformly before any request is attempted.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from urllib.parse import urlparse

import requests

TIMEOUT_SECONDS = 15
MAX_RETRIES = 2
RETRY_BACKOFF_SECONDS = 1.0
MAX_RESPONSE_BYTES = 5 * 1024 * 1024  # 5 MiB — a malicious/pathological page must not balloon memory
USER_AGENT = "geo-agent/1.0 (+https://github.com/MrStark0701/geo-agent)"

ALLOWED_SCHEMES = {"http", "https"}


class InvalidURLScheme(ValueError):
    """Raised when a fetch is attempted against a non-http(s) URL (file://, data:, etc.)."""


@dataclass
class FetchResponse:
    status_code: int
    text: str
    truncated: bool = False


def _validate_scheme(url: str) -> None:
    scheme = urlparse(url).scheme.lower()
    if scheme not in ALLOWED_SCHEMES:
        raise InvalidURLScheme(f"refusing to fetch non-http(s) URL scheme: {scheme!r}")


def fetch_url(url: str) -> tuple[FetchResponse | None, str | None]:
    """Fetch a URL with timeout, light retry, and a response-size cap.

    Never raises for ordinary network failures - returns (None, error_message) so every
    caller can guard early and return its default result, matching the reference engine's
    "guard early, return default, never raise" resilience pattern. Raises only
    InvalidURLScheme, since a bad scheme is a caller bug, not a network condition.

    Returns:
        (FetchResponse, None) on success, (None, error_message) on failure.
    """
    _validate_scheme(url)

    last_error: str | None = None
    for attempt in range(MAX_RETRIES + 1):
        try:
            with requests.get(
                url,
                headers={"User-Agent": USER_AGENT},
                timeout=TIMEOUT_SECONDS,
                stream=True,
            ) as r:
                chunks: list[bytes] = []
                total = 0
                truncated = False
                for chunk in r.iter_content(chunk_size=64 * 1024):
                    if not chunk:
                        continue
                    total += len(chunk)
                    if total > MAX_RESPONSE_BYTES:
                        truncated = True
                        break
                    chunks.append(chunk)
                raw = b"".join(chunks)
                text = raw.decode(r.encoding or "utf-8", errors="replace")
                return FetchResponse(status_code=r.status_code, text=text, truncated=truncated), None
        except (requests.ConnectionError, requests.Timeout) as exc:
            last_error = str(exc)
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_BACKOFF_SECONDS * (attempt + 1))
                continue
        except requests.RequestException as exc:
            # Non-retryable request errors (e.g. too many redirects, invalid response).
            return None, str(exc)

    return None, last_error or "unknown fetch error"
