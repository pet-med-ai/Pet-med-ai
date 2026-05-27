#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.exotic_knowledge import load_exotic_kb, load_index  # noqa: E402


def main() -> int:
    index = load_index()
    kb = load_exotic_kb()
    expected = set(index.get("rules") or [])
    actual = set(kb.keys())
    if expected != actual:
        raise SystemExit(f"rules mismatch: expected={sorted(expected)}, actual={sorted(actual)}")

    for key, rule in kb.items():
        print(
            f"OK {key}: "
            f"red_flags={len(rule.get('red_flags') or [])}, "
            f"systems={len(rule.get('system_hints') or [])}, "
            f"questions={len(rule.get('questions') or [])}"
        )

    print(f"ALL EXOTIC KB JSON RULES VALID: {index.get('version')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
