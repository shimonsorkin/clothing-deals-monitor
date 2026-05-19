"""Telegram sender. One bot for the whole system.

Credentials come from env (GitHub Actions secrets):
  TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
Set DRY_RUN=1 to print messages instead of sending — useful for the first
local validation against live stores without spamming yourself.
"""
from __future__ import annotations

import os
import time

import requests

_API = "https://api.telegram.org/bot{token}/sendMessage"


def _creds() -> tuple[str, str]:
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        raise SystemExit(
            "TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID not set "
            "(or run with DRY_RUN=1 to print instead)."
        )
    return token, chat_id


def send(text: str) -> None:
    if os.environ.get("DRY_RUN"):
        print("--- TELEGRAM (dry-run) ---\n" + text + "\n")
        return
    token, chat_id = _creds()
    try:
        resp = requests.post(
            _API.format(token=token),
            json={
                "chat_id": chat_id,
                "text": text,
                "parse_mode": "HTML",
                "disable_web_page_preview": False,
            },
            timeout=20,
        )
        if resp.status_code != 200:
            print(f"Telegram error {resp.status_code}: {resp.text[:300]}")
    except requests.RequestException as exc:
        print(f"Telegram request failed: {exc}")
    time.sleep(0.05)  # stay well under Telegram's rate limit
