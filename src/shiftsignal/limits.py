"""Data limits: none when Shift Signal runs on your own computer, hard caps only on a public demo.

Run locally (standalone, inside a local Signal Hub or on an internal company server), the app imposes no limit on
file size, panel rows, items or bootstrap draws; the computer's memory is the limit. A public demo sets
``SIGNAL_PUBLIC=1`` and then every cap below protects the shared server. All caps live in this module and are read at
call time.
"""
from __future__ import annotations

import os

# Demo caps, applied only when SIGNAL_PUBLIC=1. They are the limits of the 1.0 release.
DEMO_MAX_UPLOAD_MB = 20
DEMO_MAX_ROWS = 250_000
DEMO_MAX_ITEMS = 100
DEMO_MAX_BOOTSTRAP_DRAWS = 5_000

DEMO_NOTE = "This is a limit of the public demo only; the downloadable Shift Signal app has no built-in limit."
MEMORY_MESSAGE = (
    "There is not enough memory on this computer for this file or analysis. Close other programs, aggregate daily "
    "rows to weeks or drop unrelated items, or run Shift Signal on a computer with more memory."
)


def is_public() -> bool:
    """True on a public demo (``SIGNAL_PUBLIC=1``); independent of Hub mode (``SIGNAL_HUB``)."""
    return os.environ.get("SIGNAL_PUBLIC") == "1"


def max_upload_bytes() -> int | None:
    return DEMO_MAX_UPLOAD_MB * 1024 * 1024 if is_public() else None


def max_rows() -> int | None:
    return DEMO_MAX_ROWS if is_public() else None


def max_items() -> int | None:
    return DEMO_MAX_ITEMS if is_public() else None


def max_bootstrap_draws() -> int | None:
    return DEMO_MAX_BOOTSTRAP_DRAWS if is_public() else None


def demo_limit(message: str) -> str:
    """A capped message: what was exceeded, plus the reminder that only the demo has the cap."""
    return f"{message} {DEMO_NOTE}"
