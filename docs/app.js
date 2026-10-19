"use strict";

const CATEGORIES = ["展覽", "表演／音樂", "講座／課程", "節慶／觀光", "市集", "親子", "運動", "其他"];
const WEEKDAYS = ["日", "一", "二", "三", "四", "五", "六"];
const DEFAULT_RANGE_DAYS = 30;

const state = {
  events: [],
  sourceLabels: {},
  categories: new Set(),
  sources: new Set(),
  sourceChips: new Map(),
};

const $ = (sel) => document.querySelector(sel);
const form = $("#filter-form");

// 以台灣時區取得 YYYY-MM-DD
function taipeiToday() {
  return new Intl.DateTimeFormat("en-CA", { timeZone: "Asia/Taipei" }).format(new Date());
}

function addDays(day, n) {
  const [y, m, d] = day.split("-").map(Number);
  const dt = new Date(Date.UTC(y, m - 1, d + n));
  return dt.toISOString().slice(0, 10);
}

function fmtDay(day) {
  const [y, m, d] = day.split("-").map(Number);
  const wd = WEEKDAYS[new Date(Date.UTC(y, m - 1, d)).getUTCDay()];
  const thisYear = Number(taipeiToday().slice(0, 4));
  return `${y !== thisYear ? y + "/" : ""}${m}/${d}（${wd}）`;
}

// 事件時間以 +08:00 的 ISO 字串儲存，直接切字串即為台灣當地日期與時間
const dayOf = (iso) => iso.slice(0, 10);
const timeOf = (iso) => iso.slice(11, 16);

function whenText(e) {
  const sd = dayOf(e.start), ed = dayOf(e.end);
  const st = timeOf(e.start), et = timeOf(e.end);
  const allDay = st === "00:00" && (et === "23:59" || et === "00:00");
  if (sd === ed) {
    if (allDay) return fmtDay(sd);
    return `${fmtDay(sd)} ${st}${et !== st ? "–" + et : ""}`;
  }
  return allDay ? `${fmtDay(sd)} – ${fmtDay(ed)}` : `${fmtDay(sd)} ${st} – ${fmtDay(ed)} ${et}`;
}

function safeUrl(url) {
  return /^https?:\/\//i.test(url || "") ? url : null;
}

// --- 篩選 ---

function readFilters() {
  const f = new FormData(form);
  return {
    q: (f.get("q") || "").trim().toLowerCase(),
    from: f.get("from") || taipeiToday(),
    to: f.get("to") || "9999-12-31",
    district: f.get("district"),
    fee: f.get("fee"),
    organizer_type: f.get("organizer_type"),
    categories: state.categories,
    sources: state.sources,
  };
}

function matches(e, f) {
  if (dayOf(e.start) > f.to || dayOf(e.end) < f.from) return false;
  if (f.district && e.district !== f.district) return false;
  if (f.fee && e.fee !== f.fee) return false;
  if (f.organizer_type && e.organizer_type !== f.organizer_type) return false;
  if (f.categories.size && !f.categories.has(e.category)) return false;
  if (f.sources.size && !e.sources.some((s) => f.sources.has(s))) return false;
  if (f.q) {
    const hay = [e.title, e.venue, e.address, e.organizer, e.description].join(" ").toLowerCase();
    if (!f.q.split(/\s+/).every((w) => hay.includes(w))) return false;
  }
  return true;
}

function countActiveFilters(f) {
  const today = taipeiToday();
  let n = 0;
  if (f.q) n++;
  if (f.from !== today || f.to !== addDays(today, DEFAULT_RANGE_DAYS)) n++;
  if (f.district) n++;
  if (f.fee) n++;
  if (f.organizer_type) n++;
  if (f.categories.size) n++;
  if (f.sources.size) n++;
  return n;
}

// --- 繪製 ---

const template = $("#event-template");

function renderEvent(e) {
  const node = template.content.firstElementChild.cloneNode(true);
  const link = node.querySelector(".event-title a");
  link.textContent = e.title;
  const primary = safeUrl(e.links[0] && e.links[0].url);
  if (primary) link.href = primary;
  else link.removeAttribute("target");

  node.querySelector(".event-when").textContent = whenText(e);

  const where = [e.venue || e.address, e.district].filter(Boolean);
  if (e.venue && e.address && !e.address.includes(e.venue)) where.splice(1, 0, e.address);
  node.querySelector(".event-where").textContent = [...new Set(where)].join(" · ");

  const tags = node.querySelector(".tags");
  const addTag = (text, cls) => {
    const li = document.createElement("li");
    li.className = `tag ${cls || ""}`;
    li.textContent = text;
    tags.append(li);
  };
  addTag(e.category, "tag-cat");
  if (e.fee === "免費") addTag("免費", "tag-free");
  else if (e.fee === "付費") addTag("付費");
  if (e.organizer_type === "政府") addTag("政府", "tag-gov");
  else if (e.organizer_type === "民間") addTag("民間", "tag-private");

  const org = node.querySelector(".event-org");
  if (e.organizer) org.textContent = `主辦：${e.organizer}`;
  else org.remove();

  if (e.description) {
    const desc = node.querySelector(".event-desc");
    desc.hidden = false;
    desc.querySelector("p").textContent = e.description;
  }

  const links = node.querySelector(".event-links");
  links.append("來源：");
  for (const l of e.links) {
    const url = safeUrl(l.url);
    if (!url) continue;
    const a = document.createElement("a");
    a.href = url;
    a.target = "_blank";
    a.rel = "noopener noreferrer";
    a.textContent = state.sourceLabels[l.source] || l.source;
    links.append(a);
  }
  return node;
}

function render() {
  const f = readFilters();
  const filtered = state.events.filter((e) => matches(e, f));
  const upcoming = filtered.filter((e) => dayOf(e.start) >= f.from);
  const ongoing = filtered
    .filter((e) => dayOf(e.start) < f.from)
    .sort((a, b) => a.end.localeCompare(b.end));

  updateSourceCounts(f);

  const active = countActiveFilters(f);
  $("#active-count").textContent = active ? `（${active} 項）` : "";
  $("#summary").textContent = `即將開始 ${upcoming.length} 筆 · 進行中 ${ongoing.length} 筆`;

  const upcomingEl = $("#upcoming");
  upcomingEl.replaceChildren();
  if (!upcoming.length) {
    const p = document.createElement("p");
    p.className = "empty";
    p.textContent = "這段期間沒有符合條件的新活動。";
    upcomingEl.append(p);
  }
  let currentDay = null;
  const frag = document.createDocumentFragment();
  for (const e of upcoming) {
    const day = dayOf(e.start);
    if (day !== currentDay) {
      currentDay = day;
      const h = document.createElement("h2");
      h.className = "day-heading";
      h.textContent = fmtDay(day);
      frag.append(h);
    }
    frag.append(renderEvent(e));
  }
  upcomingEl.append(frag);

  const wrap = $("#ongoing-wrap");
  wrap.hidden = !ongoing.length;
  $("#ongoing-summary").textContent = `進行中的活動（${ongoing.length}）`;
  const ongoingEl = $("#ongoing");
  ongoingEl.replaceChildren(...ongoing.map(renderEvent));
}

// 來源 chip 上的筆數：套用其他篩選條件後，各來源各有幾筆
function updateSourceCounts(f) {
  const others = { ...f, sources: new Set() };
  const counts = {};
  for (const e of state.events) {
    if (!matches(e, others)) continue;
    for (const s of e.sources) counts[s] = (counts[s] || 0) + 1;
  }
  for (const [name, chip] of state.sourceChips) {
    chip.querySelector(".chip-count").textContent = counts[name] || 0;
  }
}

function renderStatus(status) {
  const body = $("#status-body");
  body.replaceChildren();
  for (const [name, s] of Object.entries(status.sources || {})) {
    state.sourceLabels[name] = s.label || name;
    const tr = document.createElement("tr");
    const bad = !s.ok || !s.count;
    if (bad) tr.className = "bad";

    const tdName = document.createElement("td");
    tdName.textContent = s.label || name;
    if (s.error) {
      const err = document.createElement("span");
      err.className = "err";
      err.textContent = `本次失敗：${s.error}`;
      tdName.append(err);
    } else if (!s.count) {
      const err = document.createElement("span");
      err.className = "err";
      err.textContent = "本次抓到 0 筆，可能網站改版";
      tdName.append(err);
    }
    const tdTime = document.createElement("td");
    tdTime.textContent = s.last_success ? fmtDateTime(s.last_success) : "從未成功";
    const tdCount = document.createElement("td");
    tdCount.textContent = s.ok ? s.count : `${s.cached_count ?? 0}（舊資料）`;
    tr.append(tdName, tdTime, tdCount);
    body.append(tr);
  }
}

function fmtDateTime(iso) {
  return `${fmtDay(dayOf(iso))} ${timeOf(iso)}`;
}

// --- 初始化 ---

function makeChip(selected, value, label) {
  const b = document.createElement("button");
  b.type = "button";
  b.className = "chip";
  b.textContent = label;
  b.setAttribute("aria-pressed", "false");
  b.addEventListener("click", () => {
    if (selected.has(value)) selected.delete(value);
    else selected.add(value);
    b.setAttribute("aria-pressed", String(selected.has(value)));
    render();
  });
  return b;
}

function setupFilters() {
  const chips = $("#category-chips");
  for (const c of CATEGORIES) chips.append(makeChip(state.categories, c, c));

  // 來源依 status.json 的順序排列，再補上 status 裡沒有的來源
  const sourceNames = [...new Set([...Object.keys(state.sourceLabels), ...state.events.flatMap((e) => e.sources)])];
  const sourceChips = $("#source-chips");
  for (const name of sourceNames) {
    const b = makeChip(state.sources, name, state.sourceLabels[name] || name);
    const count = document.createElement("span");
    count.className = "chip-count";
    b.append(" ", count);
    state.sourceChips.set(name, b);
    sourceChips.append(b);
  }

  const districts = [...new Set(state.events.map((e) => e.district).filter(Boolean))].sort((a, b) =>
    a.localeCompare(b, "zh-Hant-TW")
  );
  const sel = form.elements.district;
  for (const d of districts) sel.append(new Option(d, d));

  resetFilters();
  form.addEventListener("input", render);
  $("#reset-filters").addEventListener("click", () => {
    resetFilters();
    render();
  });

  // 手機上預設收合篩選區
  if (window.matchMedia("(max-width: 640px)").matches) $("#filters").open = false;
}

function resetFilters() {
  form.reset();
  const today = taipeiToday();
  form.elements.from.value = today;
  form.elements.to.value = addDays(today, DEFAULT_RANGE_DAYS);
  state.categories.clear();
  state.sources.clear();
  document.querySelectorAll(".chip").forEach((b) => b.setAttribute("aria-pressed", "false"));
}

async function main() {
  try {
    const [eventsRes, statusRes] = await Promise.all([
      fetch("data/events.json", { cache: "no-cache" }),
      fetch("data/status.json", { cache: "no-cache" }),
    ]);
    if (!eventsRes.ok) throw new Error(`events.json ${eventsRes.status}`);
    const data = await eventsRes.json();
    const status = statusRes.ok ? await statusRes.json() : { sources: {} };
    state.events = data.events;
    renderStatus(status);
    $("#meta").textContent = `更新於 ${fmtDateTime(data.generated_at)} · 共 ${data.events.length} 筆活動`;
    setupFilters();
    render();
  } catch (err) {
    $("#meta").textContent = `資料載入失敗：${err.message}`;
  }
}

main();
