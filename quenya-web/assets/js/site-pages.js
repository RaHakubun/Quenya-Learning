/* 全站资料页交互：纯前端、无 fetch、file:// 可用。 */
(function () {
  var input = document.getElementById("vocab-search");
  if (!input) return;

  var rows = Array.prototype.slice.call(document.querySelectorAll(".vocab-list-table tbody tr"));
  var countNode = document.getElementById("vocab-count");
  var listCounts = Array.prototype.slice.call(document.querySelectorAll(".list-count"));

  function norm(s) {
    return (s || "").toLowerCase().trim();
  }

  function apply() {
    var q = norm(input.value);
    var shown = 0;
    rows.forEach(function (row) {
      var hay = norm(row.getAttribute("data-search"));
      var hit = !q || hay.indexOf(q) >= 0;
      row.classList.toggle("is-hidden", !hit);
      if (hit) shown += 1;
    });
    if (countNode) {
      countNode.textContent = q ? "匹配 " + shown + " / " + rows.length + " 条" : "共 " + rows.length + " 条";
    }
    // 每张表单独计数
    var groups = [
      { sel: "#qe", rows: document.querySelectorAll("#qe .vocab-list-table tbody tr") },
      { sel: "#eq", rows: document.querySelectorAll("#eq .vocab-list-table tbody tr") }
    ];
    groups.forEach(function (g, i) {
      if (!listCounts[i]) return;
      var visible = 0;
      Array.prototype.forEach.call(g.rows, function (r) {
        if (!r.classList.contains("is-hidden")) visible += 1;
      });
      listCounts[i].textContent = "（" + visible + " 条）";
    });
  }

  input.addEventListener("input", apply);
  input.addEventListener("keydown", function (ev) {
    if (ev.key === "Escape") {
      input.value = "";
      apply();
    }
  });
  apply();
})();
