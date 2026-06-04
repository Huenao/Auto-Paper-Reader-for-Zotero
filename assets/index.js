(function () {
  const items = (window.APRZ_NOTE_INDEX && window.APRZ_NOTE_INDEX.items) || [];
  const searchInput = document.getElementById("search");
  const statusSelect = document.getElementById("status");
  const papersEl = document.getElementById("papers");
  const categoriesEl = document.getElementById("categories");
  let activeCategory = "";

  function textOf(item) {
    return [
      item.title,
      (item.authors || []).join(" "),
      (item.tags || []).join(" "),
      item.pdf_rel_path,
      item.note_rel_path,
      item.summary
    ].join(" ").toLowerCase();
  }

  function categoryKey(item) {
    return (item.category_path || []).join("/");
  }

  function filteredItems() {
    const q = (searchInput.value || "").trim().toLowerCase();
    const status = statusSelect.value;
    return items.filter((item) => {
      if (q && !textOf(item).includes(q)) return false;
      if (activeCategory && categoryKey(item) !== activeCategory) return false;
      if (status === "source_missing") return item.source_status === "source_missing";
      if (status && item.status !== status) return false;
      return true;
    });
  }

  function renderCategories() {
    const counts = new Map();
    items.forEach((item) => {
      const key = categoryKey(item) || "(root)";
      counts.set(key, (counts.get(key) || 0) + 1);
    });
    const all = document.createElement("button");
    all.className = "category";
    all.textContent = "全部";
    all.addEventListener("click", () => {
      activeCategory = "";
      renderPapers();
    });
    categoriesEl.appendChild(all);
    Array.from(counts.keys()).sort().forEach((key) => {
      const btn = document.createElement("button");
      btn.className = "category";
      btn.textContent = `${key} (${counts.get(key)})`;
      btn.addEventListener("click", () => {
        activeCategory = key === "(root)" ? "" : key;
        renderPapers();
      });
      categoriesEl.appendChild(btn);
    });
  }

  function renderPapers() {
    papersEl.innerHTML = "";
    const visible = filteredItems();
    if (!visible.length) {
      papersEl.textContent = "没有匹配的论文。";
      return;
    }
    visible.forEach((item) => {
      const article = document.createElement("article");
      article.className = "paper";
      const title = document.createElement("h3");
      title.textContent = item.title || item.pdf_rel_path;
      const meta = document.createElement("p");
      meta.className = "meta";
      meta.textContent = `${(item.authors || []).join(", ")} ${item.year || ""} ${item.venue || ""}`.trim();
      const summary = document.createElement("p");
      summary.className = "summary";
      summary.textContent = item.summary || "尚未生成笔记。";
      const path = document.createElement("p");
      path.className = "path";
      path.textContent = item.pdf_rel_path;
      const links = document.createElement("p");
      if (item.note_href) {
        const note = document.createElement("a");
        note.href = item.note_href;
        note.textContent = "打开笔记";
        links.appendChild(note);
      }
      if (item.pdf_href) {
        const pdf = document.createElement("a");
        pdf.href = item.pdf_href;
        pdf.textContent = "打开 PDF";
        links.appendChild(pdf);
      }
      article.append(title, meta, summary, path, links);
      papersEl.appendChild(article);
    });
  }

  searchInput.addEventListener("input", renderPapers);
  statusSelect.addEventListener("change", renderPapers);
  renderCategories();
  renderPapers();
})();
