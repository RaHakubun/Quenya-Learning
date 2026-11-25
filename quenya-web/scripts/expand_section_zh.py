#!/usr/bin/env python3
"""
Append paragraph-level Chinese translations keyed to export JSON.
Usage after human/LLM fills data/lessons/_zh_append/<lesson>-<section>.jsonl
Each line: {"p": <int>, "zh": <str>}
Paragraphs split on \\n\\n in sections-en (same order as export).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

WEB = Path(__file__).resolve().parents[1]
LESSONS = WEB / "data" / "lessons"
EXPORT = LESSONS / "_export"
APPEND = LESSONS / "_zh_append"
PARTS = LESSONS / "_zh_parts"


def paras(text: str) -> list[str]:
    return [p.strip() for p in text.split("\n\n") if p.strip()]


def main(lesson_n: int) -> None:
    en = json.loads((EXPORT / f"lesson-{lesson_n:02d}-sections-en.json").read_text(encoding="utf-8"))
    zh_existing = {}
    out_path = LESSONS / f"lesson-{lesson_n:02d}-section-zh.json"
    if out_path.exists():
        zh_existing = json.loads(out_path.read_text(encoding="utf-8"))

    zh_out: dict[str, str] = {}
    for key, en_text in en.items():
        append_path = APPEND / f"lesson-{lesson_n:02d}-{key}.jsonl"
        if append_path.exists():
            lines = [json.loads(ln) for ln in append_path.read_text(encoding="utf-8").splitlines() if ln.strip()]
            en_ps = paras(en_text)
            if len(lines) != len(en_ps):
                raise ValueError(f"{append_path}: {len(lines)} lines vs {len(en_ps)} paragraphs")
            zh_out[key] = "\n\n".join(item["zh"] for item in lines)
            continue
        # fallback: existing part files or prior zh json
        prefix = f"l{lesson_n:02d}-"
        chunks = sorted(PARTS.glob(f"{prefix}{key}-part*.txt"))
        single = PARTS / f"{prefix}{key}.txt"
        if chunks:
            text = "\n\n".join(c.read_text(encoding="utf-8").strip() for c in chunks)
        elif single.exists():
            text = single.read_text(encoding="utf-8").strip()
        elif key in zh_existing:
            text = zh_existing[key]
        else:
            raise FileNotFoundError(f"No zh for {key}")
        zh_out[key] = text.replace("\\n", "\n")

    out_path.write_text(json.dumps(zh_out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for k, v in zh_out.items():
        ratio = len(v) / len(en[k])
        print(f"  {k}: {len(v)}/{len(en[k])} ({ratio:.0%})")


if __name__ == "__main__":
    for n in map(int, sys.argv[1:]):
        print(f"lesson-{n:02d}")
        main(n)