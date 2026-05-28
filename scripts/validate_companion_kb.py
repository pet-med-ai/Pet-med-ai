#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

try:
    from companion_animal_knowledge import load_index, load_companion_kb
except Exception as exc:
    raise SystemExit(f"FAIL import companion_animal_knowledge: {exc}") from exc


def main() -> int:
    try:
        index = load_index()
        kb = load_companion_kb()
    except Exception as exc:
        print(f"FAIL companion knowledge JSON validation: {exc}", file=sys.stderr)
        return 1

    expected = set(index.get("rules") or [])
    actual = set(kb.keys())
    if expected != actual:
        print(f"FAIL rules mismatch: expected={sorted(expected)}, actual={sorted(actual)}", file=sys.stderr)
        return 1

    for key in sorted(kb):
        rule = kb[key]
        print(
            f"OK {key}: red_flags={len(rule.get('red_flags') or [])}, "
            f"systems={len(rule.get('system_hints') or [])}, "
            f"questions={len(rule.get('questions') or [])}"
        )

    print(f"ALL COMPANION KB JSON RULES VALID: {index.get('version')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
