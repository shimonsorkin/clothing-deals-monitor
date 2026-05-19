"""Tiny JSON state store, committed back to the repo by the workflow.

Shape: { "<store name>": { "<deal key>": <lowest price seen, minor units> } }
A deal re-alerts only when its price drops below the lowest we have recorded,
so a permanent sale never spams and a deeper markdown still notifies.
"""
from __future__ import annotations

import json
import pathlib

STATE_PATH = pathlib.Path(__file__).resolve().parent.parent / "state" / "state.json"


def load_state() -> dict:
    if STATE_PATH.exists():
        try:
            return json.loads(STATE_PATH.read_text("utf-8")) or {}
        except json.JSONDecodeError:
            return {}
    return {}


def save_state(state: dict) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(
        json.dumps(state, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        "utf-8",
    )
