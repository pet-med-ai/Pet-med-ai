#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from companion_intake_templates import load_companion_intake_templates, load_intake_index  # noqa: E402


def main() -> int:
    index = load_intake_index()
    templates = load_companion_intake_templates()
    expected = set(index.get("templates") or [])
    missing = expected - set(templates)
    if missing:
        raise SystemExit(f"missing companion intake templates: {sorted(missing)}")

    for key in sorted(templates):
        data = templates[key]
        sections = data.get("sections") or []
        question_count = sum(len(section.get("questions") or []) for section in sections)
        required_count = sum(
            1
            for section in sections
            for question in section.get("questions") or []
            if question.get("required")
        )
        red_flags = len(data.get("red_flag_prompts") or [])
        print(f"OK companion intake {key}: sections={len(sections)}, questions={question_count}, required={required_count}, red_flags={red_flags}")

    print(f"ALL COMPANION STRUCTURED INTAKE TEMPLATES VALID: {index.get('version')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
