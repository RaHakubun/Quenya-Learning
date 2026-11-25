# 昆雅语互动站点 — 分章实施计划

原则：**每次只做一章**。课文与练习答案必须从对应 RTF 经 `textutil` 转换后写入 JSON，再人工对照抽查；未完成章在站点中标记为「待制作」，不展示未经验证的内容。

资料映射（只读原件，不改动根目录 RTF）：

| 文件 | 课文范围 |
|------|----------|
| `less-a.rtf` | 第 1–5 课 |
| `less-b.rtf` | 第 6–10 课 |
| `less-c.rtf` | 第 11–15 课 |
| `less-d.rtf` | 第 16–20 课 |
| `keys.rtf` | 练习答案 |
| `q-vocab.rtf` | 词汇表（第 2–20 课练习用词） |
| `qappend.rtf` | 附录 |

---

## 阶段 0：工程骨架（已完成）

- [x] `scripts/build_content.py`：RTF → JSON（全课预生成，仅供逐章验收）
- [x] `docs/PLAN.md`：本计划
- [x] 静态前端壳 + 第 1–20 课可浏览
- [x] 静态 HTML：`index.html` / `lessons/lesson-NN.html`（双击打开）
- [x] **教学层**：`lesson-NN-teaching.json` → 学习路径 / 模块 / 要点；原文在 `<details>` 深读区

上架课次由 `scripts/build_content.py` 的 `RELEASED_LESSON_MAX` 控制（当前 20）；`assets/js/config.js` 为旧 SPA 遗留，已不参与构建。

---

## 阶段 1：第 1 课 — 语音与重音（已完成，作为教学层样板）

**原文标题：** LESSON ONE — *The sounds of Quenya. Pronunciation and accentuation.*

**课文主节（对照 `less-a.rtf` 标题）：**

1. GENERAL REMARKS  
2. BASIC TERMS  
3. THE SOUNDS OF QUENYA  
4. PRONUNCIATION（含元音、双元音、辅音、重音与 *Summary of Lesson One*）  
5. EXERCISES  

**本课交互：**

- 侧边目录锚点跳转  
- 中文学习提要 + 知识导图（节点仅对应上述章节与练习）  
- 练习区 + 键入 `keys.rtf` 第 1 课答案（可展开）  
- 中英界面切换（正文仍为原著英文）  

**验收：** 用 `textutil` 导出第 1 课纯文本，与 `data/lessons/lesson-01.json` 字数级抽查；练习 A–T 与答案一一对应。

---

## 阶段 2–5：第 2–20 课（已完成）

每课重复同一 checklist：

1. 从对应 RTF 切片，检查 VOCABULARY / EXERCISES 分隔  
2. 写本章 `lesson-NN-pedagogy.json`（中文提要须能对应到课文真实小节）  
3. 验收 `keys.rtf` 同课答案  
4. 开放该课导航  
5. 若该课练习用新词，核对 `q-vocab.rtf` 条目  

**第 2 课预告：** Nouns, plural, article（`less-a.rtf` LESSON TWO）。

---

## 阶段 6：词汇表与附录（最后）

- 词汇表：按 `q-vocab.rtf` 两列表做检索  
- 附录：按 `qappend.rtf` 各节分页面  
- 全站搜索（仅在全部课文验收后启用）

---

## 风险与规避

| 风险 | 规避 |
|------|------|
| 一次通读臆造内容 | 禁止；每章单独 `textutil` + 抽查 |
| VOCABULARY 标记错位（如第 14 课） | 每章人工看章内首次 `^VOCABULARY$` |
| 链接在 HTML 中被误标 | `build_content.py` 先高光再 linkify，且跳过 URL |