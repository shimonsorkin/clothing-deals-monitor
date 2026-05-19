# clothing-deals-monitor

Watches favourite clothing stores and pings **Telegram** the moment something
**in my size** goes **on sale** — plus a self-updating **landing page** with all
current matches. Runs free on **GitHub Actions cron**. No server.

```
GitHub Actions (every ~15 min)
   └─ python -m monitor.run
        ├─ adapters/  → fetch each store, filter by size + discount
        ├─ Telegram   → alert only on new / further-dropped items
        └─ docs/      → rebuild landing page (served by GitHub Pages)
   └─ commit state/ + docs/ back to the repo
```

Add a store = edit `config.yaml`. No code change for Shopify stores.

## Stores

| Store | Platform | Adapter | Notes |
|---|---|---|---|
| Pini Parma | Shopify | `shopify` | sale collections `fw25-sale`, `archives` |
| Natalino | Shopify | `shopify` | no sale collection — scans `all`, filters by discount |
| Anglo-Italian | Shopify | `shopify` | same — `/collections/sale` is currently empty |
| Grandlemar | Shopify | `shopify` | `the-archive` sale; `contains` match mode; blocks jacket/coat product types |
| Cavour | headless (Brink/Shoplab) | `url_watch` | rare-sale brand → pings when `/sale` opens (no per-size data available without a browser) |

### Per-store config knobs

* `size_tokens` — override the global default for that store.
* `match_mode: prefix` (default) or `contains` — prefix is safer (avoids `XS`
  matching `S`); contains is required when the wanted size sits mid-string
  (e.g. Grandlemar `"W28 L32 (US) / 46 (EU)"`).
* `require_discount: true` — only alert when `compare_at_price > price`.
* `sale_collections` — list of Shopify collection handles; defaults to `["all"]`.
* `product_types_block` — substring blocklist over Shopify `type` + `tags`
  (case-insensitive). Use for stores where the same size token would otherwise
  bleed across categories you don't want (e.g. trouser-size `"46 (EU)"` also
  matching jacket chest sizes).

### Sizing primer (whitespace collapsed + lowercased, then matched)

| Token | Matches | Doesn't match |
|---|---|---|
| `"46 (IT)"` (prefix) | `"46 (IT) / 40(FR) / 30(UK-US)"` | `"46 (IT-EU) / 36 (US-UK)"` (jacket) |
| `"S /"` (prefix) | `"S / 44-46 (IT-EU)…"` | `"S/M"` cap, `"XS / …"`, `"XXL / …"` |
| `"S"` (prefix) | exact `"S"` | `"XS"`, `"Small"` (use `"Small"` token) |
| `"46 (EU)"` (contains) | `"W28 L32 (US) / 46 (EU)"` | `"45 (EU)"` |

## One-time setup (≈10 min, human steps)

1. **GitHub repo.** Create a repo, push this folder to `main`.
2. **Telegram bot.** Message **@BotFather** → `/newbot` → copy the **bot token**.
   Message your new bot once (say "hi"), then open
   `https://api.telegram.org/bot<TOKEN>/getUpdates` and copy your numeric
   **chat id** (`message.chat.id`). (Or message **@userinfobot**.)
3. **Secrets.** Repo → Settings → Secrets and variables → Actions → add
   `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID`.
4. **Landing page.** Repo → Settings → Pages → Source: *Deploy from a branch*,
   Branch: `main`, Folder: `/docs`. URL appears there after the first run.
5. **Run it.** Repo → Actions → *clothing-deals-monitor* → **Run workflow**.
   First run sends one summary line per store (no spam) and publishes the page.

> The scheduled workflow stays alive because every run commits to the repo
> (GitHub disables cron only after 60 days of *no* repo activity).

### Privacy / GitHub Pages note

GitHub Pages on the **Free** plan requires the **repo to be public**. The repo
holds only code + a list of on-sale items; **secrets live in Actions Secrets,
never in the repo**, so the bot token is safe either way. To keep the repo
private you need GitHub **Pro** (private Pages), or host `docs/` on
Cloudflare Pages / Netlify (also free). Pick at setup.

## Test locally before trusting it

```bash
pip install -r requirements.txt
DRY_RUN=1 python -m monitor.run        # prints alerts instead of sending
open docs/index.html                   # inspect the generated page
```

`DRY_RUN=1` hits the live stores but prints Telegram messages to stdout — use
it to confirm the size filter and prices look right on real data.
