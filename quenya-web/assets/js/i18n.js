let meta = null;
let lang = localStorage.getItem("quenya-ui-lang") || "zh";

export function getLang() {
  return lang;
}

export function setLang(next) {
  lang = next === "en" ? "en" : "zh";
  localStorage.setItem("quenya-ui-lang", lang);
  document.body.classList.toggle("lang-zh", lang === "zh");
  document.body.classList.toggle("lang-en", lang === "en");
}

export async function loadMeta() {
  if (!meta) {
    const res = await fetch("data/meta.json");
    meta = await res.json();
  }
  return meta;
}

export function t(key, vars = {}) {
  const ui = meta?.ui?.[lang] || meta?.ui?.zh || {};
  let s = ui[key] || key;
  for (const [k, v] of Object.entries(vars)) {
    s = s.replace(`{${k}}`, String(v));
  }
  return s;
}

export function initI18nBodyClass() {
  document.body.classList.add(lang === "en" ? "lang-en" : "lang-zh");
}