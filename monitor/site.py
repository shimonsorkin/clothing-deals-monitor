"""Render the public landing page (docs/) served by GitHub Pages.

Writes:
  docs/index.html  — self-contained, no build step, no external assets
  docs/data.json   — same deals as data, for reuse / debugging
  docs/.nojekyll    — tell Pages to serve files as-is
Shows the *full current set* of matching discounted items every run.
"""
from __future__ import annotations

import html
import json
import pathlib
from datetime import datetime, timezone

from .adapters.base import Deal

_DOCS = pathlib.Path(__file__).resolve().parent.parent / "docs"

_PAGE = """<!doctype html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex, nofollow">
<title>Мои скидки</title>
<style>
  :root {{
    --bg:#faf8f5; --ink:#1a1714; --muted:#7c736a; --line:#e7e1d8;
    --card:#fffdfa; --accent:#9c1c2e;
  }}
  * {{ box-sizing:border-box; }}
  body {{
    margin:0; background:var(--bg); color:var(--ink);
    font:16px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;
  }}
  header {{
    padding:48px 24px 28px; border-bottom:1px solid var(--line); text-align:center;
  }}
  h1 {{
    margin:0; font:600 30px/1.2 Georgia,"Times New Roman",serif;
    letter-spacing:.01em;
  }}
  .sub {{ margin-top:8px; color:var(--muted); font-size:14px; }}
  .wrap {{ max-width:1180px; margin:0 auto; padding:24px; }}
  .filters {{
    display:flex; flex-wrap:wrap; gap:8px; justify-content:center;
    padding:18px 0 26px;
  }}
  .chip {{
    border:1px solid var(--line); background:var(--card); color:var(--ink);
    padding:7px 15px; border-radius:999px; font-size:13px; cursor:pointer;
    transition:.15s;
  }}
  .chip[aria-pressed="true"] {{
    background:var(--ink); color:var(--bg); border-color:var(--ink);
  }}
  .grid {{
    display:grid; gap:22px;
    grid-template-columns:repeat(auto-fill,minmax(240px,1fr));
  }}
  .card {{
    background:var(--card); border:1px solid var(--line); border-radius:10px;
    overflow:hidden; display:flex; flex-direction:column; text-decoration:none;
    color:inherit; transition:transform .15s, box-shadow .15s;
  }}
  .card:hover {{ transform:translateY(-3px); box-shadow:0 10px 26px rgba(0,0,0,.08); }}
  .ph {{ aspect-ratio:3/4; background:#efe9e0 center/cover no-repeat; }}
  .body {{ padding:14px 15px 17px; display:flex; flex-direction:column; gap:7px; flex:1; }}
  .store {{ font-size:11px; letter-spacing:.12em; text-transform:uppercase; color:var(--muted); }}
  .name {{ font:500 15px/1.35 Georgia,serif; }}
  .size {{ font-size:13px; color:var(--muted); }}
  .price {{ margin-top:auto; display:flex; align-items:baseline; gap:9px; flex-wrap:wrap; }}
  .now {{ font-weight:700; font-size:18px; }}
  .was {{ color:var(--muted); text-decoration:line-through; font-size:13px; }}
  .pct {{
    color:#fff; background:var(--accent); font-size:12px; font-weight:700;
    padding:2px 8px; border-radius:6px;
  }}
  .empty {{ text-align:center; color:var(--muted); padding:80px 0; }}
  footer {{ text-align:center; color:var(--muted); font-size:12px; padding:40px 0 60px; }}
</style>
</head>
<body>
<header>
  <h1>Мои скидки</h1>
  <div class="sub">Только мой размер · только со скидкой · обновлено {updated}</div>
</header>
<div class="wrap">
  <div class="filters" id="filters">{chips}</div>
  <div class="grid" id="grid">{cards}</div>
  {empty}
</div>
<footer>{count} позиций · автообновление каждые ~15 минут</footer>
<script>
  const grid = document.getElementById('grid');
  document.getElementById('filters').addEventListener('click', e => {{
    const chip = e.target.closest('.chip'); if (!chip) return;
    document.querySelectorAll('.chip').forEach(c =>
      c.setAttribute('aria-pressed', c === chip));
    const f = chip.dataset.store;
    grid.querySelectorAll('.card').forEach(card => {{
      card.style.display = (f === '*' || card.dataset.store === f) ? '' : 'none';
    }});
  }});
</script>
</body>
</html>
"""


def _card(deal: Deal) -> str:
    pct = deal.discount_pct
    img = (f'<div class="ph" style="background-image:url(\'{html.escape(deal.image)}\')"></div>'
           if deal.image else '<div class="ph"></div>')
    was = (f'<span class="was">{html.escape(deal.money(deal.compare_at_price))}</span>'
           if pct else '')
    pct_badge = f'<span class="pct">−{pct}%</span>' if pct else ''
    return (
        f'<a class="card" href="{html.escape(deal.url)}" target="_blank" rel="noopener" '
        f'data-store="{html.escape(deal.store)}">'
        f'{img}'
        f'<div class="body">'
        f'<div class="store">{html.escape(deal.store)}</div>'
        f'<div class="name">{html.escape(deal.product_title)}</div>'
        f'<div class="size">Размер: {html.escape(deal.size)}</div>'
        f'<div class="price"><span class="now">{html.escape(deal.money(deal.price))}</span>'
        f'{was}{pct_badge}</div>'
        f'</div></a>'
    )


def render(deals: list[Deal]) -> None:
    _DOCS.mkdir(parents=True, exist_ok=True)
    (_DOCS / ".nojekyll").write_text("", "utf-8")

    ordered = sorted(
        deals,
        key=lambda d: (-(d.discount_pct or 0), d.store, d.price),
    )
    stores = sorted({d.store for d in deals})

    chips = ['<button class="chip" data-store="*" aria-pressed="true">Все</button>']
    chips += [f'<button class="chip" data-store="{html.escape(s)}" '
              f'aria-pressed="false">{html.escape(s)}</button>' for s in stores]

    cards = "".join(_card(d) for d in ordered)
    empty = ('<div class="empty">Пока нет подходящих товаров со скидкой.</div>'
             if not ordered else '')
    updated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    (_DOCS / "index.html").write_text(
        _PAGE.format(
            updated=updated,
            chips="".join(chips),
            cards=cards,
            empty=empty,
            count=len(ordered),
        ),
        "utf-8",
    )
    (_DOCS / "data.json").write_text(
        json.dumps(
            {
                "updated": updated,
                "count": len(ordered),
                "deals": [
                    {
                        "store": d.store,
                        "title": d.product_title,
                        "size": d.size,
                        "url": d.url,
                        "price": d.price,
                        "compare_at_price": d.compare_at_price,
                        "discount_pct": d.discount_pct,
                        "currency": d.currency_symbol,
                        "image": d.image,
                    }
                    for d in ordered
                ],
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        "utf-8",
    )
