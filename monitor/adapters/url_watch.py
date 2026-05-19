"""Event adapter: ping when a watched URL transitions from "inactive" to "live".

Designed for headless / hard-to-scrape stores where per-size price monitoring
isn't practical, but the *event* of a sale section opening is itself valuable
(e.g. Cavour, which rarely discounts — when /sale comes alive, that *is* the
signal worth a Telegram ping).

Active = HTTP 200 AND, if `must_contain` is set, the response body contains
that substring. Otherwise inactive (404, 410, redirect to home, error).

Returns a synthetic Deal with price=0 (so the orchestrator dedups and the
landing page skips it) and a human-readable `note` for the Telegram body.
"""
from __future__ import annotations

import requests

from .base import Deal

_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)


def _is_active(url: str, must_contain: str | None) -> bool:
    try:
        resp = requests.get(url, headers={"User-Agent": _UA},
                            timeout=20, allow_redirects=False)
    except requests.RequestException:
        return False
    if resp.status_code != 200:
        return False
    if must_contain and must_contain.lower() not in resp.text.lower():
        return False
    return True


def collect(store: dict, size_tokens: list[str]) -> list[Deal]:
    deals: list[Deal] = []
    for watch in store.get("watches", []):
        if not _is_active(watch["url"], watch.get("must_contain")):
            continue
        deals.append(
            Deal(
                store=store["name"],
                product_title=watch.get("label", "Sale page is live"),
                size="",
                url=watch["url"],
                price=0,
                compare_at_price=None,
                currency_symbol="",
                image=None,
                note=watch.get(
                    "note",
                    f"🚨 Раздел открылся: <a href=\"{watch['url']}\">"
                    "посмотреть сейчас</a>",
                ),
            )
        )
    return deals
