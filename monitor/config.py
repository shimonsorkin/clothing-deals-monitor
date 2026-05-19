"""Load the YAML config that drives every store."""
from __future__ import annotations

import pathlib

import yaml

DEFAULT_PATH = pathlib.Path(__file__).resolve().parent.parent / "config.yaml"


def load_config(path: pathlib.Path | str = DEFAULT_PATH) -> dict:
    with open(path, "r", encoding="utf-8") as fh:
        cfg = yaml.safe_load(fh) or {}
    cfg.setdefault("size_tokens", [])
    cfg.setdefault("stores", [])
    return cfg
