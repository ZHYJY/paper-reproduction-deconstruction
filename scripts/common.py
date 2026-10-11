#!/usr/bin/env python3
"""Shared helpers for the paper-reproduction-deconstruction scripts.

Scripts in this directory can either be run standalone (they keep their own
minimal implementations where needed) or import these helpers. Helpers never
depend on third-party packages so they work on any Python 3.9+.
"""
from __future__ import annotations
import hashlib
from datetime import datetime, timezone
from pathlib import Path

CHUNK = 1024 * 1024


def sha256(path: Path, chunk: int = CHUNK) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(chunk), b""):
            digest.update(block)
    return digest.hexdigest()


def digest_or_none(path: Path) -> str | None:
    if not path.is_file():
        return None
    return sha256(path)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def write_json(path: Path, payload: dict) -> None:
    import json
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def is_within(child: Path, root: Path) -> bool:
    """True if child is root itself or strictly inside root."""
    return child == root or root in child.parents


def to_posix(relative_or_absolute: Path, root: Path) -> str:
    return relative_or_absolute.relative_to(root).as_posix()
