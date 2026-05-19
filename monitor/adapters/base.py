"""Shared types for store adapters."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Deal:
    store: str
    product_title: str
    size: str               # the matched variant option string, verbatim
    url: str                # canonical product URL
    price: int              # minor units (e.g. cents): 18900 == €189.00.
                            # Use 0 + `note` for event-only items (e.g. "sale
                            # section just opened") — these are sent to Telegram
                            # but excluded from the landing-page grid.
    compare_at_price: int | None
    currency_symbol: str
    image: str | None = None
    note: str | None = None  # optional message body for event-only items

    @property
    def is_event(self) -> bool:
        return self.price == 0 and self.compare_at_price is None

    @property
    def key(self) -> str:
        """Stable dedup key — independent of price, so price changes notify."""
        return f"{self.url}|{self.size}"

    @property
    def discount_pct(self) -> int | None:
        if self.compare_at_price and self.compare_at_price > self.price:
            return round((1 - self.price / self.compare_at_price) * 100)
        return None

    def money(self, minor: int | None) -> str:
        if minor is None:
            return ""
        return f"{self.currency_symbol}{minor / 100:,.2f}"
