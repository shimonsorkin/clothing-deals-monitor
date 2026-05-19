"""Shopify storefront adapter — no API key, no scraping service needed.

Two-step, deliberately:
  1. /collections/<handle>/products.json?limit=250&page=N  -> enumerate handles
     (the list endpoint's variant objects are not authoritative for
      availability / compare_at_price across Shopify themes).
  2. /products/<handle>.js  -> authoritative per-variant `available`,
     `price`, `compare_at_price` (all integer minor units).

A variant counts as a deal for us when its size matches one of the
configured tokens, it is `available`, and (if require_discount) it is
actually marked down (compare_at_price > price).
"""
from __future__ import annotations

import time

import requests

from .base import Deal

_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)
_SESSION = requests.Session()
_SESSION.headers.update({"User-Agent": _UA, "Accept": "application/json"})

_MAX_PAGES = 20          # safety cap per collection
_PRODUCT_DELAY = 0.2     # polite gap between product fetches (seconds)


def _normalize(text: str) -> str:
    """Collapse whitespace to single spaces + casefold.

    We *keep* the spaces (not strip them) so the token "S /" matches
    "S / 44-46 (IT-EU)…" but NOT a "S/M" cap.
    """
    return " ".join(str(text).split()).casefold()


def _get_json(url: str, params: dict | None = None, retries: int = 2):
    for attempt in range(retries + 1):
        try:
            resp = _SESSION.get(url, params=params, timeout=20)
            if resp.status_code == 200:
                return resp.json()
            if resp.status_code == 404:
                return None
        except (requests.RequestException, ValueError):
            pass
        time.sleep(1.5 * (attempt + 1))
    return None


def _matched_size(variant: dict, norm_tokens: list[str], mode: str) -> str | None:
    """Return the human-readable size if any option value matches a token.

    mode="prefix"   : option startswith token after normalization (default).
                      Good for Pini Parma "46 (IT)", Natalino "S".
    mode="contains" : token appears anywhere in normalized option. Required
                      when the size we care about is mid-string, e.g. Grandlemar
                      "W28 L32 (US) / 46 (EU)" — token "46 (EU)" hits.
    """
    options = variant.get("options") or [variant.get("title", "")]
    matcher = (str.__contains__ if mode == "contains" else str.startswith)
    for opt in options:
        norm = _normalize(opt)
        if any(matcher(norm, tok) for tok in norm_tokens):
            return str(opt)
    return None


def _list_has_discount(product: dict) -> bool | None:
    """Cheap pre-filter from the list endpoint variants.

    Returns True if any variant looks marked down, False if list data proves
    nothing is, None if the list endpoint doesn't expose enough to decide
    (then the caller must fall back to the authoritative .js fetch).
    """
    variants = product.get("variants") or []
    if not variants or "compare_at_price" not in variants[0]:
        return None
    for v in variants:
        try:
            cap = float(v.get("compare_at_price") or 0)
            price = float(v.get("price") or 0)
        except (ValueError, TypeError):
            return None
        if cap > 0 and cap > price:
            return True
    return False


def _first_image(product: dict) -> str | None:
    img = product.get("featured_image")
    if not img:
        images = product.get("images") or []
        img = images[0] if images else None
    if isinstance(img, dict):
        img = img.get("src")
    if isinstance(img, str) and img.startswith("//"):
        img = "https:" + img
    return img if isinstance(img, str) else None


def _product_deals(base: str, handle: str, store: str,
                   norm_tokens: list[str], match_mode: str,
                   require_discount: bool, symbol: str,
                   block_types: list[str]) -> list[Deal]:
    data = _get_json(f"{base}/products/{handle}.js")
    if not data:
        return []
    # Substring-match against Shopify's `type` (and `tags`) — lets us exclude
    # whole categories like jackets/coats even when their size string contains
    # our token (e.g. Grandlemar jacket "36R (US) / 46 (EU)").
    haystack = (
        f"{data.get('type', '')} {' '.join(data.get('tags') or [])}".casefold()
    )
    if any(b for b in block_types if b in haystack):
        return []
    url = f"{base}/products/{handle}"
    image = _first_image(data)
    title = data.get("title", handle)
    out: list[Deal] = []
    for variant in data.get("variants", []):
        if not variant.get("available"):
            continue
        size = _matched_size(variant, norm_tokens, match_mode)
        if size is None:
            continue
        price = variant.get("price")
        if price is None:
            continue
        compare_at = variant.get("compare_at_price")
        if require_discount and not (compare_at and compare_at > price):
            continue
        out.append(
            Deal(
                store=store,
                product_title=title,
                size=size,
                url=url,
                price=int(price),
                compare_at_price=int(compare_at) if compare_at else None,
                currency_symbol=symbol,
                image=image,
            )
        )
    return out


def collect(store: dict, size_tokens: list[str]) -> list[Deal]:
    base = store["base_url"].rstrip("/")
    require_discount = store.get("require_discount", True)
    symbol = store.get("currency_symbol", "")
    match_mode = store.get("match_mode", "prefix")
    block_types = [b.casefold() for b in (store.get("product_types_block") or [])]
    norm_tokens = [_normalize(t) for t in size_tokens]

    # If a store has no dedicated sale collection (Natalino, Anglo-Italian),
    # scan "all" and rely on require_discount to filter — slower but works.
    collections = store.get("sale_collections") or ["all"]

    seen: set[str] = set()
    deals: list[Deal] = []
    for collection in collections:
        page = 1
        while page <= _MAX_PAGES:
            data = _get_json(
                f"{base}/collections/{collection}/products.json",
                params={"limit": 250, "page": page},
            )
            products = (data or {}).get("products") or []
            if not products:
                break
            for product in products:
                handle = product.get("handle")
                if not handle or handle in seen:
                    continue
                seen.add(handle)
                # When require_discount is on, skip a wasted .js fetch for
                # products the list endpoint proves are at full price.
                if require_discount and _list_has_discount(product) is False:
                    continue
                deals.extend(
                    _product_deals(base, handle, store["name"],
                                   norm_tokens, match_mode,
                                   require_discount, symbol, block_types)
                )
                time.sleep(_PRODUCT_DELAY)
            page += 1
    return deals
