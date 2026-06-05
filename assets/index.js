(function () {
  const items = (window.APRZ_NOTE_INDEX && window.APRZ_NOTE_INDEX.items) || [];
  const state = {
    category: "All",
    status: "All",
    search: "",
  };

  const els = {
    search: document.getElementById("search"),
    statusFilters: document.getElementById("statusFilters"),
    categoryGrid: document.getElementById("categoryGrid"),
    papers: document.getElementById("papers"),
    resultCount: document.getElementById("resultCount"),
    queueList: document.getElementById("queueList"),
    template: document.getElementById("paperCardTemplate"),
  };

  function text(value) {
    return String(value || "").trim();
  }

  function list(value) {
    return Array.isArray(value) ? value : [];
  }

  function categoryOf(item) {
    return text(item.research_area) || (list(item.category_path)[0] || "Unclassified");
  }

  function subtopicOf(item) {
    const categoryPath = list(item.category_path);
    return text(item.primary_subtopic) || categoryPath[categoryPath.length - 1] || "General";
  }

  function readingStatus(item) {
    return text(item.reading_status) || text(item.status) || "unread";
  }

  function priorityClass(value) {
    return text(value).toLowerCase().replace(/[^a-z0-9]+/g, "-") || "saved";
  }

  function countBy(values, getter) {
    return values.reduce((acc, item) => {
      const key = getter(item);
      acc.set(key, (acc.get(key) || 0) + 1);
      return acc;
    }, new Map());
  }

  function searchText(item) {
    return [
      item.title,
      list(item.authors).join(" "),
      list(item.tags).join(" "),
      item.pdf_rel_path,
      item.note_rel_path,
      item.summary,
      categoryOf(item),
      subtopicOf(item),
      item.problem_preview,
      item.method_preview,
      item.findings_preview,
      item.value_preview,
      item.next_action,
    ].join(" ").toLowerCase();
  }

  function matchesStatus(item) {
    if (state.status === "All") return true;
    if (state.status === "queue") return item.status !== "read" || item.source_status === "source_missing";
    if (state.status === "source_missing") return item.source_status === "source_missing";
    return item.status === state.status;
  }

  function filteredItems() {
    const query = state.search.trim().toLowerCase();
    return items
      .filter((item) => state.category === "All" || categoryOf(item) === state.category)
      .filter(matchesStatus)
      .filter((item) => !query || searchText(item).includes(query))
      .sort((a, b) => {
        const categoryDelta = categoryOf(a).localeCompare(categoryOf(b));
        if (categoryDelta !== 0) return categoryDelta;
        return text(a.title).localeCompare(text(b.title));
      });
  }

  function button(label, count, active, onClick) {
    const node = document.createElement("button");
    node.type = "button";
    node.className = `filter-btn${active ? " active" : ""}`;
    node.textContent = `${label} ${count}`;
    node.addEventListener("click", onClick);
    return node;
  }

  function renderStatusFilters() {
    const counts = {
      All: items.length,
      read: items.filter((item) => item.status === "read").length,
      unread: items.filter((item) => item.status !== "read").length,
      source_missing: items.filter((item) => item.source_status === "source_missing").length,
      queue: items.filter((item) => item.status !== "read" || item.source_status === "source_missing").length,
    };
    const labels = {
      All: "全部",
      read: "已有笔记",
      unread: "待读",
      source_missing: "源缺失",
      queue: "队列",
    };
    els.statusFilters.replaceChildren(
      ...Object.keys(labels).map((key) =>
        button(labels[key], counts[key], state.status === key, () => {
          state.status = key;
          render();
        }),
      ),
    );
  }

  function renderCategories() {
    const counts = countBy(items, categoryOf);
    const max = Math.max(...counts.values(), 1);
    const cards = [];

    const all = document.createElement("button");
    all.type = "button";
    all.className = `category-card${state.category === "All" ? " active" : ""}`;
    all.innerHTML = '<span>全部研究方向</span><strong></strong><span class="category-track"><span></span></span>';
    all.querySelector("strong").textContent = String(items.length);
    all.querySelector(".category-track span").style.width = "100%";
    all.addEventListener("click", () => {
      state.category = "All";
      render();
    });
    cards.push(all);

    [...counts.entries()].sort((a, b) => a[0].localeCompare(b[0])).forEach(([category, count]) => {
      const card = document.createElement("button");
      card.type = "button";
      card.className = `category-card${state.category === category ? " active" : ""}`;
      const percent = Math.max(8, Math.round((count / max) * 100));
      const label = document.createElement("span");
      label.textContent = category;
      const strong = document.createElement("strong");
      strong.textContent = String(count);
      const track = document.createElement("span");
      track.className = "category-track";
      const fill = document.createElement("span");
      fill.style.width = `${percent}%`;
      track.append(fill);
      card.append(label, strong, track);
      card.addEventListener("click", () => {
        state.category = state.category === category ? "All" : category;
        render();
      });
      cards.push(card);
    });

    els.categoryGrid.replaceChildren(...cards);
  }

  function addText(parent, selector, value, fallback) {
    const node = parent.querySelector(selector);
    node.textContent = text(value) || fallback || "";
  }

  function action(label, href, primary) {
    const node = document.createElement("a");
    node.className = `action${primary ? " primary" : ""}`;
    node.href = href;
    node.textContent = label;
    return node;
  }

  function renderCard(item) {
    const node = els.template.content.firstElementChild.cloneNode(true);
    addText(node, ".meta", `${readingStatus(item)} · ${text(item.year)} · ${text(item.venue)}`.replace(/\s+·\s+$/g, ""), "unread");
    addText(node, "h3", item.title || item.pdf_rel_path, "Untitled paper");
    addText(node, ".area-line", `${categoryOf(item)} / ${subtopicOf(item)}`, "Unclassified / General");
    addText(node, ".summary", item.summary, "尚未生成笔记。");

    const priority = node.querySelector(".priority");
    priority.textContent = text(item.priority) || "Saved";
    priority.classList.add(priorityClass(item.priority));

    const tagRow = node.querySelector(".tag-row");
    tagRow.replaceChildren(
      ...list(item.tags).slice(0, 6).map((tag) => {
        const chip = document.createElement("span");
        chip.className = "tag-chip";
        chip.textContent = tag;
        return chip;
      }),
    );

    addText(node, ".problem-preview", item.problem_preview, "尚无问题预览。");
    addText(node, ".method-preview", item.method_preview, "尚无方法预览。");
    addText(node, ".findings-preview", item.findings_preview, "尚无结论预览。");
    addText(node, ".value-preview", item.value_preview, "尚无研究价值预览。");
    addText(node, ".next-action", item.next_action, "暂无下一步。");
    addText(node, ".evidence", item.evidence_basis ? `证据来源：${item.evidence_basis}` : "", "");

    const actions = node.querySelector(".actions");
    if (item.note_href) actions.append(action("打开笔记", item.note_href, true));
    if (item.pdf_href) actions.append(action("打开 PDF", item.pdf_href, false));
    const path = document.createElement("span");
    path.className = "path";
    path.textContent = item.pdf_rel_path || "";
    actions.append(path);

    const toggle = node.querySelector(".detail-toggle");
    const panel = node.querySelector(".details-panel");
    toggle.addEventListener("click", () => {
      const expanded = toggle.getAttribute("aria-expanded") === "true";
      toggle.setAttribute("aria-expanded", String(!expanded));
      toggle.querySelector(".toggle-icon").textContent = expanded ? "+" : "-";
      panel.hidden = expanded;
    });

    return node;
  }

  function renderPapers() {
    const visible = filteredItems();
    els.resultCount.textContent = `${visible.length} papers`;
    if (!visible.length) {
      const empty = document.createElement("p");
      empty.className = "empty";
      empty.textContent = "没有匹配的论文。";
      els.papers.replaceChildren(empty);
      return;
    }
    els.papers.replaceChildren(...visible.map(renderCard));
  }

  function renderQueue() {
    const queue = items.filter((item) => item.status !== "read" || item.source_status === "source_missing");
    if (!queue.length) {
      const empty = document.createElement("p");
      empty.className = "empty";
      empty.textContent = "当前没有待读或源缺失论文。";
      els.queueList.replaceChildren(empty);
      return;
    }
    els.queueList.replaceChildren(
      ...queue.slice(0, 12).map((item) => {
        const row = document.createElement("article");
        row.className = "queue-item";
        const title = document.createElement("h3");
        title.textContent = item.title || item.pdf_rel_path || "Untitled paper";
        const meta = document.createElement("p");
        meta.className = "queue-meta";
        meta.textContent = `${item.source_status || "available"} · ${readingStatus(item)} · ${categoryOf(item)}`;
        row.append(title, meta);
        return row;
      }),
    );
  }

  function render() {
    renderStatusFilters();
    renderCategories();
    renderPapers();
    renderQueue();
  }

  els.search.addEventListener("input", () => {
    state.search = els.search.value || "";
    renderPapers();
  });

  render();
})();
