"""Orchestrator: collect deals -> Telegram alerts + landing page.

Per store:
  * first ever run                  -> seed silently, send one summary line
  * later runs                      -> alert on new or further-dropped items
The landing page always reflects the full current set of price-bearing deals
(event-only items like "sale page opened" go to Telegram but not the page).
"""
from __future__ import annotations

import html

from .adapters import shopify, url_watch
from .adapters.base import Deal
from .config import load_config
from .site import render
from .state import load_state, save_state
from .telegram import send

ADAPTERS = {"shopify": shopify, "url_watch": url_watch}
MAX_ALERTS_PER_RUN = 40
_SEEN_KEY = "__seen__"   # sentinel inside per-store state


def _deal_message(d: Deal) -> str:
    lines = [f"🛍 <b>{html.escape(d.store)}</b>", html.escape(d.product_title)]
    if d.note:
        lines.append(d.note)
    if d.size:
        lines.append(f"Размер: <b>{html.escape(d.size)}</b>")
    if d.price > 0:
        pct = d.discount_pct
        if pct:
            lines.append(
                f"💸 <b>{html.escape(d.money(d.price))}</b> "
                f"<s>{html.escape(d.money(d.compare_at_price))}</s> (−{pct}%)"
            )
        else:
            lines.append(f"Цена: <b>{html.escape(d.money(d.price))}</b>")
    if not d.note:  # event notes already embed the link
        lines.append(f'<a href="{html.escape(d.url)}">Открыть →</a>')
    return "\n".join(lines)


def main() -> None:
    cfg = load_config()
    default_tokens = cfg["size_tokens"]
    state = load_state()
    site_deals: list[Deal] = []

    for store in cfg["stores"]:
        if not store.get("enabled", True):
            continue
        adapter = ADAPTERS.get(store.get("adapter"))
        if adapter is None:
            print(f"[{store.get('name')}] unknown adapter: {store.get('adapter')}")
            continue

        name = store["name"]
        size_tokens = store.get("size_tokens") or default_tokens
        try:
            deals = adapter.collect(store, size_tokens)
        except Exception as exc:  # one bad store must not sink the run
            print(f"[{name}] adapter error: {exc}")
            continue

        site_deals.extend(d for d in deals if not d.is_event)
        prev = state.get(name, {})
        ever_seen = prev.pop(_SEEN_KEY, False)
        current: dict[str, int] = {}
        fresh: list[Deal] = []
        for d in deals:
            seen_price = prev.get(d.key)
            if seen_price is None or d.price < seen_price:
                fresh.append(d)
            current[d.key] = (min(d.price, seen_price)
                              if seen_price is not None else d.price)

        if not ever_seen:
            send(
                f"✅ <b>{html.escape(name)}</b>: мониторинг включён. "
                f"Сейчас в твоём размере со скидкой: <b>{len(deals)}</b>. "
                f"Дальше — только новое и подешевевшее."
            )
        else:
            for d in fresh[:MAX_ALERTS_PER_RUN]:
                send(_deal_message(d))
            if len(fresh) > MAX_ALERTS_PER_RUN:
                send(
                    f"…и ещё {len(fresh) - MAX_ALERTS_PER_RUN} новых в "
                    f"<b>{html.escape(name)}</b> (показал первые "
                    f"{MAX_ALERTS_PER_RUN})."
                )
        state[name] = {**current, _SEEN_KEY: True}
        print(f"[{name}] deals={len(deals)} new={len(fresh)} "
              f"ever_seen={ever_seen}")

    render(site_deals)
    save_state(state)


if __name__ == "__main__":
    main()
