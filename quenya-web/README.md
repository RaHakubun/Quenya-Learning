# 昆雅语互动教程（分章建设中）

基于目录内 Helge Kåre Fauskanger 课程 RTF **原文** 的静态站点。**第 1–20 课全部上线**；第 2–20 课已按统一教学层（逐段中英对照 + 规则卡 + 练习工作台）重做并通过 `verify` / `audit` 全绿验收。

## 打开方式（学习者）

**直接双击**下面任一文件即可用浏览器阅读，无需安装任何东西、**无需**运行命令、**无需**开本地端口：

- `index.html` — 目录
- `lessons/lesson-01.html` … `lessons/lesson-20.html` — 第 1–20 课

页面内容已经写在 HTML 里；你平时**不用**执行任何 python。

## 仅供维护者：从 RTF 重新生成（学习者请忽略）

只有在你改了上一级 RTF 或 `scripts/build_content.py`、需要把新内容写回 HTML 时，才在终端运行 `python3 scripts/build_content.py`。原始 RTF 不被脚本修改。

## 分章计划

见 [docs/PLAN.md](docs/PLAN.md) 与 [docs/AGENT_HANDOFF_PROMPT.md](docs/AGENT_HANDOFF_PROMPT.md)（后者记录逐课验收数据）。上架课次由 `scripts/build_content.py` 中的 `RELEASED_LESSON_MAX` 控制，当前为 20。