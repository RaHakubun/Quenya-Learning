# 昆雅课程静态站 · 接手 Agent 提示词（交接说明）

你是接手的工程 Agent。请完整阅读本文后再动手。**不要**要求学习者运行 Python 或开本地服务器；交付物必须是**双击即可打开的静态 HTML**。课程**英文原著 RTF 不得删改**，只可只读抽取。上一任工作的定位是「把资料挂上站 + 双语壳」，你需要做的是**前端与教学结构重构**，让每一章真正像教学产品，而不是「原文对照阅读器」。

---

## 一、项目位置与硬性约束（必须遵守）

### 1.1 目录结构

| 路径 | 说明 |
|------|------|
| `/Users/luobowen/Documents/Quenya Course/` | 根目录：**只读** RTF 原著（勿改） |
| `less-a.rtf` ~ `less-d.rtf` | 第 1–20 课正文 |
| `keys.rtf` | 练习答案 |
| `q-vocab.rtf` | 练习用总词汇表 |
| `qappend.rtf` | 附录 |
| `/Users/luobowen/Documents/Quenya Course/quenya-web/` | 静态站工程（用户只打开这里面的 HTML） |

### 1.2 用户已明确拒绝的做法（上一任踩过的坑）

1. **不要**用 `fetch` + 本地服务器才能看的 SPA（`app.js` / `i18n.js` 等为早期遗留，**以 `scripts/build_content.py` 生成的 HTML 为准**）。
2. **不要**默认只展示英文、中文藏在折叠里；**中英对照应默认可见**。
3. **不要**把设计决策推给用户（形态、是否跑命令等由 Agent 定夺）。
4. **不要**让学习者执行 `python3 ...`；构建是维护者行为，生成结果须已写入 `index.html` 与 `lessons/*.html`。
5. **keys.rtf 解析**曾用 `re.split` 捕获组导致第 1 课答案错位——已改为 `finditer` 切课，接手后若再动 keys 逻辑须回归测试第 1 课答案块。
6. 练习工作台须可操作（输入/选择 → 核对 → 显示 keys），勿仅「显示答案」按钮。

### 1.3 维护者重建（学习者不涉及）

```bash
python3 "/Users/luobowen/Documents/Quenya Course/quenya-web/scripts/build_content.py"
```

会：读 RTF → 写 `data/*` → 写 `index.html` + `lessons/lesson-NN.html`。`RELEASED_LESSON_MAX = 20`（在 `build_content.py`）。

---

## 二、当前已完成的工作（事实清单）

### 2.1 数据管线（`scripts/build_content.py`）

- RTF → `data/lessons/lesson-NN.json`（`main` / `vocabulary` / `exercises` 分段 HTML）。
- `keys.json`：20 课答案 HTML（keys 切课已修复）。
- `vocabulary.json`（q-vocab）、`appendix.json`（qappend）、`catalog.json`、`meta.json`。
- 静态页生成：`render_lesson_page` + `render_teaching_modules` + 中英对照 + 练习工作台。
- 布局（CSS）：`--page-max` 约 1680px；课文页 **左侧 sticky 本章导航** + 主栏；首页宽屏 4–5 列课卡。

### 2.2 第 1 课（精耕样板，质量最高）

| 文件 | 作用 |
|------|------|
| `lesson-01-teaching.json` | 人工撰写的 5 步路径、目标、要点、表格、清单 |
| `lesson-01-pedagogy.json` | 章总览、思维导图结构 |
| `lesson-01-section-zh.json` | 大节中文 |
| `lesson-01-units-en.json` / `lesson-01-units-zh.json` | **逐段** 英/中（约 47 段），可对齐双栏 |
| `lesson-01-exercises.json` | 重音 A–J、h 类 K–T、电影附加题；工作台核对逻辑专用 |
| `lessons/lesson-01.html` | 已生成 |

练习：`assets/js/lesson-page.js`（重音输入、h 下拉核对、译题核对、keys 展开）。

### 2.3 第 2–20 课（批量上架，教学深度不足）

由 `scripts/generate_lesson_assets.py` 自动生成（`build_content.py` 的 `main()` 会调用）：

| 产物 | 内容 |
|------|------|
| `lesson-NN-teaching.json` | **模板化**中文：路径/模块标题/泛化目标，**非**细读原文后的教学设计 |
| `lesson-NN-pedagogy.json` | 标题 + Summary 摘录 + 简略 mindmap |
| `lesson-NN-units-en.json` | 从 HTML 拆段的英文 |
| `lesson-NN-section-zh.json` | 各 **大节** 中文译本（子 Agent 批量翻译） |
| `lesson-NN-exercises.json` | `kind: translation`；题干从 exercises 解析，答案从 keys 解析 |
| `lessons/lesson-02.html` … `lesson-20.html` | 已生成 |

中英呈现：当 `units-zh` 缺失或段数不一致时，用 **`bilingual-sheet--columns`**（左整节中文、右英文分段），**非**第 1 课那种逐段行对齐。

### 2.4 练习工作台（两类）

1. **第 1 课**：重音 + h 分类专用 UI。
2. **第 2–20 课**：译题 textarea + `wb-check-translate`（与 keys 字符串粗比对）+ 展开 keys。

### 2.5 已核对的数据完整性（上一任脚本结论）

- **20 课**正文 + 练习英文：在 JSON/HTML 中与 RTF **长度基本一致**（约 ≥92%）。
- **keys**：20 课均有答案块。
- **尚未挂上网页、仅在 JSON**：每课 **VOCABULARY** 块（第 2 课起）；**q-vocab** 总表、**qappend** 附录（无 `vocabulary.html` / `appendix.html`）；**keys.rtf 篇首说明**。
- **中文译本**：第 12–16 课等相对英文 **有压缩**，不宜称「与原著逐段等量」。

### 2.6 遗留 / 勿混淆

- `quenya-web/assets/js/app.js` 等旧 SPA 可忽略或删除以免混淆。
- `docs/PLAN.md` 为分章计划，可能滞后于现状。
- `README.md` 已注明学习者只双击 HTML。

---

## 三、核心问题判断（为何需要重构）

当前站点本质是：

> **「中文导航壳 + 英文原著全量展示 + 机翻/节译中文栏 + 简易练习台」**

而不是：

> **「按语法概念拆解、循序渐进、可自查理解的教学网站」**

具体不足：

1. **结构**：模块多名为「模块 · 第 N 课主干 / 某英文标题」，缺少与语法概念绑定的层级（定义 → 规则 → 例外 → 例句 → 易错点 → 小结 → 练习）。
2. **理解粒度**：除第 1 课外，没有「要点精讲 / 对照表 / 跟练清单」等细内容；`keyPoints` 常为空数组。
3. **双语策略不统一**：第 1 课逐段对齐；第 2–20 课整节对分段，不利于 **句级/规则级** 对照学习。
4. **词汇与附录**：原著要求的课末 VOCABULARY、总词汇表、附录未进入用户可见信息流。
5. **练习**：译题工作台仅有粗糙字符串匹配，缺少「考点提示、分步提示、与当课规则链接」。
6. **中文质量**：批量 `section-zh` 不能替代 **基于教学的改写**（小结、口诀、与中文学习者背景的说明）。

**你的任务不是推翻 RTF，而是重构前端信息架构与教学层 JSON/HTML**，使每一章在保留 **英文未删节** 的前提下，增加 **可消化的中文教学结构**。

---

## 四、重构目标（建议验收标准）

### 4.1 每一章页面应包含（自上而下建议）

1. **本章一句话** + **学完能做什么**（可操作目标，非空泛）。
2. **概念地图 / 本章目录**（与语法点一致，非 slug 英文标题）。
3. **分节教学单元**（每节固定模板，例如）：
   - 本节学习目标（3–5 条，可检验）
   - 核心规则（条目化 + 极简例句）
   - 对照表（英术语 | 中文 | 例 | 备注）
   - 常见例外 / 作者 NOTE 提要（链到双语原文位置）
   - **精读理解**（中文短文：解释「为什么这样」，不是复述英文）
   - **中英对照区**：英文必须完整；中文与英文层级对应（至少段落级，关键规则句级）
   - 自查清单（自测问题）
4. **课末词汇**（第 2 课起）：VOCABULARY RTF 全文 + 中文释义列（可与 q-vocab 交叉引用）。
5. **练习工作台**：分题显示考点；核对后链回规则；keys 全文可展开。
6. **本章 summary**：对齐原文 Summary of Lesson N，并附中文等价小结。

### 4.2 全站级页面（当前缺失）

- `vocabulary.html`：q-vocab 双列表 + 搜索（静态，无后端）。
- `appendix.html`：qappend 中英（可先英 + 中文章节导读）。
- `keys.html` 或 keys 前言：keys.rtf 开头说明。

### 4.3 技术与构建约定

- 继续 **构建时烘焙** 进 HTML（或内联 JSON 再渲染），保持 **file:// 可开**。
- 教学数据建议分文件：`lesson-NN-teaching.json`（重构重点）、`lesson-NN-glossary.json`（课末词）、可选 `lesson-NN-units-zh.json`（逐段中译）。
- **禁止**为赶进度全课机器一次性幻觉；**按章验收**（对照 RTF 抽检），再 `RELEASED_LESSON_MAX` 或 quality flag。
- 第 1 课为样板：第 2 课起重构时 **对齐第 1 课的信息密度与组件**，而非对齐当前 `generate_lesson_assets` 的稀疏模板。

---

## 五、推荐接手工作流程

1. **读** `lessons/lesson-01.html` + `lesson-01-teaching.json`，理解「好样板」组件。
2. **读** `lessons/lesson-02.html`，对比差距（你会觉得「像资料站不像课」——这是要改的）。
3. **定组件规范**：在 `main.css` + `build_content.py` 的 render 函数中固化 **教学块类型**（规则卡、对照表、精读、双语、练习、词汇）。
4. **先重构第 2 课端到端**（名词/复数/冠词），用户或维护者满意后，复制流程到第 3–20 课（**逐课**，勿一夜 19 课幻觉）。
5. 每课完成：`build_content.py` → 打开 HTML 自检 → 对照 `keys.rtf` 抽 3 题 → 对照 VOCABULARY 是否在页上。
6. 更新 `docs/PLAN.md` 与本文「进度」节。

---

## 六、关键文件索引（接手优先读）

```
quenya-web/
├── scripts/build_content.py       # 主构建 + HTML 渲染
├── scripts/generate_lesson_assets.py  # 2–20 课自动骨架（待替换/增强）
├── data/lessons/lesson-NN.json    # 英文 HTML 源
├── data/lessons/lesson-NN-*.json  # 教学 / 双语 / 练习
├── assets/css/main.css
├── assets/js/lesson-page.js       # 练习交互
├── lessons/lesson-NN.html         # 用户打开的文件
└── docs/PLAN.md
```

原著只读：`/Users/luobowen/Documents/Quenya Course/*.rtf`

---

## 七、给接手 Agent 的一句话任务

在**不改变 RTF 原文完整性**的前提下，**重构静态前端的信息架构与教学 JSON**，使每一章具备**清晰、可检验、细粒度的中文教学结构**（目标 → 规则 → 理解 → 对照原文 → 词汇 → 练习），补齐 **课末词汇、总词汇表、附录** 的浏览页，统一双语呈现策略；**降低「原文粘贴感」**，提升「学完能理解规则」的密度。**默认交付已生成的 HTML，不要求用户跑任何命令。**

---

## 八、进度快照（交接时）

| 项目 | 状态 |
|------|------|
| 20 课英文正文+练习进 HTML | ✅ |
| 20 课 keys 进页 | ✅ |
| 第 1 课精细教学 + 逐段双语 | ✅ |
| 第 2–20 课重做（schemaVersion 2 + 逐段双语 + 练习工作台） | ✅ |
| 第 20 课（最后一课） | ✅ 已重做 |
| 课末 VOCABULARY 在页上 | ✅（第 1–20 课） |
| q-vocab / qappend 浏览页 | ✅ |
| 教学理解层（规则/表/精读） | ✅ 第 1–20 课 |
| 中文译本与英文等量 | ✅ 第 1–20 课（逐段 1:1） |

**已验收课次（每课均跑 `verify.py N` + `audit.py N` 全绿）**：第 2、3、4、5、6、7、8、9、10、11、12、13、14、15、16、17、18、19、20 课（全部）。
第 9 课：覆盖率 1.0000、五节逐段对齐、keys 16/16、词汇 12/12、模块 32、对照行 90、引文 56/56。
第 10 课：覆盖率 1.0000、六节逐段对齐（34/11/9/20/20/12）、keys 16/16、词汇 12/12、模块 41、对照行 105、引文 89/89。
第 11 课：覆盖率 1.0000、四节逐段对齐（7/39/18/12）、keys 16/16、词汇 12/12、模块 44、对照行 75、引文 62/62。
第 12 课：覆盖率 1.0000、六节逐段对齐（1/18/8/17/19/12）、keys 16/16、词汇 12/12、模块 41、对照行 74、引文 57/57。
第 13 课：覆盖率 1.0000、六节逐段对齐（20/20/13/3/18/14）、keys 16/16、词汇 12/12、模块 52、对照行 87、引文 111/111。
第 14 课：覆盖率 1.0000、四节逐段对齐（41/36/31/14）、keys 16/16、词汇 12/12、模块 52、对照行 121、引文 110/110。
第 15 课：覆盖率 1.0000、六节逐段对齐（14/12/30/10/20/12）、keys 16/16、词汇 12/12、模块 59、对照行 97、引文 138/138。
第 16 课：覆盖率 1.0000、六节逐段对齐（34/6/11/1/18/12）、keys 16/16、词汇 12/12、模块 50、对照行 81、引文 120/120。
第 17 课：覆盖率 1.0000、六节逐段对齐（13/19/10/12/18/14）、keys 16/16、词汇 12/12、模块 44、对照行 85、引文 126/126。
第 18 课：覆盖率 1.0000、五节逐段对齐（22/6/22/19/12）、keys 16/16、词汇 12/12、模块 52、对照行 80、引文 158/158。
第 19 课：覆盖率 1.0000、六节逐段对齐（8/19/5/5/19/13）、keys 16/16、词汇 12/12、模块 39、对照行 68、引文 181/181。
第 20 课：覆盖率 1.0000、五节逐段对齐（46/9/1/20/13）、keys 16/16、词汇 12/12、模块 50、对照行 88、引文 217/217。

**重做一课的固定流程**（照此逐课推进，勿整批生成）：
1. `python3 -c` 读 `lesson-NN-units-en.json` 拿每节段数；`textutil` 抽 `keys.rtf` 该课答案；
2. 写 `lesson-NN-units-zh.json`（**段数必须与 en 完全相等**，逐段直译，不合并）；
3. 写 `lesson-NN-teaching.json`（`schemaVersion: 2`，模块按「概念 → 规则 → 例外 → 例句 → 易错 → 精读 → 小结 → 自查」铺，每模块挂 `bilingual.unitIds`，**所有单元恰好分配一次**）；
4. 写 `glossary.json`（词条须在页面上出现）、`exercises.json`（`answerKey` 必须逐字取自 keys）、`pedagogy.json`；
5. `python3 scripts/build_content.py` → `verify.py N` → `audit.py N`，修到全绿；
6. 抽查截图（1440 宽）确认无溢出。

**下一任主要工作：前端与教学层重构，而非从零做静态站。**