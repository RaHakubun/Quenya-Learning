(function () {
  function normalizeStress(s) {
    return (s || "")
      .trim()
      .toLowerCase()
      .replace(/\s+/g, "")
      .replace(/á/g, "a")
      .replace(/é/g, "e")
      .replace(/í/g, "i")
      .replace(/ó/g, "o")
      .replace(/ú/g, "u");
  }

  function stressInputMatches(input, answerVowel) {
    var raw = (input || "").trim();
    if (!raw) return null;
    var normIn = normalizeStress(raw);
    var normAns = normalizeStress(answerVowel);
    if (!normAns) return null;
    if (normIn === normAns) return true;
    if (normIn.indexOf(normAns) >= 0) return true;
    // allow two-letter diphthong answers when user typed longer phrase
    if (normAns.length === 2 && normIn.indexOf(normAns) >= 0) return true;
    return false;
  }

  function setExplainOpen(node, open) {
    if (!node) return;
    node.classList.toggle("is-open", !!open);
  }

  var keyBtn = document.getElementById("toggle-key");
  var keyPanel = document.getElementById("key-box");
  if (keyBtn && keyPanel) {
    keyBtn.addEventListener("click", function () {
      if (typeof keyPanel.open === "boolean") {
        keyPanel.open = true;
      } else {
        keyPanel.setAttribute("open", "");
      }
      keyPanel.scrollIntoView({ behavior: "smooth", block: "nearest" });
    });
  }

  document.querySelectorAll(".wb-reveal").forEach(function (btn) {
    btn.addEventListener("click", function () {
      var cell = btn.closest("td");
      if (!cell) return;
      var explain = cell.querySelector(".wb-explain");
      if (!explain) return;
      var open = !explain.classList.contains("is-open");
      setExplainOpen(explain, open);
      btn.textContent = open ? "隐藏解析" : "显示解析";
    });
  });

  document.querySelectorAll(".wb-check-stress").forEach(function (btn) {
    btn.addEventListener("click", function () {
      var cell = btn.closest("td");
      if (!cell) return;
      var input = cell.querySelector(".wb-stress-input");
      var feedback = cell.querySelector(".wb-feedback");
      var explain = cell.querySelector(".wb-explain");
      var tr = btn.closest("tr");
      var vowel = btn.getAttribute("data-answer-vowel") || "";
      if (!input || !feedback) return;
      var match = stressInputMatches(input.value, vowel);
      tr.classList.remove("wb-right", "wb-wrong");
      if (match === null) {
        feedback.textContent = "请先在「你的标注」里写下元音或双元音（如 a、ui）。";
        feedback.className = "wb-feedback wb-feedback-warn";
        return;
      }
      if (match) {
        tr.classList.add("wb-right");
        feedback.textContent = "正确：重读元音/双元音为「" + vowel + "」。";
        feedback.className = "wb-feedback wb-feedback-ok";
        setExplainOpen(explain, true);
        var revealBtn = cell.querySelector(".wb-reveal");
        if (revealBtn) revealBtn.textContent = "隐藏解析";
      } else {
        tr.classList.add("wb-wrong");
        feedback.textContent = "还不对。可再想想，或点「显示解析」看规则说明。";
        feedback.className = "wb-feedback wb-feedback-bad";
      }
    });
  });

  document.querySelectorAll(".wb-stress-input").forEach(function (input) {
    input.addEventListener("keydown", function (ev) {
      if (ev.key === "Enter") {
        var cell = input.closest("td");
        var btn = cell && cell.querySelector(".wb-check-stress");
        if (btn) btn.click();
      }
    });
  });

  var revealAll = document.getElementById("wb-reveal-all-part1");
  var hideAll = document.getElementById("wb-hide-all-part1");
  if (revealAll) {
    revealAll.addEventListener("click", function () {
      document.querySelectorAll("#workbench .wb-explain").forEach(function (p) {
        setExplainOpen(p, true);
      });
      document.querySelectorAll("#workbench .wb-reveal").forEach(function (b) {
        b.textContent = "隐藏解析";
      });
    });
  }
  if (hideAll) {
    hideAll.addEventListener("click", function () {
      document.querySelectorAll("#workbench .wb-explain").forEach(function (p) {
        setExplainOpen(p, false);
      });
      document.querySelectorAll("#workbench .wb-reveal").forEach(function (b) {
        b.textContent = "显示解析";
      });
    });
  }

  function resetGradeRow(tr) {
    tr.classList.remove("wb-right", "wb-wrong");
    var feedback = tr.querySelector(".wb-cell-grade .wb-feedback");
    var keyLine = tr.querySelector(".wb-key-line");
    var btn = tr.querySelector(".wb-grade");
    if (feedback) {
      feedback.textContent = "";
      feedback.className = "wb-feedback";
    }
    if (keyLine) keyLine.classList.remove("is-open");
    if (btn) btn.textContent = "核对";
  }

  document.querySelectorAll(".wb-select").forEach(function (sel) {
    sel.addEventListener("change", function () {
      var tr = sel.closest("tr");
      if (tr) resetGradeRow(tr);
    });
  });

  function normTrans(s) {
    return (s || "")
      .toLowerCase()
      .normalize("NFD")
      .replace(/[\u0300-\u036f]/g, "")
      .replace(/\([^)]*\)/g, " ")
      .replace(/[\u2018\u2019\u201c\u201d"'`.,;:!?，。！？、；：（）()\[\]\-–—]/g, " ")
      .replace(/\s+/g, " ")
      .trim();
  }

  function referenceAnswers(keyLine) {
    var refs = [keyLine.textContent];
    try {
      var alts = JSON.parse(keyLine.getAttribute("data-answer-alt") || "[]");
      if (alts && alts.length) refs = refs.concat(alts);
    } catch (e) { /* 数据缺失时退回单一答案 */ }
    var zh = keyLine.getAttribute("data-answer-zh");
    if (zh) refs.push(zh);
    return refs.map(normTrans).filter(Boolean);
  }

  function toggleAnswerPair(cell, open) {
    var keyLine = cell.querySelector(".wb-key-line");
    var zhLine = cell.querySelector(".wb-answer-zh");
    if (keyLine) keyLine.classList.toggle("is-open", open);
    if (zhLine) zhLine.classList.toggle("is-open", open);
    var reveal = cell.querySelector(".wb-reveal-keyline");
    if (reveal) reveal.textContent = open ? "隐藏答案" : "显示答案";
  }

  document.querySelectorAll(".wb-check-translate").forEach(function (btn) {
    btn.addEventListener("click", function () {
      var cell = btn.closest("td");
      if (!cell) return;
      var ta = cell.querySelector(".wb-translate-input");
      var keyLine = cell.querySelector(".wb-key-line");
      var feedback = cell.querySelector(".wb-feedback");
      var tr = btn.closest("tr");
      if (!ta || !keyLine || !feedback) return;
      var mine = normTrans(ta.value);
      var refs = referenceAnswers(keyLine);
      tr.classList.remove("wb-right", "wb-wrong");
      if (!mine) {
        feedback.textContent = "请先写下译文再核对。";
        feedback.className = "wb-feedback wb-feedback-warn";
        return;
      }
      var exact = refs.some(function (r) { return r === mine; });
      var close = refs.some(function (r) {
        return mine.length >= 2 && (r.indexOf(mine) >= 0 || mine.indexOf(r) >= 0);
      });
      if (exact || close) {
        tr.classList.add("wb-right");
        feedback.textContent = exact
          ? "与 keys 一致（含可接受的替代译文）。"
          : "与 keys 高度接近，仍请对照下方答案确认拼写。";
        feedback.className = "wb-feedback wb-feedback-ok";
      } else {
        tr.classList.add("wb-wrong");
        feedback.textContent = "与 keys 有出入，请对照下方答案与中文解析修改。";
        feedback.className = "wb-feedback wb-feedback-bad";
      }
      toggleAnswerPair(cell, true);
    });
  });

  document.querySelectorAll(".wb-reveal-keyline").forEach(function (btn) {
    btn.addEventListener("click", function () {
      var cell = btn.closest("td");
      var keyLine = cell && cell.querySelector(".wb-key-line");
      if (!keyLine) return;
      toggleAnswerPair(cell, !keyLine.classList.contains("is-open"));
    });
  });

  // 学习目标：勾选后即时显示本课完成度，并记住进度。
  var checks = Array.prototype.slice.call(document.querySelectorAll(".cando-check"));
  var countNode = document.getElementById("cando-count");
  var barNode = document.getElementById("cando-bar-fill");
  var candoKey = "quenya-cando:" + location.pathname;
  function saveCando() {
    try {
      var on = [];
      checks.forEach(function (c, i) { if (c.checked) on.push(i); });
      localStorage.setItem(candoKey, JSON.stringify(on));
    } catch (e) {}
  }
  function refreshCando() {
    if (!countNode) return;
    var done = checks.filter(function (c) { return c.checked; }).length;
    countNode.textContent = String(done);
    if (barNode) barNode.style.width = (checks.length ? (done / checks.length) * 100 : 0) + "%";
  }
  try {
    var saved = JSON.parse(localStorage.getItem(candoKey) || "[]");
    if (Array.isArray(saved)) {
      saved.forEach(function (i) { if (checks[i]) checks[i].checked = true; });
    }
  } catch (e) {}
  checks.forEach(function (c) {
    c.addEventListener("change", function () { refreshCando(); saveCando(); });
  });
  refreshCando();

  document.querySelectorAll(".wb-grade").forEach(function (btn) {
    btn.addEventListener("click", function () {
      var tr = btn.closest("tr");
      if (!tr) return;
      var sel = tr.querySelector(".wb-select");
      var feedback = tr.querySelector(".wb-cell-grade .wb-feedback");
      var keyLine = tr.querySelector(".wb-key-line");
      if (!sel || !feedback || !keyLine) return;
      var pick = (sel.value || "").toUpperCase();
      var correct = (btn.getAttribute("data-correct") || "").toUpperCase();
      var alt = (btn.getAttribute("data-answer-alt") || "").toUpperCase();
      tr.classList.remove("wb-right", "wb-wrong");
      if (!pick) {
        feedback.textContent = "请先在「你的选项」里选 A / B / C / D。";
        feedback.className = "wb-feedback wb-feedback-warn";
        return;
      }
      var ok = pick === correct || (alt && pick === alt);
      if (ok) {
        tr.classList.add("wb-right");
        if (pick === correct) {
          feedback.textContent = "正确：" + correct + "。";
        } else {
          feedback.textContent = "可接受：" + pick + "（早期/特殊读法，标准答案为 " + correct + "）。";
        }
        feedback.className = "wb-feedback wb-feedback-ok";
        keyLine.classList.add("is-open");
        btn.textContent = "正确";
      } else {
        tr.classList.add("wb-wrong");
        feedback.textContent = "不对。答案为 " + correct + (alt ? "（或早期口音 " + alt + "）" : "") + "，点「核对」后可看解析。";
        feedback.className = "wb-feedback wb-feedback-bad";
        keyLine.classList.add("is-open");
        btn.textContent = "再核对";
      }
    });
  });
})();