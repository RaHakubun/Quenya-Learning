#!/usr/bin/env python3
"""Convert Quenya Course RTF sources into structured JSON for the static web app."""
from __future__ import annotations

import json
import re
import subprocess
import html
import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WEB = Path(__file__).resolve().parents[1]
OUT = WEB / "data"

# Static HTML pages built for lessons 1…RELEASED_LESSON_MAX (all must have zh teaching + bilingual).
RELEASED_LESSON_MAX = 20


def _asset_version(*rel_paths: str) -> str:
    """内容哈希，拼进 CSS/JS 的 URL 查询串。

    托管方（GitHub Pages / WorkBuddy 沙箱）都不发 Cache-Control，浏览器按
    Last-Modified 做启发式缓存，改版后旧样式可能被继续用上几小时。把内容哈希
    写进 URL，样式一改 URL 就变，旧缓存自然失效。
    """
    digest = hashlib.sha1()
    for rel in rel_paths:
        path = WEB / "assets" / rel
        if path.exists():
            digest.update(path.read_bytes())
    return digest.hexdigest()[:8]


ASSET_V = _asset_version("css/main.css", "js/lesson-page.js")

LESSON_WORDS = {
    "ONE": 1, "TWO": 2, "THREE": 3, "FOUR": 4, "FIVE": 5,
    "SIX": 6, "SEVEN": 7, "EIGHT": 8, "NINE": 9, "TEN": 10,
    "ELEVEN": 11, "TWELVE": 12, "THIRTEEN": 13, "FOURTEEN": 14, "FIFTEEN": 15,
    "SIXTEEN": 16, "SEVENTEEN": 17, "EIGHTEEN": 18, "NINETEEN": 19, "TWENTY": 20,
}

LESSON_RE = re.compile(
    r"^LESSON\s+(ONE|TWO|THREE|FOUR|FIVE|SIX|SEVEN|EIGHT|NINE|TEN|ELEVEN|TWELVE|THIRTEEN|FOURTEEN|FIFTEEN|SIXTEEN|SEVENTEEN|EIGHTEEN|NINETEEN|TWENTY)\s*$",
    re.MULTILINE | re.IGNORECASE,
)

SECTION_MARKERS = frozenset({
    "VOCABULARY", "EXERCISES", "PRONUNCIATION", "SUMMARY",
})

MAJOR_SECTION_RE = re.compile(
    r"^[A-Z][A-Z0-9 ,\-'/\(\)\"\.:]+[\.]?$",
)


def rtf_to_text(path: Path) -> str:
    result = subprocess.run(
        ["textutil", "-convert", "txt", "-stdout", str(path)],
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.replace("\r\n", "\n").replace("\r", "\n")


def text_to_paragraphs(text: str) -> list[dict]:
    """Split body into paragraphs with optional heading level."""
    lines = text.split("\n")
    blocks: list[dict] = []
    buf: list[str] = []

    def flush():
        nonlocal buf
        if not buf:
            return
        body = "\n".join(buf).strip()
        if body:
            blocks.append({"type": "p", "text": body})
        buf = []

    for line in lines:
        stripped = line.strip()
        if not stripped:
            flush()
            continue
        if stripped in SECTION_MARKERS or (
            len(stripped) < 120
            and MAJOR_SECTION_RE.match(stripped)
            and sum(1 for c in stripped if c.isalpha() and c.isupper()) >= len(stripped) * 0.6
        ):
            flush()
            blocks.append({"type": "h3", "text": stripped})
            continue
        if stripped.startswith("NOTE:") or stripped.startswith("UPDATED NOTE:"):
            flush()
            blocks.append({"type": "note", "text": stripped})
            continue
        buf.append(stripped)
    flush()
    return blocks


def blocks_to_html(blocks: list[dict]) -> str:
    parts: list[str] = []
    for b in blocks:
        t = html.escape(b["text"])
        t = highlight_quenya(t)
        t = linkify(t)
        kind = b["type"]
        if kind == "h3":
            parts.append(f'<h3 class="section-heading">{t}</h3>')
        elif kind == "note":
            parts.append(f'<aside class="callout note">{t}</aside>')
        else:
            parts.append(f"<p>{t}</p>")
    return "\n".join(parts)


def linkify(text: str) -> str:
    return re.sub(
        r"(https?://[^\s<]+)",
        r'<a href="\1" target="_blank" rel="noopener">\1</a>',
        text,
    )


QUENYA_INLINE = re.compile(
    r'\b([A-Za-záéíóúëäöüÁÉÍÓÚËÄÖÜ][A-Za-záéíóúëäöüÁÉÍÓÚËÄÖÜ\-\'/]+)\b'
)


def highlight_quenya(text: str) -> str:
    """Wrap quoted gloss strings as Quenya spans (plain text, before linkify)."""
    def gloss_repl(m: re.Match) -> str:
        inner = m.group(1)
        if "://" in inner or inner.startswith("http"):
            return m.group(0)
        return f'"<span class="quenya">{inner}</span>"'

    return re.sub(r'"([^"]{1,120})"', gloss_repl, text)


def split_lessons(text: str) -> dict[int, str]:
    matches = list(LESSON_RE.finditer(text))
    out: dict[int, str] = {}
    for i, m in enumerate(matches):
        word = m.group(1).upper()
        num = LESSON_WORDS[word]
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        chunk = text[m.start() : end].strip()
        out[num] = chunk
    return out


def extract_subtitle(chunk: str) -> tuple[str, str]:
    lines = chunk.split("\n")
    title_line = lines[0].strip() if lines else ""
    subtitle_lines: list[str] = []
    body_start = 1
    for j in range(1, min(len(lines), 6)):
        line = lines[j].strip()
        if not line:
            body_start = j + 1
            break
        if line.startswith("LESSON"):
            break
        if line.upper() in SECTION_MARKERS:
            body_start = j
            break
        subtitle_lines.append(line)
        body_start = j + 1
    subtitle = " ".join(subtitle_lines).strip()
    body = "\n".join(lines[body_start:]).strip()
    return subtitle, body


def _section_index(body: str, name: str) -> int:
    m = re.search(rf"(?m)^\s*{re.escape(name)}\s*$", body)
    return m.start() if m else -1


def _section_slice(body: str, name: str) -> str:
    m = re.search(rf"(?m)^\s*{re.escape(name)}\s*$\n?", body)
    if not m:
        return ""
    return body[m.end() :].strip()


def split_vocab_exercises(body: str) -> dict:
    vocab_idx = _section_index(body, "VOCABULARY")
    ex_idx = _section_index(body, "EXERCISES")

    main = body
    vocabulary = ""
    exercises = ""
    indices = sorted([(vocab_idx, "v"), (ex_idx, "e")], key=lambda x: x[0] if x[0] >= 0 else 10**9)

    if vocab_idx >= 0 or ex_idx >= 0:
        first_idx = min(i for i in (vocab_idx, ex_idx) if i >= 0)
        main = body[:first_idx].strip()

    if vocab_idx >= 0:
        vocab_end = ex_idx if ex_idx > vocab_idx else len(body)
        vocabulary = body[vocab_idx:vocab_end]
        vocabulary = re.sub(r"(?m)^\s*VOCABULARY\s*$\n?", "", vocabulary, count=1).strip()

    if ex_idx >= 0:
        exercises = body[ex_idx:]
        exercises = re.sub(r"(?m)^\s*EXERCISES\s*$\n?", "", exercises, count=1).strip()

    return {
        "mainText": main,
        "vocabulary": vocabulary,
        "exercises": exercises,
    }


def parse_vocabulary_file(text: str) -> dict:
    sections = {"intro": "", "quenyaEnglish": [], "englishQuenya": []}
    current = "intro"
    for line in text.split("\n"):
        s = line.strip()
        if s == "QUENYA-ENGLISH LIST":
            current = "qe"
            continue
        if s == "ENGLISH-QUENYA LIST":
            current = "eq"
            continue
        if current == "intro":
            if s:
                sections["intro"] += (s + "\n")
            continue
        if s.startswith("¤") or s.startswith("\u00a4"):
            entry = s.lstrip("¤\u00a4 ").strip()
            if current == "qe":
                sections["quenyaEnglish"].append(entry)
            else:
                sections["englishQuenya"].append(entry)
    sections["intro"] = sections["intro"].strip()
    return sections


APPENDIX_HEADINGS = [
    "WHAT IS THE FUNCTION OF THE PARTITIVE PLURAL?",
    "THE APPLICATION OF CASE ENDINGS INCLUDING T",
    "INFINITIVES WITH PREFIXED A-",
    "ELISION OF FINAL VOWELS",
    "STEM VARIATION",
    "VOWEL VARIATIONS",
]


def split_appendix(text: str) -> list[dict]:
    intro_end = text.find("WHAT IS THE FUNCTION")
    intro = text[:intro_end].strip() if intro_end > 0 else ""
    sections: list[dict] = [{"id": "intro", "title": "APPENDICES", "text": intro}]
    markers = []
    for h in APPENDIX_HEADINGS:
        idx = text.find(h)
        if idx >= 0:
            markers.append((idx, h))
    markers.sort()
    for i, (idx, title) in enumerate(markers):
        end = markers[i + 1][0] if i + 1 < len(markers) else len(text)
        body = text[idx + len(title) : end].strip()
        sections.append({
            "id": re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-"),
            "title": title,
            "text": body,
        })
    return sections


PEDAGOGY_ZH = {
    1: {
        "title": "昆雅语音与重音",
        "goal": "掌握元音、辅音、重音规则，能按附录 E 朗读昆雅文本。",
        "mindmap": ["音位学", "元音长短", "辅音与连缀", "重音与音节", "吠声 H / hl·hr"],
    },
    2: {"title": "名词、复数与定冠词", "goal": "理解名词复数 -i/-r、定冠词 i 及无冠词语义。", "mindmap": ["名词", "复数", "定冠词 i", "词序", "练习词汇"]},
    3: {"title": "双数与词干变化", "goal": "区分自然双数与 attá + 复数；掌握 -u/-t 双数词尾。", "mindmap": ["双数", "-u / -t", "成对身体", "词干", "与格 -nt"]},
    4: {"title": "形容词、系词与数一致", "goal": "形容词一致、系词 ná/nar、定语与表语位置。", "mindmap": ["形容词", "一致", "ná", "定语/表语", "数的一致"]},
    5: {"title": "动词：现在时与数一致", "goal": "现在时 -ë/-i 及与主语数一致；最高级 an-。", "mindmap": ["现在时", "主宾语", "超级形容词", "-ëa 词干"]},
    6: {"title": "动词的过去时", "goal": "Elen síla 式过去时；译语到昆雅的变换。", "mindmap": ["过去时", "tengwa 默写", "不规则", "元音变级"]},
    7: {"title": "将来时与无定时", "goal": "将来时 -uva；Híril 不可分 aorist。", "mindmap": ["将来时", "Aorist", "用法对比", "时间副词"]},
    8: {"title": "完成时与代词", "goal": "前缀 ai-/au- 与脱元音；人称尾 -nye/-lye/-nye 等。", "mindmap": ["完成体", "音变", "人称尾", "及物/不及物"]},
    9: {"title": "不定式、否定动词与主动分词", "goal": "动词不定式、ú- 否定；主动分词 -la/-da。", "mindmap": ["不定式", "ú-", "分词", "句法位置"]},
    10: {"title": "副词、人称尾与被动分词", "goal": "-ntë/-t；副词构成；-ya 不及物过去时。", "mindmap": ["副词", "人称尾", "被动分词", "宾语代词"]},
    11: {"title": "格系统与属格", "goal": "步行格体系；属格 -o / -ion。", "mindmap": ["格", "属格", "单复双", "Plotz 信"]},
    12: {"title": "所有格与动名词", "goal": "-va 领属与抽象名词；与属格互动。", "mindmap": ["-va", "抽象名", "属格", "bodhisattva 式分析"]},
    13: {"title": "与格、动名词与「我们」", "goal": "与格 -n/-en；-lmë/-lvë/-mmë；不定代词。", "mindmap": ["与格", "动名词", "人称尾", "veru 例"]},
    14: {"title": "向格、离格与领属词尾", "goal": "-nna/-llo；equë、auta；领属代词尾。", "mindmap": ["向格", "离格", "equë", "auta", "-nya 等"]},
    15: {"title": "-rya、位格与关系句", "goal": "-rya 领属；方位 -ssë；关系从句。", "mindmap": ["-rya", "方位格", "关系句", "第三人称"]},
    16: {"title": "工具格与命令式", "goal": "-nen 工具格；á 祈使；nai 句式。", "mindmap": ["工具格", "-ta 动词", "祈使", "nai"]},
    17: {"title": "指示词、末位变格与 U 词干", "goal": "sina/tanya/enta/yana；末词曲折；U 词干名。", "mindmap": ["指示词", "末词", "U 词干", "-ëa 序数"]},
    18: {"title": "独立代词、无人称动词与 lá", "goal": "强调/独立人称；无人称；lá 多种含义。", "mindmap": ["独立代词", "无人称", "U 动词", "lá"]},
    19: {"title": "命令句代词、强调代词、疑问词与后置词", "goal": "man/mana/manen；强调代词；祈使短语。", "mindmap": ["疑问", "后置词", "强调代词", "命令式"]},
    20: {"title": "to be 的诸形式、ma 与 sa 从句", "goal": "ná/nat 系词；ma 疑问；sa 从句。", "mindmap": ["系词", "ma", "sa 从句", "存在 vs 属格"]},
}

UI_STRINGS = {
    "zh": {
        "siteTitle": "昆雅语互动教程",
        "siteSubtitle": "基于 Helge K. Fauskanger 完整课程原文",
        "navHome": "总览",
        "navLessons": "二十课",
        "navVocab": "词汇表",
        "navAppendix": "附录",
        "navKeys": "练习答案",
        "langToggle": "English UI",
        "progress": "学习进度",
        "original": "原文",
        "summary": "本课提要",
        "mindmap": "知识导图",
        "vocabulary": "课末词汇",
        "exercises": "练习",
        "showKey": "显示答案",
        "hideKey": "隐藏答案",
        "searchPlaceholder": "搜索课文、词汇…",
        "fontQuenya": "昆雅字体",
        "fontLatin": "拉丁转写",
        "authorNote": "正文严格保留原课程英文，未被删节；提要仅作学习导航。",
        "lesson": "第 {n} 课",
        "readLesson": "阅读课文",
        "appendixSection": "附录章节",
        "vocabQE": "昆雅 → 英语",
        "vocabEQ": "英语 → 昆雅",
        "mindmapTip": "点击节点可跳转到对应段落标题。",
    },
    "en": {
        "siteTitle": "Quenya Interactive Course",
        "siteSubtitle": "Full text of Helge K. Fauskanger's course",
        "navHome": "Overview",
        "navLessons": "20 Lessons",
        "navVocab": "Vocabulary",
        "navAppendix": "Appendices",
        "navKeys": "Exercise Keys",
        "langToggle": "中文界面",
        "progress": "Progress",
        "original": "Original text",
        "summary": "Chapter summary",
        "mindmap": "Mind map",
        "vocabulary": "Lesson vocabulary",
        "exercises": "Exercises",
        "showKey": "Show answers",
        "hideKey": "Hide answers",
        "searchPlaceholder": "Search lessons, vocabulary…",
        "fontQuenya": "Tengwar-ready Latin",
        "fontLatin": "Standard Latin",
        "authorNote": "Lesson body is the unabridged original English; summaries aid navigation only.",
        "lesson": "Lesson {n}",
        "readLesson": "Read lesson",
        "appendixSection": "Appendix",
        "vocabQE": "Quenya → English",
        "vocabEQ": "English → Quenya",
        "mindmapTip": "Click a node to jump to the matching section heading.",
    },
}


def build_lessons():
    sources = [
        ROOT / "less-a.rtf",
        ROOT / "less-b.rtf",
        ROOT / "less-c.rtf",
        ROOT / "less-d.rtf",
    ]
    merged: dict[int, str] = {}
    for src in sources:
        text = rtf_to_text(src)
        merged.update(split_lessons(text))

    lessons_dir = OUT / "lessons"
    lessons_dir.mkdir(parents=True, exist_ok=True)
    catalog = []

    for n in sorted(merged.keys()):
        chunk = merged[n]
        subtitle, _ = extract_subtitle(chunk)
        parts = split_vocab_exercises(chunk.split("\n", 1)[1] if "\n" in chunk else "")
        # Re-parse body from full chunk
        _, raw_body = extract_subtitle(chunk)
        split_data = split_vocab_exercises(raw_body)

        main_blocks = text_to_paragraphs(split_data["mainText"])
        vocab_blocks = text_to_paragraphs(split_data["vocabulary"]) if split_data["vocabulary"] else []
        ex_blocks = text_to_paragraphs(split_data["exercises"]) if split_data["exercises"] else []

        ped = PEDAGOGY_ZH.get(n, {"title": f"Lesson {n}", "goal": "", "mindmap": []})
        word = next(k for k, v in LESSON_WORDS.items() if v == n)
        lesson = {
            "number": n,
            "titleEn": f"LESSON {word}",
            "subtitleEn": subtitle,
            "pedagogyZh": ped,
            "html": {
                "main": blocks_to_html(main_blocks),
                "vocabulary": blocks_to_html(vocab_blocks) if vocab_blocks else "",
                "exercises": blocks_to_html(ex_blocks) if ex_blocks else "",
            },
            "sectionHeadings": [b["text"] for b in main_blocks if b["type"] == "h3"],
        }
        path = lessons_dir / f"lesson-{n:02d}.json"
        path.write_text(json.dumps(lesson, ensure_ascii=False, indent=0), encoding="utf-8")
        catalog.append({
            "number": n,
            "subtitleEn": subtitle,
            "titleZh": ped["title"],
            "goalZh": ped["goal"],
        })

    (OUT / "catalog.json").write_text(json.dumps(catalog, ensure_ascii=False, indent=2), encoding="utf-8")


def build_keys():
    text_full = rtf_to_text(ROOT / "keys.rtf")
    m = re.search(r"(?m)^LESSON\s+ONE\s*$", text_full)
    preface = text_full[: m.start()].strip() if m else ""
    if m:
        text_full = text_full[m.start():]
    marker = re.compile(
        r"^LESSON\s+(ONE|TWO|THREE|FOUR|FIVE|SIX|SEVEN|EIGHT|NINE|TEN|"
        r"ELEVEN|TWELVE|THIRTEEN|FOURTEEN|FIFTEEN|SIXTEEN|SEVENTEEN|EIGHTEEN|NINETEEN|TWENTY)\s*$",
        re.MULTILINE | re.IGNORECASE,
    )
    matches = list(marker.finditer(text_full))
    keys = {}
    for i, match in enumerate(matches):
        word = match.group(1).upper()
        num = LESSON_WORDS[word]
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text_full)
        body = text_full[start:end].strip()
        keys[str(num)] = {
            "number": num,
            "html": blocks_to_html(text_to_paragraphs(body)),
        }
    keys["_preface"] = {
        "number": 0,
        "html": blocks_to_html(text_to_paragraphs(preface)),
    }
    (OUT / "keys.json").write_text(json.dumps(keys, ensure_ascii=False, indent=0), encoding="utf-8")


def build_vocab():
    text = rtf_to_text(ROOT / "q-vocab.rtf")
    data = parse_vocabulary_file(text)
    (OUT / "vocabulary.json").write_text(json.dumps(data, ensure_ascii=False, indent=0), encoding="utf-8")


def build_appendix():
    text = rtf_to_text(ROOT / "qappend.rtf")
    sections = split_appendix(text)
    for sec in sections:
        sec["html"] = blocks_to_html(text_to_paragraphs(sec["text"]))
    (OUT / "appendix.json").write_text(json.dumps(sections, ensure_ascii=False, indent=0), encoding="utf-8")


def slug_heading(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower().strip()).strip("-")


def inject_section_ids(html: str) -> str:
    def repl(m: re.Match) -> str:
        title = m.group(1)
        return f'<h3 class="section-heading" id="{slug_heading(title)}">{title}</h3>'

    return re.sub(r'<h3 class="section-heading">([^<]+)</h3>', repl, html)


def split_html_sections(main_html: str) -> dict[str, str]:
    """Split lesson main HTML into sections keyed by heading id."""
    sections: dict[str, str] = {}
    chunks = re.split(r"(?=<h3 class=\"section-heading\" id=)", main_html)
    for chunk in chunks:
        chunk = chunk.strip()
        if not chunk:
            continue
        m = re.match(
            r'<h3 class="section-heading" id="([^"]+)">([^<]+)</h3>(.*)',
            chunk,
            re.DOTALL,
        )
        if m:
            sid, _title, _rest = m.group(1), m.group(2), m.group(3)
            sections[sid] = chunk
        elif not sections:
            sections["_preamble"] = chunk
    return sections


def _section_label(sid: str) -> str:
    """把内部 section id 换成读者看得懂的标签。"""
    if sid == "_preamble":
        return "开篇"
    return sid.replace("-", " ").upper()


def _render_objectives(items: list[str]) -> str:
    if not items:
        return ""
    lis = "".join(f"<li>{html.escape(x)}</li>" for x in items)
    return f'<div class="teach-block"><h4 class="teach-h4">学习目标</h4><ul class="teach-list">{lis}</ul></div>'


def _render_key_points(points: list[dict]) -> str:
    if not points:
        return ""
    rows = "".join(
        f"<article class=\"key-card\"><h5>{html.escape(p.get('termZh') or p.get('term', ''))}</h5>"
        f"<p class=\"key-term\">{html.escape(p.get('term', ''))}</p>"
        f"<p>{html.escape(p.get('explainZh', ''))}</p></article>"
        for p in points
    )
    return f'<div class="teach-block"><h4 class="teach-h4">要点精讲</h4><div class="key-grid">{rows}</div></div>'


def _render_table(tbl: dict | None) -> str:
    if not tbl:
        return ""
    head = "".join(f"<th>{html.escape(h)}</th>" for h in tbl["headers"])
    body = "".join(
        "<tr>" + "".join(f"<td>{html.escape(c)}</td>" for c in row) + "</tr>"
        for row in tbl["rows"]
    )
    cap = html.escape(tbl.get("captionZh", ""))
    return (
        f'<div class="teach-block"><h4 class="teach-h4">{cap}</h4>'
        f'<div class="table-wrap"><table><thead><tr>{head}</tr></thead>'
        f"<tbody>{body}</tbody></table></div></div>"
    )


def _render_checklist(items: list[str] | None) -> str:
    if not items:
        return ""
    lis = "".join(f"<li>{html.escape(x)}</li>" for x in items)
    return f'<div class="teach-block"><h4 class="teach-h4">跟练清单</h4><ul class="teach-list checklist">{lis}</ul></div>'


def _render_workflow(items: list[str] | None) -> str:
    if not items:
        return ""
    steps = "".join(
        f'<li><span class="step-n">{i + 1}</span>{html.escape(s)}</li>'
        for i, s in enumerate(items)
    )
    return f'<div class="teach-block"><h4 class="teach-h4">练习流程</h4><ol class="teach-steps">{steps}</ol></div>'


def _split_paragraphs(text: str) -> list[str]:
    if not text:
        return []
    return [p.strip() for p in re.split(r"\n\s*\n", text.strip()) if p.strip()]


def _unit_text_to_html(text: str) -> str:
    chunks: list[str] = []
    for para in _split_paragraphs(text) if "\n\n" in text else [text.strip()]:
        if not para:
            continue
        lines = [html.escape(x) for x in para.split("\n") if x.strip()]
        inner = "<br/>".join(highlight_quenya(linkify(line)) for line in lines) if len(lines) > 1 else highlight_quenya(linkify(html.escape(para)))
        chunks.append(f'<p class="unit-para">{inner}</p>')
    return "".join(chunks)


# ---------------------------------------------------------------------------
# v2 教学组件：目标 → 规则 → 例外 → 例句 → 易错 → 精读 → 小结 → 自查
# 全部在构建时烘焙为静态 HTML；页面不依赖 fetch / 本地服务。
# ---------------------------------------------------------------------------


def _esc(value) -> str:
    return html.escape("" if value is None else str(value))


def _rich(text) -> str:
    """中文教学文字：转义后把换行还原为 <br/>。"""
    return _esc(text).replace("\n", "<br/>")


def render_rules(rules: list | None) -> str:
    if not rules:
        return ""
    cards = []
    for i, r in enumerate(rules, 1):
        rid = r.get("id") or f"rule-{i}"
        en = r.get("en") or ""
        pair = ""
        if en:
            pair = (
                '<div class="rule-pair">'
                f'<p class="rule-en font-quenya" lang="en">{_esc(en)}</p>'
                f'<p class="rule-zh" lang="zh-CN">{_esc(r.get("zh") or "（中文见右侧逐段对照）")}</p>'
                "</div>"
            )
        ex = r.get("exampleZh") or ""
        note = r.get("noteZh") or ""
        ex_html = '<p class="rule-example">' + _rich(ex) + "</p>" if ex else ""
        note_html = '<p class="rule-note">' + _rich(note) + "</p>" if note else ""
        cards.append(
            f'<article class="rule-card" id="{_esc(rid)}">'
            f'<p class="rule-num">规则 {i}</p>'
            f'<h5>{_esc(r.get("headZh", ""))}</h5>'
            f'<p class="rule-body">{_rich(r.get("bodyZh", ""))}</p>'
            f"{pair}{ex_html}{note_html}</article>"
        )
    return (
        '<div class="teach-block"><h4 class="teach-h4">核心规则</h4>'
        f'<div class="rule-list">{"".join(cards)}</div></div>'
    )


def render_exceptions(items: list | None) -> str:
    if not items:
        return ""
    cards = []
    for x in items:
        src = x.get("sourceEn") or ""
        anchor = x.get("anchor") or ""
        cards.append(
            '<article class="exception-card">'
            f'<h5>{_esc(x.get("titleZh", ""))}</h5>'
            f'<p>{_rich(x.get("bodyZh", ""))}</p>'
            + (f'<p class="exception-src font-quenya" lang="en">{_esc(src)}</p>' if src else "")
            + (f'<a class="exception-link" href="{_esc(anchor)}">定位原文 →</a>' if anchor else "")
            + "</article>"
        )
    return (
        '<div class="teach-block"><h4 class="teach-h4">例外与作者 NOTE 提要</h4>'
        f'<div class="exception-list">{"".join(cards)}</div></div>'
    )


def render_examples(items: list | None) -> str:
    if not items:
        return ""
    cards = []
    for x in items:
        cards.append(
            '<article class="example-card">'
            f'<p class="example-en font-quenya" lang="en">{_esc(x.get("en", ""))}</p>'
            f'<p class="example-zh" lang="zh-CN">{_esc(x.get("zh", ""))}</p>'
            f'<p class="example-why"><strong>为什么：</strong>{_rich(x.get("whyZh", ""))}</p>'
            "</article>"
        )
    return (
        '<div class="teach-block"><h4 class="teach-h4">例句精解</h4>'
        f'<div class="example-list">{"".join(cards)}</div></div>'
    )


def render_pitfalls(items: list | None) -> str:
    if not items:
        return ""
    cards = []
    for x in items:
        cards.append(
            '<article class="pitfall-card">'
            f'<p class="pitfall-wrong"><span>✗</span>{_esc(x.get("wrong", ""))}</p>'
            f'<p class="pitfall-right"><span>✓</span>{_esc(x.get("right", ""))}</p>'
            f'<p class="pitfall-why">{_rich(x.get("whyZh", ""))}</p>'
            "</article>"
        )
    return (
        '<div class="teach-block"><h4 class="teach-h4">易错点</h4>'
        f'<div class="pitfall-list">{"".join(cards)}</div></div>'
    )


def render_close_reading(items: list | None) -> str:
    if not items:
        return ""
    blocks = []
    for x in items:
        blocks.append(
            '<article class="close-item">'
            f'<h5>{_esc(x.get("headZh", ""))}</h5>'
            f'<p>{_rich(x.get("bodyZh", ""))}</p>'
            "</article>"
        )
    return (
        '<div class="teach-block"><h4 class="teach-h4">精读理解 · 为什么这样</h4>'
        f'<div class="close-reading">{"".join(blocks)}</div></div>'
    )


def render_recap(text: str | None) -> str:
    if not text:
        return ""
    return (
        '<div class="teach-block"><h4 class="teach-h4">本节小结</h4>'
        f'<aside class="recap">{_rich(text)}</aside></div>'
    )


def render_self_check(items: list | None) -> str:
    if not items:
        return ""
    rows = []
    for x in items:
        rows.append(
            '<details class="self-check-item">'
            f'<summary>{_esc(x.get("qZh", ""))}</summary>'
            f'<p class="self-check-answer">{_rich(x.get("aZh", ""))}</p>'
            "</details>"
        )
    return (
        '<div class="teach-block"><h4 class="teach-h4">自查</h4>'
        f'<div class="self-check">{"".join(rows)}</div></div>'
    )


def render_lesson_overview_v2(teaching: dict, pedagogy: dict | None) -> str:
    one = teaching.get("oneLineZh", "")
    can = teaching.get("canDoZh") or []
    cmap = teaching.get("conceptMap") or []
    can_rows = "".join(
        f'<li><label><input type="checkbox" class="cando-check" />'
        f'<span>{_esc(x)}</span></label></li>'
        for x in can
    )
    nodes = "".join(
        f'<a class="concept-node" href="#module-{_esc(x.get("sectionId", ""))}">'
        f'<span class="concept-label">{_esc(x.get("labelZh", ""))}</span>'
        f'<span class="concept-note">{_esc(x.get("noteZh", ""))}</span></a>'
        for x in cmap
    )
    progress = (
        f'<p class="cando-progress">已掌握 <strong id="cando-count">0</strong> / {len(can)}'
        '<span class="cando-bar"><i id="cando-bar-fill"></i></span></p>'
        if can else ""
    )
    return (
        '<section class="overview-v2">'
        f'<p class="overview-eyebrow">本课要点</p><p class="overview-oneline">{_esc(one)}</p>'
        '<div class="overview-cols">'
        '<div class="overview-cando"><h2>学完能做什么</h2>'
        f'<ul class="cando-list">{can_rows}</ul>{progress}</div>'
        '<div class="overview-map"><h2>概念地图</h2>'
        f'<div class="concept-map">{nodes}</div></div>'
        "</div></section>"
    )


def render_summary_module(mod: dict, original_html: str) -> str:
    en = mod.get("summaryEn") or ""
    zh = mod.get("summaryZh") or ""
    formula = mod.get("formulaZh") or []
    formula_html = "".join(f"<li>{_esc(x)}</li>" for x in formula)
    return (
        '<section class="summary-block">'
        '<h4 class="teach-h4">本课小结</h4>'
        '<div class="summary-cols">'
        f'<div class="summary-en original-body lesson-content font-quenya" lang="en">{en and _esc(en) or original_html}</div>'
        '<div class="summary-zh" lang="zh-CN">'
        f'<p>{_rich(zh)}</p>'
        + (f'<ol class="summary-formula">{formula_html}</ol>' if formula else "")
        + "</div></div></section>"
    )


def qvocab_lookup(word: str, qvocab: list[str] | None) -> str:
    if not qvocab:
        return ""
    w = word.strip().lower()
    for line in qvocab:
        head = line.split(",", 1)[0].strip().lower()
        if head == w or head.startswith(w + " "):
            return line
    return ""


def render_lesson_vocabulary(vocab_html: str, glossary: dict | None, qvocab: list[str] | None) -> str:
    glossary = glossary or {}
    entries = glossary.get("entries") or []
    intro = glossary.get("introZh") or ""
    cards = []
    for e in entries:
        word = e.get("word", "")
        ref = qvocab_lookup(word, qvocab)
        cards.append(
            '<article class="vocab-card">'
            f'<p class="vocab-word font-quenya" lang="en">{_esc(word)}</p>'
            f'<p class="vocab-pos">{_esc(e.get("posZh", ""))}</p>'
            f'<p class="vocab-gloss">{_esc(e.get("glossZh", ""))}</p>'
            f'<p class="vocab-note">{_rich(e.get("noteZh", ""))}</p>'
            + (f'<p class="vocab-ref">总表：{_esc(ref)}</p>' if ref else "")
            + "</article>"
        )
    return (
        '<section class="vocab-block">'
        '<h4 class="teach-h4">课末词汇</h4>'
        + (f'<p class="vocab-intro">{_rich(intro)}</p>' if intro else "")
        + f'<div class="vocab-grid">{"".join(cards)}</div>'
        + '<details class="original-panel" open id="original-vocabulary">'
        + '<summary>原著 VOCABULARY 原文</summary>'
        + f'<div class="original-body lesson-content font-quenya" lang="en">{vocab_html}</div>'
        + "</details>"
        + '<p class="vocab-cross"><a href="../vocabulary.html">查看总词汇表 →</a></p>'
        + "</section>"
    )


def _module_kind(mod: dict) -> str:
    sid = mod.get("sectionId", "")
    return mod.get("kind") or (
        "vocabulary" if sid == "vocabulary"
        else "exercises" if sid == "exercises"
        else "summary" if sid == "summary"
        else "teaching"
    )


def _module_units(bilingual: dict, en_units: list[str], zh_units: list[str]) -> tuple[list[int], list[str], list[str]]:
    """按 unitIds 或 from/to 取该模块负责的对照单元（保留原文索引号）。"""
    ids = bilingual.get("unitIds")
    if ids is not None:
        idx = [int(i) for i in ids]
    else:
        start = int(bilingual.get("from", 0))
        end = int(bilingual.get("to", len(en_units) - 1))
        idx = list(range(start, min(end, len(en_units) - 1) + 1))
    en = [en_units[i] if i < len(en_units) else "" for i in idx]
    zh = [zh_units[i] if i < len(zh_units) else "" for i in idx]
    return idx, en, zh


def render_bilingual_block(
    section_id: str,
    section_zh: dict[str, str],
    units_en: dict[str, list[str]],
    units_zh: dict[str, list[str]] | None,
    bilingual: dict | None = None,
    label_zh: str | None = None,
) -> str:
    """逐段（关键规则为逐句）中英对照；英文一律取自 RTF 生成的 units-en。"""
    spec = bilingual or {}
    sid = spec.get("sectionId") or section_id
    en_all = list(units_en.get(sid, []))
    zh_all = list(units_zh.get(sid, [])) if units_zh else []
    if spec:
        idx, en_units, zh_units = _module_units(spec, en_all, zh_all)
    else:
        idx = list(range(len(en_all)))
        en_units = en_all
        zh_units = zh_all
    if not zh_units and not en_units:
        return ""

    label = label_zh or ("练习" if sid == "exercises" else "课文")
    aligned = bool(zh_units) and bool(en_units) and len(zh_units) == len(en_units)

    if not aligned:
        # 未精讲课的降级路径：左整节中文、右英文分段（明确标注，不冒充逐段对照）。
        zh_fallback = zh_all or _split_paragraphs(section_zh.get(sid, ""))
        if not zh_fallback and not en_units:
            return ""
        zh_html = _unit_text_to_html("\n\n".join(zh_fallback))
        en_html = "".join(
            f'<div class="unit-en font-quenya">{_unit_text_to_html(u)}</div>' for u in en_units
        )
        return (
            f'<section class="bilingual-sheet bilingual-sheet--columns" aria-label="{_esc(label)}中英对照">'
            f'<header class="bilingual-head"><h4 class="teach-h4">{_esc(label)} · 中英对照</h4></header>'
            '<div class="bilingual-columns">'
            f'<div class="bilingual-col bilingual-zh" lang="zh-CN">{zh_html}</div>'
            f'<div class="bilingual-col bilingual-en" lang="en">{en_html}</div>'
            "</div></section>"
        )

    rows: list[str] = []
    for pos, (orig_idx, zh, en) in enumerate(zip(idx, zh_units, en_units), 1):
        zh_cell = _unit_text_to_html(zh) if zh else '<p class="unit-para unit-gap" aria-hidden="true">　</p>'
        en_cell = (
            f'<div class="unit-en font-quenya">{_unit_text_to_html(en)}</div>' if en else ""
        )
        rows.append(
            f'<div class="bilingual-row" data-row="{pos}" id="unit-{_esc(sid)}-{orig_idx}">'
            f'<div class="bilingual-zh" lang="zh-CN">'
            f'<p class="unit-index">第 {orig_idx + 1} 段</p>{zh_cell}</div>'
            f'<div class="bilingual-en" lang="en">{en_cell}</div></div>'
        )
    return (
        f'<section class="bilingual-sheet" aria-label="{_esc(label)}中英对照">'
        f'<header class="bilingual-head"><h4 class="teach-h4">{_esc(label)} · 中英对照</h4></header>'
        f'<div class="bilingual-rows">{"".join(rows)}</div></section>'
    )


def render_translation_workbook(ex: dict, key_html: str, lesson_n: int) -> str:
    def row_part(items: list[dict], to_en: bool) -> str:
        rows = []
        for it in items:
            prompt = it.get("prompt", "")
            cell_cls = "font-quenya" if to_en else ""
            point = it.get("pointZh") or ""
            hints = it.get("hintsZh") or []
            rule_ref = it.get("ruleRef") or ""
            rule_label = it.get("ruleLabelZh") or "回到本课规则"
            answer_zh = it.get("answerZh") or ""
            alts = it.get("answerAlt") or []
            alt_attr = _esc(json.dumps(alts, ensure_ascii=False))
            hints_html = ""
            if hints:
                hints_html = (
                    '<details class="wb-step-hint"><summary>分步提示</summary><ol>'
                    + "".join(f"<li>{_esc(h)}</li>" for h in hints)
                    + "</ol></details>"
                )
            rule_link = (
                f'<a class="wb-rule-link" href="#{_esc(rule_ref)}">{_esc(rule_label)} →</a>'
                if rule_ref else ""
            )
            zh_html = (
                f'<p class="wb-answer wb-answer-zh">{_rich(answer_zh)}</p>' if answer_zh else ""
            )
            rows.append(
                f'<tr data-row-id="{_esc(it["id"])}"><th scope="row">{_esc(it["id"])}</th>'
                f'<td class="wb-prompt"><p class="{cell_cls}">{_esc(prompt)}</p>'
                + (f'<p class="wb-point"><strong>考点</strong> {_esc(point)}</p>' if point else "")
                + hints_html
                + "</td>"
                '<td class="wb-cell-actions">'
                '<textarea class="wb-translate-input" rows="2" placeholder="在此写出你的译文"></textarea>'
                '<div class="wb-btn-row">'
                '<button type="button" class="btn btn-primary btn-sm wb-check-translate">核对</button>'
                '<button type="button" class="btn btn-ghost btn-sm wb-reveal-keyline">显示答案</button>'
                "</div>"
                '<p class="wb-feedback" aria-live="polite"></p>'
                f'<p class="wb-answer wb-key-line" data-answer-alt="{alt_attr}" '
                f'data-answer-zh="{_esc(it.get("answerKeyZh", ""))}">{_esc(it.get("answerKey", ""))}</p>'
                + zh_html + rule_link
                + "</td></tr>"
            )
        return "".join(rows)

    key_fold = ""
    if key_html:
        key_fold = (
            f'<details class="key-panel key-panel-full" id="key-box">'
            f'<summary>第 {lesson_n} 课完整答案</summary>'
            f'<div class="original-body lesson-content">{key_html}</div></details>'
        )
    point_map = ex.get("pointMapZh") or []
    point_map_html = ""
    if point_map:
        point_map_html = (
            '<div class="wb-point-map"><h5>考点对应的规则</h5><ul>'
            + "".join(
                f'<li><a href="#{_esc(x.get("ruleRef", ""))}">{_esc(x.get("labelZh", ""))}</a>'
                f'<span>{_esc(x.get("noteZh", ""))}</span></li>'
                for x in point_map
            )
            + "</ul></div>"
        )
    p1, p2 = ex.get("part1", {}), ex.get("part2", {})
    return (
        f'<section class="exercise-workbench" id="workbench">'
        f'<header class="wb-head"><h4 class="teach-h4">练习</h4>'
        f'<p>{_esc(ex.get("introZh", ""))}</p>{point_map_html}</header>'
        f'<section class="wb-part"><h5>{_esc(p1.get("titleZh", "练习一"))}</h5>'
        f'<p class="wb-hint">{_esc(p1.get("hintZh", ""))}</p>'
        f'<div class="table-wrap"><table class="wb-table"><thead><tr>'
        f"<th>题号</th><th>题干 / 考点</th><th>作答与核对</th></tr></thead>"
        f'<tbody>{row_part(p1.get("items", []), True)}</tbody></table></div></section>'
        f'<section class="wb-part"><h5>{_esc(p2.get("titleZh", "练习二"))}</h5>'
        f'<p class="wb-hint">{_esc(p2.get("hintZh", ""))}</p>'
        f'<div class="table-wrap"><table class="wb-table"><thead><tr>'
        f"<th>题号</th><th>题干 / 考点</th><th>作答与核对</th></tr></thead>"
        f'<tbody>{row_part(p2.get("items", []), False)}</tbody></table></div></section>'
        f'<div class="exercise-actions"><button type="button" class="btn btn-primary" id="toggle-key">'
        f"展开完整答案</button>{key_fold}</div></section>"
    )


def render_exercise_workbook(ex: dict, key_html: str, lesson_n: int = 1) -> str:
    if not ex:
        return ""
    if ex.get("kind") == "translation":
        return render_translation_workbook(ex, key_html, lesson_n)
    p1_items = "".join(
        f'<tr data-row-id="{html.escape(it["id"])}"><th scope="row">{html.escape(it["id"])}</th>'
        f'<td class="q-word font-quenya">{html.escape(it["word"])}</td>'
        f'<td>{html.escape(it.get("glossZh", ""))}</td>'
        f'<td class="wb-cell-actions">'
        f'<label class="wb-field-label">你的标注 '
        f'<input type="text" class="wb-stress-input" autocomplete="off" '
        f'placeholder="如 a、ui、ó" /></label>'
        f'<div class="wb-btn-row">'
        f'<button type="button" class="btn btn-primary btn-sm wb-check-stress" '
        f'data-answer-vowel="{html.escape(it.get("answerVowel", ""))}">核对</button>'
        f'<button type="button" class="btn btn-ghost btn-sm wb-reveal">显示解析</button>'
        f"</div>"
        f'<p class="wb-feedback" aria-live="polite"></p>'
        f'<p class="wb-answer wb-explain">{html.escape(it.get("answerSyllable", ""))}</p>'
        f"</td></tr>"
        for it in ex["part1"]["items"]
    )
    extra = ex["part1"].get("extra") or {}
    extra_block = (
        f'<section class="wb-extra"><h5>{html.escape(extra.get("titleZh", "附加题"))}</h5>'
        f'<p>{html.escape(extra.get("sceneZh", ""))}</p>'
        f'<details class="wb-extra-key"><summary>显示分析与参考答案</summary>'
        f'<p>{html.escape(extra.get("analysisZh", ""))}</p></details></section>'
    )
    p2_opts = "".join(f"<li>{html.escape(x)}</li>" for x in ex["part2"]["optionsZh"])
    p2_items = "".join(
        f'<tr><th scope="row">{html.escape(it["id"])}</th>'
        f'<td class="q-word font-quenya">{html.escape(it["word"])}</td>'
        f'<td>{html.escape(it.get("glossZh", ""))}</td>'
        f'<td><select class="wb-select" aria-label="选择 {html.escape(it["id"])} 的 h 类型">'
        f'<option value="">—</option><option>A</option><option>B</option><option>C</option><option>D</option>'
        f"</select></td>"
        f'<td class="wb-cell-grade">'
        f'<button type="button" class="btn btn-primary btn-sm wb-grade" '
        f'data-correct="{html.escape(it["answer"])}"'
        f'{f" data-answer-alt=\"{html.escape(it['answerAlt'])}\" title=\"{html.escape(it.get('answerAltNoteZh', ''))}\"" if it.get("answerAlt") else ""}'
        f">核对</button>"
        f'<p class="wb-feedback" aria-live="polite"></p>'
        f'<p class="wb-answer wb-key-line">{html.escape(it["answer"])} · {html.escape(it.get("answerZh", ""))}'
        f'{("（亦可能：" + it["answerAlt"] + "）" + html.escape(it.get("answerAltNoteZh", "")) if it.get("answerAlt") else "")}'
        f"</p></td></tr>"
        for it in ex["part2"]["items"]
    )
    key_fold = ""
    if key_html:
        key_fold = (
            f'<details class="key-panel key-panel-full" id="key-box">'
            f'<summary>第 {lesson_n} 课完整答案</summary>'
            f'<div class="original-body lesson-content">{key_html}</div></details>'
        )
    return (
        f'<section class="exercise-workbench" id="workbench">'
        f'<header class="wb-head"><h4 class="teach-h4">练习</h4>'
        f'<p>{html.escape(ex.get("introZh", ""))}</p></header>'
        f'<section class="wb-part"><h5>{html.escape(ex["part1"]["titleZh"])}</h5>'
        f'<p class="wb-hint">{html.escape(ex["part1"].get("hintZh", ""))}</p>'
        f'<div class="wb-toolbar">'
        f'<button type="button" class="btn btn-ghost btn-sm" id="wb-reveal-all-part1">全部显示解析</button>'
        f'<button type="button" class="btn btn-ghost btn-sm" id="wb-hide-all-part1">全部隐藏解析</button>'
        f"</div>"
        f'<div class="table-wrap"><table class="wb-table"><thead><tr>'
        f"<th>题号</th><th>昆雅词</th><th>词义</th><th>作答与核对</th></tr></thead>"
        f"<tbody>{p1_items}</tbody></table></div>{extra_block}</section>"
        f'<section class="wb-part"><h5>{html.escape(ex["part2"]["titleZh"])}</h5>'
        f'<ul class="wb-options">{p2_opts}</ul>'
        f'<div class="table-wrap"><table class="wb-table"><thead><tr>'
        f"<th>题号</th><th>昆雅词</th><th>词义</th><th>你的选项</th><th>核对</th></tr></thead>"
        f"<tbody>{p2_items}</tbody></table></div></section>"
        f'<div class="exercise-actions"><button type="button" class="btn btn-primary" id="toggle-key">'
        f"展开完整答案</button>{key_fold}</div></section>"
    )


def render_teaching_modules(
    teaching: dict,
    sections: dict[str, str],
    ex_html: str,
    key_html: str,
    section_zh: dict[str, str] | None = None,
    units_en: dict[str, list[str]] | None = None,
    units_zh: dict[str, list[str]] | None = None,
    exercises_data: dict | None = None,
    lesson_n: int = 1,
    vocab_html: str = "",
    glossary: dict | None = None,
    qvocab: list[str] | None = None,
) -> str:
    parts: list[str] = []
    path = teaching.get("path", [])
    path_html = "".join(
        f'<a class="path-step" href="#module-{_esc(p["sectionId"])}">'
        f'<span class="path-n">{p["step"]}</span>'
        f'<span class="path-label">{_esc(p["labelZh"])}</span></a>'
        for p in path
    )
    parts.append(
        f'<nav class="learn-path" aria-label="{_esc(teaching.get("pathTitleZh", "本课脉络"))}">'
        f'<p class="path-title">{_esc(teaching.get("pathTitleZh", "本课脉络"))}</p>'
        f'<div class="path-steps">{path_html}</div></nav>'
    )

    path_step = {p["sectionId"]: p["step"] for p in path}
    sidebar_steps = "".join(
        f'<a class="sidebar-step" href="#module-{_esc(p["sectionId"])}">'
        f'<span class="sidebar-n">{p["step"]}</span>'
        f'<span class="sidebar-label">{_esc(p["labelZh"])}</span></a>'
        for p in path
    )

    seen_originals: set[str] = set()
    for mod in teaching.get("modules", []):
        sid = mod["sectionId"]
        kind = _module_kind(mod)
        src_sid = mod.get("sourceSectionId") or sid
        orig = sections.get(src_sid, "")
        if src_sid == "_preamble" and not orig:
            orig = sections.get("_preamble", "")

        inner = [
            f'<header class="module-head"><p class="module-kicker">第 {path_step.get(sid, "?")} 节</p>'
            f'<h2 id="module-{_esc(sid)}">{_esc(mod["titleZh"])}</h2>'
            f'<p class="module-lead">{_esc(mod.get("leadZh", ""))}</p></header>',
            _render_objectives(mod.get("objectives", [])),
            render_rules(mod.get("rules")),
            _render_key_points(mod.get("keyPoints", [])),
            _render_table(mod.get("table")),
            render_examples(mod.get("examples")),
            render_exceptions(mod.get("exceptions")),
            render_pitfalls(mod.get("pitfalls")),
            render_close_reading(mod.get("closeReadingZh")),
            render_recap(mod.get("recapZh")),
            render_self_check(mod.get("selfCheckZh")),
            _render_checklist(mod.get("checklistZh")),
            _render_workflow(mod.get("workflowZh")),
        ]
        if mod.get("teachingNoteZh"):
            inner.append(
                '<aside class="teach-tip"><strong>注意</strong>'
                f'<p>{_rich(mod["teachingNoteZh"])}</p></aside>'
            )

        if kind == "vocabulary":
            inner.append(render_lesson_vocabulary(vocab_html, glossary, qvocab))
        elif kind == "exercises":
            if exercises_data:
                inner.append(render_exercise_workbook(exercises_data, key_html, lesson_n))
            elif key_html:
                # 兜底：即使某课练习题干尚未结构化，keys.rtf 答案仍须在页上可展开。
                inner.append(
                    f'<details class="key-panel key-panel-full" id="key-box">'
                    f'<summary>第 {lesson_n} 课完整答案</summary>'
                    f'<div class="original-body lesson-content">{key_html}</div></details>'
                )
            if ex_html:
                inner.append(
                    '<details class="original-panel" id="original-exercises">'
                    '<summary>原著 EXERCISES 原文</summary>'
                    f'<div class="original-body lesson-content font-quenya" lang="en">{ex_html}</div>'
                    "</details>"
                )
        elif kind == "summary":
            inner.append(render_summary_module(mod, orig))

        if mod.get("bilingual") and units_en:
            spec = mod["bilingual"]
            inner.append(
                render_bilingual_block(
                    spec.get("sectionId", sid),
                    section_zh or {},
                    units_en,
                    units_zh,
                    spec,
                    spec.get("labelZh"),
                )
            )
        elif (
            section_zh is not None
            and units_en
            and (units_en.get(sid) or section_zh.get(sid))
        ):
            inner.append(
                render_bilingual_block(sid, section_zh, units_en, units_zh)
            )

        # 每个原文大节只挂一次「未删节全文」兜底面板，供逐段对照逐字核对。
        if src_sid not in seen_originals and orig and mod.get("showOriginal", True):
            seen_originals.add(src_sid)
            inner.append(
                f'<details class="original-panel original-panel-full" id="original-{_esc(src_sid)}">'
                f'<summary>原著原文 · {_esc(_section_label(src_sid))}</summary>'
                f'<div class="original-body lesson-content font-quenya" lang="en">{orig}</div></details>'
            )
        parts.append(f'<section class="teach-module" data-section="{_esc(sid)}">{"".join(inner)}</section>')

    inner_main = "\n".join(parts)
    return (
        '<div class="lesson-body-grid">'
        '<aside class="lesson-sidebar" aria-label="本课目录">'
        f'<p class="sidebar-title">本课目录</p><nav class="sidebar-nav">{sidebar_steps}</nav></aside>'
        f'<div class="lesson-body-main">{inner_main}</div></div>'
    )


def site_nav(prefix: str = "", active: str = "") -> str:
    items = [
        ("index", "总览"),
        ("vocabulary", "总词汇表"),
        ("appendix", "附录"),
        ("keys", "练习答案"),
    ]
    links = "".join(
        f'<a class="site-nav-link{" is-active" if key == active else ""}" '
        f'href="{prefix}{key}.html">{_esc(label)}</a>'
        for key, label in items
    )
    return f'<nav class="site-nav" aria-label="全站导航">{links}</nav>'


def render_lesson_page(
    n: int,
    lesson: dict,
    key_html: str,
    pedagogy: dict | None,
    catalog_entry: dict,
    teaching: dict | None,
    section_zh: dict[str, str] | None = None,
    units_en: dict[str, list[str]] | None = None,
    units_zh: dict[str, list[str]] | None = None,
    exercises_data: dict | None = None,
    lesson_n: int | None = None,
    vocab_html: str = "",
    glossary: dict | None = None,
    qvocab: list[str] | None = None,
) -> str:
    lesson_n = lesson_n or n
    word = next(k for k, v in LESSON_WORDS.items() if v == n)
    main_html = inject_section_ids(lesson["html"]["main"])
    ex_html = inject_section_ids(lesson["html"]["exercises"]) if lesson["html"]["exercises"] else ""
    sections = split_html_sections(main_html)

    title_zh = catalog_entry.get("titleZh", "")
    is_v2 = bool(teaching and int(teaching.get("schemaVersion", 1)) >= 2)

    if teaching:
        body = render_teaching_modules(
            teaching,
            sections,
            ex_html,
            key_html,
            section_zh,
            units_en,
            units_zh,
            exercises_data,
            lesson_n,
            vocab_html,
            glossary,
            qvocab,
        )
    else:
        body = f'<section class="teach-module"><div class="original-body lesson-content font-quenya">{main_html}</div></section>{ex_html}'

    if is_v2:
        overview_block = render_lesson_overview_v2(teaching, pedagogy)
    elif pedagogy and pedagogy.get("summaryZh"):
        overview_block = (
            '<aside class="lesson-overview"><h2>本课总览</h2>'
            f'<p>{_esc(pedagogy["summaryZh"])}</p></aside>'
        )
    else:
        overview_block = ""

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>第 {n} 课 · {_esc(title_zh)} · 昆雅语课程</title>
  <link rel="stylesheet" href="../assets/css/main.css?v={ASSET_V}" />
</head>
<body>
  <header class="site-header">
    <div class="site-header-inner">
      <a class="brand" href="../index.html">
        <span class="brand-title">昆雅语课程</span>
        <span class="brand-sub">Helge K. Fauskanger · 第 {n} 课</span>
      </a>
      {site_nav("../")}
      <a class="btn btn-ghost" href="../index.html">目录</a>
    </div>
  </header>
  <div class="page-wrap page-lesson">
    <header class="lesson-hero lesson-hero--wide">
      <p class="lesson-eyebrow">LESSON {word}</p>
      <h1>{_esc(title_zh)}</h1>
      <p class="lesson-subtitle-en">{_esc(lesson["subtitleEn"])}</p>
    </header>
    {overview_block}
  <main class="lesson-main">
      {body}
  </main>
  </div>
  <script src="../assets/js/lesson-page.js?v={ASSET_V}"></script>
</body>
</html>"""


def render_index(catalog: list, refined: set[int] | None = None) -> str:
    refined = refined or set()
    cards = []
    for n in range(1, 21):
        entry = next(c for c in catalog if c["number"] == n)
        if n <= RELEASED_LESSON_MAX:
            cards.append(
                f'<a class="lesson-card{" is-refined" if n in refined else ""}" href="lessons/lesson-{n:02d}.html">'
                f'<span class="lesson-card-n">第 {n} 课</span>'
                f'<span class="lesson-card-title">{_esc(entry["titleZh"])}</span>'
                f'<span class="lesson-card-en">{_esc(entry["subtitleEn"])}</span>'
                f'<span class="lesson-card-cta">开始本课 →</span></a>'
            )
        else:
            cards.append(
                f'<div class="lesson-card is-locked"><span class="lesson-card-n">第 {n} 课</span>'
                f'<span class="lesson-card-title">{_esc(entry["titleZh"])}</span>'
                f'<span class="lesson-card-muted">尚未开放</span></div>'
            )
    nav = "\n".join(cards)
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>昆雅语课程</title>
  <link rel="stylesheet" href="assets/css/main.css?v={ASSET_V}" />
</head>
<body>
  <header class="site-header">
    <div class="site-header-inner">
      <div class="brand"><span class="brand-title">昆雅语课程</span>
      <span class="brand-sub">Helge K. Fauskanger 原著 · 中文讲解</span></div>
      {site_nav("", "index")}
    </div>
  </header>
  <div class="page-wrap page-home">
    <header class="home-intro">
      <h1>昆雅语二十课</h1>
      <p>从发音与重音讲到系词「是」。每课按原著段落顺序展开：先立规则，再给例句与精读，最后进练习；英文原文完整保留，与中文逐段对照。</p>
      <p class="home-meta">共二十课 · 中文讲解与英文原文逐段对照</p>
    </header>
    <section class="home-resources" aria-label="全站资料">
      <a class="resource-card" href="vocabulary.html"><strong>总词汇表</strong><span>昆雅→英语、英语→昆雅双列，可直接搜索</span></a>
      <a class="resource-card" href="appendix.html"><strong>附录</strong><span>六个专题，中文导读与英文全文</span></a>
      <a class="resource-card" href="keys.html"><strong>练习答案</strong><span>作者说明与二十课答案</span></a>
    </section>
    <section class="lesson-grid" aria-label="课程目录">{nav}</section>
  </div>
</body>
</html>"""


# ---------------------------------------------------------------------------
# 全站级静态页：总词汇表 / 附录 / keys 前言。均为构建时烘焙，file:// 可开。
# ---------------------------------------------------------------------------

VOCAB_INTRO_ZH = (
    "这两张表（昆雅→英语、英语→昆雅）覆盖本课程第 2–20 课练习中出现的全部词汇，"
    "少数专有名词除外。只出现在课文正文、未进入练习的词不收；第 1 课练习用词也不收，"
    "因为那些词对做题没有意义。注意：所有词都以最基本形式列出，练习原文里往往用的是"
    "带屈折词尾或派生形式；昆雅→英语表不含屈折词尾，英语→昆雅表则收了人称词尾。"
    "用法建议：做某课练习前先在该课「课末词汇」里记住 12 个新词，"
    "再按英文或昆雅词反查即可。"
)

KEYS_PREFACE_ZH = (
    "注意：昆雅课程（含练习）仍在修订中。有些地方修订未彻底，导致练习题与这里的答案对不上。"
    "作者已尽力剔除这类错误；若你怀疑某条答案确实与练习不符，请先下载最新版的 Keys 文件和"
    "对应课文再核对。若最新版里仍然存在出入，请告知作者（helge.fauskanger@nor.uib.no）。"
    "——中文提示：答案以原著答案为准，各课页面底部也可直接展开完整答案；"
    "若两处不一致，以原著答案为准，并注意作者上述修订说明。"
)

APPENDIX_GUIDES_ZH = {
    "intro": (
        "附录的定位：作者把「有把握、能据以出题」的内容放进了 20 课正文，"
        "把证据不足、不宜拿来出练习的专题留在这里。因此第 2 课说「部分复数暂不教」，"
        "真正展开讨论就在下面第一节。读附录时不必背诵，重点是理解「为什么课程里不讲」。"
    ),
    "what-is-the-function-of-the-partitive-plural": (
        "对应第 2 课留的悬念。先讲 -li 的构形（含辅音同化、** 号表示错误形式、各格变化），"
        "再讨论它的语义：早期研究者认为是「许多」，作者列举 Namárië、Treebeard 的问候语、"
        "Markirya 等反例，倾向「某个子集 / some」，但结论仍是推测。"
        "读法：先分清「构形有据」与「功能未定」两层，别把推测当规则记。"
    ),
    "the-application-of-case-endings-including-t": (
        "围绕双数词尾 -u / -t 与含 -t- 的格词尾（属格 -to、与格 -nt 等）能否搭配使用。"
        "作者从 Plotz Letter 出发提出一种历史演化的解释，并明确说明没有确定答案。"
        "与第 3 课「双数」、后续各格章节对读。"
    ),
    "infinitives-with-prefixed-a": (
        "从《Markirya》里两处带前缀 a- 的不定式（ahosta、acúna）出发，讨论这个前缀的功能；"
        "作者提到托尔金先写 na-、后改为 a-，涉及的动词是 A 词干 hosta-「聚集」与 cúna-「弯曲」。"
        "与正文不定式相关章节对读。"
    ),
    "elision-of-final-vowels": (
        "讲的是：一个词以元音结尾、下一个词以元音开头时，前词的词末元音可以省略（并非必须）。"
        "开篇例证是问候语 elen síla lúmenn' omentielvo（lúmenna 的 -a 在 omentielvo 前脱落），"
        "以及《埃兰迪尔之誓》里的 tenn' Ambar-metta（tenna 在 a- 前缩为 tenn'）。"
        "遇到拼写「少一个元音」时回到这一节查。"
    ),
    "stem-variation": (
        "承接第 3 课：加了词尾后词干有时会变，例如 talan「地板」的复数是 talami 而不是 **talani，"
        "词干形式为 talam-。作者说明这类词干形式通常反映该词更古老的面貌。"
    ),
    "vowel-variations": (
        "讨论加词尾时长元音变短（或反过来说，无词尾时变长）的现象："
        "nén、nér、quén 加词尾时词干分别为 nen-、ner-、quen-；也列举 yén 的复数 yéni 保留长元音这类"
        "与规则不一致的例子，并推测托尔金改动了该词的最终词源。适合作为查阅资料。"
    ),
}


def render_site_page(title: str, body: str, active: str, extra_head: str = "") -> str:
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{_esc(title)} · 昆雅语课程</title>
  <link rel="stylesheet" href="assets/css/main.css?v={ASSET_V}" />{extra_head}
</head>
<body>
  <header class="site-header">
    <div class="site-header-inner">
      <a class="brand" href="index.html">
        <span class="brand-title">昆雅语课程</span>
        <span class="brand-sub">Helge K. Fauskanger 原著</span>
      </a>
      {site_nav("", active)}
    </div>
  </header>
  <div class="page-wrap page-site">
    {body}
  </div>
  <script src="assets/js/site-pages.js"></script>
</body>
</html>"""


def _vocab_rows(entries: list[str], kind: str) -> str:
    rows = []
    for line in entries:
        if kind == "qe" and "," in line:
            head, rest = line.split(",", 1)
        elif kind == "eq" and " " in line:
            head, rest = line.split(" ", 1)
        else:
            head, rest = line, ""
        rows.append(
            f'<tr data-search="{_esc(line.lower())}">'
            f'<th scope="row" class="vocab-list-word font-quenya">{_esc(head.strip())}</th>'
            f'<td class="vocab-list-gloss">{_esc(rest.strip())}</td></tr>'
        )
    return "".join(rows)


def render_vocabulary_page(vocab: dict) -> str:
    intro_en = _esc(vocab.get("intro", "")).replace("\n", "<br/>")
    qe = vocab.get("quenyaEnglish", [])
    eq = vocab.get("englishQuenya", [])
    body = (
        '<header class="site-hero">'
        '<h1>全课程总词汇表</h1>'
        '<p class="site-lead">第 2–20 课练习用词 · 昆雅→英语、英语→昆雅双列，可直接搜索</p></header>'
        '<section class="site-intro"><h2>这张表怎么用</h2>'
        f'<p class="site-intro-zh">{_esc(VOCAB_INTRO_ZH)}</p>'
        f'<details class="original-panel"><summary>原著词汇表篇首说明</summary>'
        f'<div class="original-body lesson-content font-quenya" lang="en">{intro_en}</div></details></section>'
        '<div class="filter-bar"><label for="vocab-search">搜索词汇（英文词义或昆雅词）</label>'
        '<input id="vocab-search" class="site-search" type="search" '
        'placeholder="如 horse / rocco / king" autocomplete="off" />'
        '<span class="filter-count" id="vocab-count"></span></div>'
        '<section class="vocab-list-section" id="qe"><h2>昆雅 → 英语 <span class="list-count"></span></h2>'
        '<div class="table-wrap"><table class="vocab-list-table"><thead><tr>'
        '<th>昆雅词</th><th>英文释义 / 说明</th></tr></thead>'
        f'<tbody>{_vocab_rows(qe, "qe")}</tbody></table></div></section>'
        '<section class="vocab-list-section" id="eq"><h2>英语 → 昆雅 <span class="list-count"></span></h2>'
        '<div class="table-wrap"><table class="vocab-list-table"><thead><tr>'
        '<th>英语词</th><th>昆雅词 / 说明</th></tr></thead>'
        f'<tbody>{_vocab_rows(eq, "eq")}</tbody></table></div></section>'
        '<p class="site-foot-note">词条来自原著附词汇表，按原顺序排列；中文释义仅作学习提示。</p>'
    )
    return render_site_page("总词汇表", body, "vocabulary")


def render_appendix_page(sections: list[dict]) -> str:
    nav = "".join(
        f'<a class="sidebar-step" href="#appendix-{_esc(s["id"])}">'
        f'<span class="sidebar-label">{_esc(s["title"])}</span></a>'
        for s in sections
        if s["id"] != "intro"
    )
    blocks = []
    intro = next((s for s in sections if s["id"] == "intro"), None)
    for s in sections:
        sid = s["id"]
        if sid == "intro":
            continue
        guide = APPENDIX_GUIDES_ZH.get(sid, "")
        blocks.append(
            f'<section class="appendix-section" id="appendix-{_esc(sid)}">'
            f'<h2>{_esc(s["title"])}</h2>'
            + (f'<aside class="appendix-guide"><strong>中文章节导读</strong><p>{_esc(guide)}</p></aside>' if guide else "")
            + f'<div class="original-body lesson-content font-quenya appendix-original" lang="en">{s.get("html", "")}</div>'
            + "</section>"
        )
    body = (
        '<header class="site-hero">'
        '<h1>课程附录</h1>'
        '<p class="site-lead">六个专题 · 中文导读与英文原文</p></header>'
        '<section class="site-intro"><h2>附录在课程里的位置</h2>'
        f'<p class="site-intro-zh">{_esc(APPENDIX_GUIDES_ZH["intro"])}</p>'
        + (
            '<details class="original-panel"><summary>APPENDICES 篇首说明（英文原文）</summary>'
            f'<div class="original-body lesson-content font-quenya" lang="en">{intro.get("html", "")}</div></details>'
            if intro else ""
        )
        + '</section>'
        '<div class="site-body-grid">'
        f'<aside class="lesson-sidebar"><p class="sidebar-title">附录章节</p><nav class="sidebar-nav">{nav}</nav></aside>'
        f'<div class="site-body-main">{"".join(blocks)}</div></div>'
        '<p class="site-foot-note">英文为原著全文，未作删改；中文只作导读。</p>'
    )
    return render_site_page("附录", body, "appendix")


def render_keys_page(keys: dict) -> str:
    preface = keys.get("_preface", {}).get("html", "")
    links = "".join(
        f'<a class="keys-lesson-link" href="lessons/lesson-{n:02d}.html#key-box">第 {n} 课 →</a>'
        for n in range(1, RELEASED_LESSON_MAX + 1)
    )
    folds = "".join(
        f'<details class="key-panel key-panel-full" id="keys-lesson-{n}">'
        f'<summary>第 {n} 课完整答案</summary>'
        f'<div class="original-body lesson-content">{keys[str(n)]["html"]}</div></details>'
        for n in range(1, RELEASED_LESSON_MAX + 1)
        if str(n) in keys
    )
    body = (
        '<header class="site-hero">'
        '<h1>练习答案与作者说明</h1>'
        '<p class="site-lead">作者说明 · 二十课答案</p></header>'
        '<section class="site-intro"><h2>使用前必读（作者说明）</h2>'
        '<div class="keys-preface-cols">'
        f'<div class="keys-preface-en original-body lesson-content font-quenya" lang="en">{preface}</div>'
        f'<div class="keys-preface-zh" lang="zh-CN"><p>{_esc(KEYS_PREFACE_ZH)}</p></div>'
        '</div></section>'
        '<section class="keys-index"><h2>按课跳转</h2>'
        f'<div class="keys-grid">{links}</div>'
        '<p class="site-foot-note">各课页面底部也能直接展开该课完整答案。</p></section>'
        '<section class="keys-full"><h2>20 课答案全文（可展开）</h2>'
        f'{folds}</section>'
    )
    return render_site_page("练习答案", body, "keys")


def build_static_html():
    catalog = json.loads((OUT / "catalog.json").read_text(encoding="utf-8"))
    keys = json.loads((OUT / "keys.json").read_text(encoding="utf-8"))
    vocab = json.loads((OUT / "vocabulary.json").read_text(encoding="utf-8"))
    appendix = json.loads((OUT / "appendix.json").read_text(encoding="utf-8"))
    lessons_dir = WEB / "lessons"
    lessons_dir.mkdir(parents=True, exist_ok=True)

    refined: set[int] = set()
    for n in range(1, RELEASED_LESSON_MAX + 1):
        tp = OUT / "lessons" / f"lesson-{n:02d}-teaching.json"
        if tp.exists():
            try:
                if int(json.loads(tp.read_text(encoding="utf-8")).get("schemaVersion", 1)) >= 2:
                    refined.add(n)
            except (ValueError, TypeError, json.JSONDecodeError):
                pass

    (WEB / "index.html").write_text(render_index(catalog, refined), encoding="utf-8")
    (WEB / "vocabulary.html").write_text(render_vocabulary_page(vocab), encoding="utf-8")
    (WEB / "appendix.html").write_text(render_appendix_page(appendix), encoding="utf-8")
    (WEB / "keys.html").write_text(render_keys_page(keys), encoding="utf-8")

    for n in range(1, RELEASED_LESSON_MAX + 1):
        lesson = json.loads(
            (OUT / "lessons" / f"lesson-{n:02d}.json").read_text(encoding="utf-8")
        )
        ped_path = OUT / "lessons" / f"lesson-{n:02d}-pedagogy.json"
        pedagogy = (
            json.loads(ped_path.read_text(encoding="utf-8")) if ped_path.exists() else None
        )
        entry = next(c for c in catalog if c["number"] == n)
        teach_path = OUT / "lessons" / f"lesson-{n:02d}-teaching.json"
        teaching = (
            json.loads(teach_path.read_text(encoding="utf-8")) if teach_path.exists() else None
        )
        sec_zh_path = OUT / "lessons" / f"lesson-{n:02d}-section-zh.json"
        section_zh = (
            json.loads(sec_zh_path.read_text(encoding="utf-8")) if sec_zh_path.exists() else None
        )
        units_en_path = OUT / "lessons" / f"lesson-{n:02d}-units-en.json"
        units_en = (
            json.loads(units_en_path.read_text(encoding="utf-8")) if units_en_path.exists() else None
        )
        units_zh_path = OUT / "lessons" / f"lesson-{n:02d}-units-zh.json"
        units_zh = (
            json.loads(units_zh_path.read_text(encoding="utf-8")) if units_zh_path.exists() else None
        )
        ex_path = OUT / "lessons" / f"lesson-{n:02d}-exercises.json"
        exercises_data = json.loads(ex_path.read_text(encoding="utf-8")) if ex_path.exists() else None
        glossary_path = OUT / "lessons" / f"lesson-{n:02d}-glossary.json"
        glossary = (
            json.loads(glossary_path.read_text(encoding="utf-8")) if glossary_path.exists() else None
        )
        page = render_lesson_page(
            n,
            lesson,
            keys[str(n)]["html"],
            pedagogy,
            entry,
            teaching,
            section_zh,
            units_en,
            units_zh,
            exercises_data,
            vocab_html=lesson["html"].get("vocabulary", ""),
            glossary=glossary,
            qvocab=vocab.get("quenyaEnglish", []),
        )
        (lessons_dir / f"lesson-{n:02d}.html").write_text(page, encoding="utf-8")
    print(
        f"Wrote index.html, vocabulary.html, appendix.html, keys.html and lessons 1–"
        f"{RELEASED_LESSON_MAX} under {WEB} (refined: {sorted(refined)})"
    )


def build_meta():
    meta = {
        "author": "Helge Kåre Fauskanger",
        "sourceFiles": [
            "less-a.rtf", "less-b.rtf", "less-c.rtf", "less-d.rtf",
            "keys.rtf", "q-vocab.rtf", "qappend.rtf",
        ],
        "ui": UI_STRINGS,
        "pedagogyZh": PEDAGOGY_ZH,
    }
    (OUT / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")


def main():
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from generate_lesson_assets import ensure_all  # noqa: WPS433

    OUT.mkdir(parents=True, exist_ok=True)
    build_lessons()
    build_keys()
    keys_data = json.loads((OUT / "keys.json").read_text(encoding="utf-8"))
    ensure_all(RELEASED_LESSON_MAX, keys_data)
    build_vocab()
    build_appendix()
    build_meta()
    build_static_html()
    print(f"Built course data in {OUT}")


if __name__ == "__main__":
    main()