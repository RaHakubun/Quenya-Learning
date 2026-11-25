import { RELEASED_LESSON_MAX } from "./config.js";
import { loadMeta, t, getLang, setLang, initI18nBodyClass } from "./i18n.js";

const LESSON_WORDS = [
  "",
  "ONE",
  "TWO",
  "THREE",
  "FOUR",
  "FIVE",
  "SIX",
  "SEVEN",
  "EIGHT",
  "NINE",
  "TEN",
  "ELEVEN",
  "TWELVE",
  "THIRTEEN",
  "FOURTEEN",
  "FIFTEEN",
  "SIXTEEN",
  "SEVENTEEN",
  "EIGHTEEN",
  "NINETEEN",
  "TWENTY",
];

let catalog = null;

initI18nBodyClass();

async function ensureCatalog() {
  if (!catalog) {
    const res = await fetch("data/catalog.json");
    catalog = await res.json();
  }
  return catalog;
}

function slugHeading(text) {
  return text
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-|-$/g, "");
}

function injectSectionIds(html) {
  const wrap = document.createElement("div");
  wrap.innerHTML = html;
  wrap.querySelectorAll("h3.section-heading").forEach((h) => {
    h.id = slugHeading(h.textContent.trim());
  });
  return wrap.innerHTML;
}

function renderNav(active) {
  const ul = document.getElementById("lesson-nav");
  if (!ul) return;
  ul.innerHTML = "";
  for (let n = 1; n <= 20; n++) {
    const li = document.createElement("li");
    if (n <= RELEASED_LESSON_MAX) {
      const a = document.createElement("a");
      a.href = `#/lesson/${n}`;
      const cat = catalog?.find((c) => c.number === n);
      const zh = cat?.titleZh || "";
      a.textContent =
        getLang() === "zh"
          ? `${t("lesson", { n })}：${zh}`
          : `Lesson ${n}${cat?.subtitleEn ? ` — ${cat.subtitleEn.split(".")[0]}` : ""}`;
      if (active === n) a.classList.add("active");
      li.appendChild(a);
    } else {
      const span = document.createElement("span");
      span.className = "locked";
      span.textContent =
        getLang() === "zh" ? `第 ${n} 课（待制作）` : `Lesson ${n} (coming)`;
      li.appendChild(span);
    }
    ul.appendChild(li);
  }
}

async function renderHome(main) {
  await ensureCatalog();
  const pct = (RELEASED_LESSON_MAX / 20) * 100;
  main.innerHTML = `
    <div class="panel home-hero">
      <h1>${t("siteTitle")}</h1>
      <p>${t("siteSubtitle")}</p>
      <p class="prose-zh">${t("authorNote")}</p>
      <div class="progress-bar" style="--pct: ${pct}%"><span></span></div>
      <p style="margin-top:1rem;color:var(--text-muted);font-size:0.9rem">
        ${getLang() === "zh" ? `已开放：第 1–${RELEASED_LESSON_MAX} 课 / 共 20 课` : `Released: lessons 1–${RELEASED_LESSON_MAX} of 20`}
      </p>
      <p style="margin-top:1.5rem">
        <a class="btn btn-primary" href="#/lesson/1">${t("readLesson")} →</a>
      </p>
    </div>
    <div class="panel">
      <h2 style="font-family:var(--font-display);color:var(--gold);font-size:1rem">${
        getLang() === "zh" ? "分章制作计划" : "Rollout plan"
      }</h2>
      <p class="prose-zh">${
        getLang() === "zh"
          ? "本站按章节逐步上线：每课正文从 RTF 原件转换而来，经对照验收后才解锁下一课。详见 <code>docs/PLAN.md</code>。"
          : "Lessons go live one at a time after RTF verification. See <code>docs/PLAN.md</code>."
      }</p>
    </div>
  `;
}

async function renderLesson(n, main) {
  if (n > RELEASED_LESSON_MAX) {
    main.innerHTML = `<div class="panel"><p class="prose-zh">${
      getLang() === "zh"
        ? `第 ${n} 课尚未制作完成。请先学习已开放的章节。`
        : `Lesson ${n} is not released yet.`
    }</p></div>`;
    return;
  }

  const [lessonRes, keyRes] = await Promise.all([
    fetch(`data/lessons/lesson-${String(n).padStart(2, "0")}.json`),
    fetch("data/keys.json"),
  ]);
  const lesson = await lessonRes.json();
  const keys = await keyRes.json();

  let pedagogy = null;
  if (n === 1) {
    const pedRes = await fetch("data/lessons/lesson-01-pedagogy.json");
    pedagogy = await pedRes.json();
  }

  const word = LESSON_WORDS[n] || n;
  const mainHtml = injectSectionIds(lesson.html.main);
  const exHtml = lesson.html.exercises
    ? injectSectionIds(lesson.html.exercises)
    : "";

  let pedagogyBlock = "";
  if (pedagogy) {
    const branches = pedagogy.mindmap.branches
      .map(
        (b) =>
          `<button type="button" class="mindmap-branch" data-section="${b.sectionId}">${
            getLang() === "zh" ? b.labelZh : b.labelEn
          }</button>`
      )
      .join("");
    const toc = pedagogy.sections
      .map((s) => {
        const label = getLang() === "zh" ? s.headingZh : s.headingEn;
        const href = s.id === "exercises" ? "#exercises" : `#${slugHeading(s.anchor)}`;
        return `<a href="${href}">${label}</a>`;
      })
      .join("");
    pedagogyBlock = `
      <div class="panel" id="pedagogy">
        <span class="badge">${getLang() === "zh" ? "学习导航（非原文）" : "Study guide (not source text)"}</span>
        <h2 style="font-family:var(--font-display);color:var(--gold);font-size:1rem;margin:0 0 0.5rem">${t("summary")}</h2>
        <p class="prose-zh">${pedagogy.summaryZh}</p>
        <p style="font-size:0.85rem;color:var(--text-muted)">${
          getLang() === "zh" ? pedagogy.exerciseGuideZh : "Exercises: stress (A–J) and h-types (K–T). Use Show answers."
        }</p>
        <h2 style="font-family:var(--font-display);color:var(--gold);font-size:1rem;margin:1.25rem 0 0.5rem">${t("mindmap")}</h2>
        <div class="mindmap" role="navigation" aria-label="${t("mindmap")}">
          <div class="mindmap-core">${
            getLang() === "zh" ? pedagogy.mindmap.rootZh : pedagogy.mindmap.rootEn
          }</div>
          ${branches}
        </div>
        <p style="font-size:0.8rem;color:var(--text-muted)">${t("mindmapTip")}</p>
        <div class="toc-chips">${toc}</div>
      </div>
    `;
  }

  main.innerHTML = `
    <article class="panel">
      <h1>${getLang() === "zh" && pedagogy ? pedagogy.titleZh : `LESSON ${word}`}</h1>
      <p class="lesson-subtitle">${lesson.subtitleEn}</p>
      <p style="font-size:0.85rem;color:var(--text-muted)">
        ${getLang() === "zh" ? "以下正文为课程原文（英文），未删节。" : "Full original lesson text below."}
      </p>
    </article>
    ${pedagogyBlock}
    <div class="panel lesson-content font-quenya" id="lesson-body">
      ${mainHtml}
    </div>
    ${
      exHtml
        ? `
    <div class="panel exercise-panel" id="exercises">
      <h2 style="font-family:var(--font-display);color:var(--gold)">${t("exercises")}</h2>
      <div class="lesson-content">${exHtml}</div>
      <button type="button" class="btn btn-primary" id="toggle-key">${t("showKey")}</button>
      <div class="key-reveal" id="key-box" hidden>
        <h3 style="color:var(--gold);font-family:var(--font-display);font-size:0.95rem">${t("navKeys")}</h3>
        <div class="lesson-content">${keys[String(n)]?.html || "<p>—</p>"}</div>
      </div>
    </div>`
        : ""
    }
  `;

  document.getElementById("toggle-key")?.addEventListener("click", () => {
    const box = document.getElementById("key-box");
    const btn = document.getElementById("toggle-key");
    const open = box.hidden;
    box.hidden = !open;
    btn.textContent = open ? t("hideKey") : t("showKey");
  });

  main.querySelectorAll(".mindmap-branch").forEach((btn) => {
    btn.addEventListener("click", () => {
      const sec = pedagogy.sections.find((s) => s.id === btn.dataset.section);
      if (!sec) return;
      const targetId =
        sec.id === "exercises" ? "exercises" : slugHeading(sec.anchor);
      document.getElementById(targetId)?.scrollIntoView({
        behavior: "smooth",
        block: "start",
      });
    });
  });
}

async function route() {
  await loadMeta();
  await ensureCatalog();
  document.getElementById("site-title").textContent = t("siteTitle");
  document.getElementById("site-tagline").textContent = t("siteSubtitle");
  document.getElementById("lang-toggle").textContent = t("langToggle");

  const hash = location.hash.replace(/^#\/?/, "") || "home";
  const main = document.getElementById("main");
  let activeLesson = null;

  if (hash === "home" || hash === "") {
    await renderHome(main);
  } else if (hash.startsWith("lesson/")) {
    const n = parseInt(hash.split("/")[1], 10);
    if (!Number.isNaN(n)) {
      activeLesson = n;
      await renderLesson(n, main);
    }
  } else {
    await renderHome(main);
  }

  renderNav(activeLesson);
  const key = activeLesson ? `lesson-${activeLesson}` : "home";
  if (activeLesson) {
    const done = JSON.parse(localStorage.getItem("quenya-progress") || "{}");
    done[key] = true;
    localStorage.setItem("quenya-progress", JSON.stringify(done));
  }
}

document.getElementById("lang-toggle")?.addEventListener("click", () => {
  setLang(getLang() === "zh" ? "en" : "zh");
  route();
});

document.getElementById("font-toggle")?.addEventListener("click", () => {
  document.body.classList.toggle("font-quenya-latin");
  const on = !document.body.classList.contains("font-quenya-latin");
  document.getElementById("lesson-body")?.classList.toggle("font-quenya", on);
});

window.addEventListener("hashchange", route);

loadMeta().then(() => {
  if (location.protocol === "file:") {
    const main = document.getElementById("main");
    main.innerHTML = `<div class="panel"><p class="prose-zh">请用本地服务器打开（浏览器会拦截 file:// 的 JSON 请求）：<br><code>cd quenya-web && python3 -m http.server 8765</code><br>然后访问 <code>http://localhost:8765</code></p></div>`;
    return;
  }
  route();
});