#!/usr/bin/env python3
"""Merge _zh_parts/*.txt into lesson-NN-section-zh.json using keys from _export JSON."""
from __future__ import annotations

import json
from pathlib import Path

WEB = Path(__file__).resolve().parents[1]
LESSONS = WEB / "data" / "lessons"
EXPORT = LESSONS / "_export"
PARTS = LESSONS / "_zh_parts"


def merge(lesson_n: int) -> None:
    en_path = EXPORT / f"lesson-{lesson_n:02d}-sections-en.json"
    en = json.loads(en_path.read_text(encoding="utf-8"))
    zh: dict[str, str] = {}
    prefix = f"l{lesson_n:02d}-"
    def read_key(key: str) -> str:
        single = PARTS / f"{prefix}{key}.txt"
        if single.exists():
            text = single.read_text(encoding="utf-8").strip()
        else:
            chunks = sorted(PARTS.glob(f"{prefix}{key}-part*.txt"))
            if not chunks:
                raise FileNotFoundError(f"{prefix}{key}")
            text = "\n\n".join(c.read_text(encoding="utf-8").strip() for c in chunks)
        return text.replace("\\n", "\n")

    for key in en:
        zh[key] = read_key(key)
    out = LESSONS / f"lesson-{lesson_n:02d}-section-zh.json"
    out.write_text(json.dumps(zh, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {out} ({len(zh)} sections)")


if __name__ == "__main__":
    import sys
    for n in map(int, sys.argv[1:]):
        merge(n)