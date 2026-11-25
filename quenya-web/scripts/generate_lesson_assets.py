#!/usr/bin/env python3
"""Generate teaching JSON, units-en, exercises, pedagogy, and section exports for lessons 2–20."""
from __future__ import annotations

import json
import re
import html as html_mod
from pathlib import Path

WEB = Path(__file__).resolve().parents[1]
OUT = WEB / "data"
LESSONS = OUT / "lessons"
EXPORT = LESSONS / "_export"

PEDAGOGY_ZH = {
    1: {"title": "昆雅语音与重音", "goal": "掌握元音、辅音、重音规则，能按附录 E 朗读昆雅文本。", "mindmap": ["音位学", "元音长短", "辅音与连缀", "重音与音节", "吠声 H / hl·hr"]},
    2: {"title": "名词、复数与定冠词", "goal": "理解名词复数 -i/-r、定冠词 i 及无冠词语义。", "mindmap": ["名词", "复数", "定冠词 i", "词序", "练习词汇"]},
    3: {"title": "双数与词干变化", "goal": "区分自然双数与 attá + 复数；掌握 -u/-t 双数词尾。", "mindmap": ["双数", "-u / -t", "成对身体", "词干", "与格 -nt"]},
    4: {"title": "形容词与系词", "goal": "形容词一致、系词 ná/nar、定语与表语位置。", "mindmap": ["形容词", "一致", "ná", "定语/表语", "数的一致"]},
    5: {"title": "动词现在时", "goal": "现在时 -ë/-i 及与主语数一致；最高级 an-。", "mindmap": ["现在时", "主宾语", "超级形容词", "-ëa 词干"]},
    6: {"title": "过去时", "goal": "过去时 -në 式及译语到昆雅的变换。", "mindmap": ["过去时", "tengwa 默写", "不规则", "元音变级"]},
    7: {"title": "将来时与不定式", "goal": "将来时 -uva；Híril 不可分 aorist。", "mindmap": ["将来时", "Aorist", "用法对比", "时间副词"]},
    8: {"title": "完成时", "goal": "前缀 ai-/au- 与脱元音；人称尾。", "mindmap": ["完成体", "音变", "人称尾", "及物/不及物"]},
    9: {"title": "不定式与分词", "goal": "动词不定式、ú- 否定；主动分词 -la/-da。", "mindmap": ["不定式", "ú-", "分词", "句法位置"]},
    10: {"title": "副词与人称尾", "goal": "-ntë/-t；副词构成；-ya 不及物过去时。", "mindmap": ["副词", "人称尾", "被动分词", "宾语代词"]},
    11: {"title": "格变概念与属格", "goal": "步行格体系；属格 -o / -ion。", "mindmap": ["格", "属格", "单复双", "Plotz 信"]},
    12: {"title": "领属形容词格", "goal": "-va 领属与抽象名词；与属格互动。", "mindmap": ["-va", "抽象名", "属格", "bodhisattva 式分析"]},
    13: {"title": "与格与动名词", "goal": "与格 -n/-en；-lmë/-lvë/-mmë；不定代词。", "mindmap": ["与格", "动名词", "人称尾", "veru 例"]},
    14: {"title": "向格与离格", "goal": "-nna/-llo；equë、auta；领属代词尾。", "mindmap": ["向格", "离格", "equë", "auta", "-nya 等"]},
    15: {"title": "-rya 与方位格", "goal": "-rya 领属；方位 -ssë；关系从句。", "mindmap": ["-rya", "方位格", "关系句", "第三人称"]},
    16: {"title": "工具格与祈使", "goal": "-nen 工具格；á 祈使；nai 句式。", "mindmap": ["工具格", "-ta 动词", "祈使", "nai"]},
    17: {"title": "指示词", "goal": "sina/tanya/enta/yana；末词曲折；U 词干名。", "mindmap": ["指示词", "末词", "U 词干", "-ëa 序数"]},
    18: {"title": "独立代词", "goal": "强调/独立人称；无人称；lá 多种含义。", "mindmap": ["独立代词", "无人称", "U 动词", "lá"]},
    19: {"title": "疑问词与后置词", "goal": "man/mana/manen；强调代词；祈使短语。", "mindmap": ["疑问", "后置词", "强调代词", "命令式"]},
    20: {"title": "系词「是」", "goal": "ná/nat 系词；ma 疑问；sa 从句。", "mindmap": ["系词", "ma", "sa 从句", "存在 vs 属格"]},
}

SECTION_TITLE_ZH = {
    "the-article": "定冠词",
    "vocabulary": "词汇",
    "exercises": "练习",
}

ITEM_RE = re.compile(r"(?m)^\s*([A-Z])\.\s*(.+?)\s*$")
KEY_ITEM_RE = re.compile(r"(?m)^\s*([A-Z])\.\s*(.+?)(?=\n\s*[A-Z]\.\s|\n\s*\d+\.\s|\Z)", re.DOTALL)


def slug_heading(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower().strip()).strip("-")


def strip_html_to_text(fragment: str) -> str:
    t = re.sub(r"<br\s*/?>", "\n", fragment, flags=re.I)
    t = re.sub(r"</p>\s*<p>", "\n\n", t, flags=re.I)
    t = re.sub(r"<[^>]+>", "", t)
    return html_mod.unescape(t).strip()


def split_html_units(fragment: str) -> list[str]:
    """按 RTF 原始行切分，供逐段中英对照使用。

    textutil 把每个自然段保留为一行；text_to_paragraphs 又把连续行塞进同一个
    <p>。这里按行还原段落。唯一例外是原著里跨行的断句（下一行以小写字母或
    左括号开头），把它接回上一行，避免把一句话劈成两个对照单元。
    """
    if not fragment:
        return []
    units: list[str] = []
    for para in re.findall(r"<p[^>]*>(.*?)</p>", fragment, re.DOTALL | re.I):
        plain = strip_html_to_text(para)
        if not plain:
            continue
        lines = [x.strip() for x in plain.split("\n") if x.strip()]
        merged: list[str] = []
        for line in lines:
            if (
                merged
                and not re.search(r'[.!?:;"\)]$', merged[-1])
                and re.match(r"^[(a-z]", line)
            ):
                merged[-1] += " " + line
            else:
                merged.append(line)
        units.extend(merged)
    if not units:
        plain = strip_html_to_text(fragment)
        if plain:
            units = [p.strip() for p in re.split(r"\n\s*\n", plain) if p.strip()]
    return units


def lesson_sections(lesson: dict) -> dict[str, str]:
    main = lesson["html"]["main"]
    sections: dict[str, str] = {}
    chunks = re.split(r"(?=<h3 class=\"section-heading\")", main)
    preamble = ""
    for chunk in chunks:
        chunk = chunk.strip()
        if not chunk:
            continue
        m = re.match(
            r'<h3 class="section-heading"[^>]*>([^<]+)</h3>(.*)',
            chunk,
            re.DOTALL,
        )
        if m:
            title, rest = m.group(1).strip(), m.group(2)
            sections[slug_heading(title)] = f'<h3 class="section-heading">{title}</h3>{rest}'
        else:
            preamble += chunk
    if preamble.strip():
        sections["_preamble"] = preamble.strip()
    return sections


def section_meta(n: int, sid: str, headings: list[str]) -> tuple[str, str]:
    if sid == "_preamble":
        return (f"模块 · 第 {n} 课主干", f"第 {n} 课核心内容（名词、句式或语法点），请与右侧英文逐段对照。")
    if sid == "exercises":
        return ("模块 · 练习", "完成练习工作台，再对照 keys.rtf。")
    label = SECTION_TITLE_ZH.get(sid, sid.replace("-", " ").title())
    return (f"模块 · {label}", f"本节「{label}」与课文正文衔接，右侧为未删节英文。")


def auto_teaching(n: int, lesson: dict, ped: dict) -> dict:
    sections = lesson_sections(lesson)
    order = []
    if "_preamble" in sections:
        order.append("_preamble")
    for h in lesson.get("sectionHeadings", []):
        sid = slug_heading(h)
        if sid in sections and sid not in order:
            order.append(sid)
    for sid in sections:
        if sid not in order:
            order.append(sid)
    if lesson["html"].get("exercises"):
        order.append("exercises")

    path = []
    modules = []
    for i, sid in enumerate(order, start=1):
        if sid == "exercises":
            label = "动手练"
            title = "模块 · 练习"
            lead = "先在工作台作答，再展开 keys.rtf 与对照阅读区。"
        else:
            title, lead = section_meta(n, sid, lesson.get("sectionHeadings", []))
            if sid == "_preamble":
                label = ped["mindmap"][0] if ped.get("mindmap") else "主干"
            else:
                label = title.replace("模块 · ", "")[:12]
        path.append({"step": i, "labelZh": label, "sectionId": sid})
        objectives = [f"读懂：{ped['goal']}"] if sid == "_preamble" else [f"掌握本节：{label}"]
        if sid == "exercises":
            objectives = ["完成英译/昆雅互译练习", "对照 keys 原文答案", "用本课词汇表复习生词"]
        modules.append({
            "sectionId": sid,
            "titleZh": title,
            "leadZh": lead,
            "objectives": objectives[:3],
            "keyPoints": [],
            "teachingNoteZh": "默认展示中英对照；英文未删节，译文在左侧。" if sid != "exercises" else "练习答案以 keys.rtf 为准，工作台仅供作答与核对。",
        })
    return {
        "lesson": n,
        "pathTitleZh": "本课学习路径",
        "path": path,
        "modules": modules,
    }


WORDS = [
    "ONE", "TWO", "THREE", "FOUR", "FIVE", "SIX", "SEVEN", "EIGHT", "NINE", "TEN",
    "ELEVEN", "TWELVE", "THIRTEEN", "FOURTEEN", "FIFTEEN", "SIXTEEN", "SEVENTEEN",
    "EIGHTEEN", "NINETEEN", "TWENTY",
]


def extract_summary(lesson: dict, n: int) -> str:
    main = strip_html_to_text(lesson["html"]["main"])
    word = WORDS[n - 1]
    m = re.search(rf"Summary of Lesson\s+{word}[:\s]+(.+?)(?:\n\n|\Z)", main, re.DOTALL | re.I)
    if m:
        return m.group(1).strip()[:1200]
    ped = PEDAGOGY_ZH.get(n, {})
    return ped.get("goal", "")


def parse_exercise_parts(ex_text: str) -> tuple[list[dict], list[dict]]:
    lines = ex_text.split("\n")
    parts: list[tuple[str, str]] = []
    current_title = ""
    current_kind = ""
    for line in lines:
        s = line.strip()
        # 有些课的 EXERCISES 只有 "Translate into English:" 这样的无编号小标题
        # （第 9、10 课），旧逻辑会漏掉整段题目；这里一并识别。
        if re.match(r"^\d+\.", s) or re.match(r"^Translate into", s, re.I):
            if "Translate into English" in s or "into English" in s:
                current_kind = "to-en"
            elif "Translate into Quenya" in s or "into Quenya" in s:
                current_kind = "to-q"
            else:
                current_kind = "other"
            current_title = s
            continue
        m = ITEM_RE.match(s)
        if m and current_kind in ("to-en", "to-q"):
            parts.append((current_kind, m.group(1), m.group(2).strip()))
    p1, p2 = [], []
    for kind, lid, prompt in parts:
        item = {"id": lid, "prompt": prompt, "glossZh": ""}
        if kind == "to-en":
            p1.append(item)
        else:
            p2.append(item)
    return p1, p2


def parse_keys_answers(keys_html: str) -> dict[str, str]:
    plain = strip_html_to_text(keys_html)
    out: dict[str, str] = {}
    for m in KEY_ITEM_RE.finditer(plain):
        ans = m.group(2).strip()
        ans = re.sub(r"\s+", " ", ans)
        out[m.group(1)] = ans
    return out


def auto_exercises(n: int, lesson: dict, key_answers: dict[str, str]) -> dict | None:
    ex_html = lesson["html"].get("exercises") or ""
    if not ex_html:
        return None
    ex_text = strip_html_to_text(ex_html)
    p1, p2 = parse_exercise_parts(ex_text)
    if not p1 and not p2:
        return None

    def attach_answers(items: list[dict]) -> list[dict]:
        for it in items:
            it["answerKey"] = key_answers.get(it["id"], "")
            it["answerZh"] = f"keys：{it['answerKey']}" if it["answerKey"] else "见 keys.rtf"
        return items

    return {
        "kind": "translation",
        "introZh": "请先在文稿框中写出译文，再点「核对」比对 keys.rtf；也可直接「显示答案」。",
        "part1": {
            "titleZh": "练习一 · 译成中文（或你使用的语言）",
            "hintZh": "昆雅 → 目标语；对照词汇表与正文例句。",
            "items": attach_answers(p1),
        },
        "part2": {
            "titleZh": "练习二 · 译成昆雅",
            "hintZh": "目标语 → 昆雅；注意复数、冠词 i、词序。",
            "items": attach_answers(p2),
        },
    }


def units_en_from_lesson(lesson: dict) -> dict[str, list[str]]:
    secs = lesson_sections(lesson)
    units: dict[str, list[str]] = {}
    for sid, html_frag in secs.items():
        units[sid] = split_html_units(html_frag)
    if lesson["html"].get("exercises"):
        units["exercises"] = split_html_units(lesson["html"]["exercises"])
    if lesson["html"].get("vocabulary"):
        units["vocabulary"] = split_html_units(lesson["html"]["vocabulary"])
    return units


def export_sections_en(n: int, lesson: dict) -> dict[str, str]:
    secs = lesson_sections(lesson)
    return {sid: strip_html_to_text(html) for sid, html in secs.items()}


def ensure_lesson(n: int, keys: dict) -> None:
    if n == 1:
        return
    lesson_path = LESSONS / f"lesson-{n:02d}.json"
    lesson = json.loads(lesson_path.read_text(encoding="utf-8"))
    ped = PEDAGOGY_ZH[n]

    units_en = units_en_from_lesson(lesson)
    (LESSONS / f"lesson-{n:02d}-units-en.json").write_text(
        json.dumps(units_en, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    # 人工精讲课（schemaVersion >= 2）教学层由维护者撰写，构建不得覆盖；
    # 仅 units-en / 导出文件仍从 RTF 重新生成，保证英文原文不失真。
    teach_path = LESSONS / f"lesson-{n:02d}-teaching.json"
    hand_crafted = False
    if teach_path.exists():
        try:
            hand_crafted = int(
                json.loads(teach_path.read_text(encoding="utf-8")).get("schemaVersion", 1)
            ) >= 2
        except (ValueError, TypeError, json.JSONDecodeError):
            hand_crafted = False

    if not hand_crafted:
        teaching = auto_teaching(n, lesson, ped)
        teach_path.write_text(
            json.dumps(teaching, ensure_ascii=False, indent=2), encoding="utf-8"
        )

        pedagogy = {
            "lesson": n,
            "titleZh": ped["title"],
            "titleEn": lesson.get("subtitleEn", ""),
            "summaryZh": extract_summary(lesson, n),
            "mindmap": {"rootZh": f"第 {n} 课", "branches": [{"labelZh": x, "sectionId": "_preamble"} for x in ped["mindmap"][:5]]},
        }
        (LESSONS / f"lesson-{n:02d}-pedagogy.json").write_text(
            json.dumps(pedagogy, ensure_ascii=False, indent=2), encoding="utf-8"
        )

        key_ans = parse_keys_answers(keys.get(str(n), {}).get("html", ""))
        ex = auto_exercises(n, lesson, key_ans)
        if ex:
            (LESSONS / f"lesson-{n:02d}-exercises.json").write_text(
                json.dumps(ex, ensure_ascii=False, indent=2), encoding="utf-8"
            )

    EXPORT.mkdir(parents=True, exist_ok=True)
    export = export_sections_en(n, lesson)
    (EXPORT / f"lesson-{n:02d}-sections-en.json").write_text(
        json.dumps(export, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    sec_zh_path = LESSONS / f"lesson-{n:02d}-section-zh.json"
    if sec_zh_path.exists():
        sec_zh = json.loads(sec_zh_path.read_text(encoding="utf-8"))
        if "exercises" not in sec_zh and "exercises" in units_en:
            ex_intro = (
                "完成上方练习工作台中的互译题，再对照本节右侧英文 EXERCISES 原文与 keys.rtf。"
            )
            sec_zh["exercises"] = ex_intro
            sec_zh_path.write_text(json.dumps(sec_zh, ensure_ascii=False, indent=2), encoding="utf-8")


def ensure_all(max_lesson: int, keys: dict) -> None:
    for n in range(2, max_lesson + 1):
        ensure_lesson(n, keys)


if __name__ == "__main__":
    keys = json.loads((OUT / "keys.json").read_text(encoding="utf-8"))
    ensure_all(20, keys)
    print("Generated assets for lessons 2–20")