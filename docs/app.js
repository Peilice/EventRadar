"use strict";

const CATEGORIES = ["展覽", "表演／音樂", "講座／課程", "節慶／觀光", "市集", "親子", "運動", "其他"];
// 分類對應的樣式代號（顏色與圖示），沒列到的歸「其他」
const CATEGORY_KEYS = {
  "展覽": "exhibit",
  "表演／音樂": "show",
  "講座／課程": "talk",
  "節慶／觀光": "fest",
  "市集": "market",
  "親子": "kids",
  "運動": "sport",
  "其他": "other",
};
const catKey = (c) => CATEGORY_KEYS[c] || "other";
const WEEKDAYS = ["日", "一", "二", "三", "四", "五", "六"];
const DEFAULT_RANGE_DAYS = 30;
// 個人標記：存在瀏覽器的 localStorage，格式 { 活動 ID: "want" | "going" }
const MARK_KEY = "eventradar.marks";
const MARK_LABELS = { want: "想去", going: "已報名" };
// 月曆：展期超過這個天數的活動不畫在格子上，改列在月曆下方；每週最多畫幾條橫條
const LONG_EVENT_DAYS = 14;
const CAL_LANES = 3;

const state = {
  events: [],
  sourceLabels: {},
  categories: new Set(),
  sources: new Set(),
  sourceChips: new Map(),
  marks: {},
  markFilter: new Set(),
  markChips: new Map(),
  // 最近一次更新的日期；first_seen 等於這天的活動就是這次新增的
  latestDay: "",
  newFilter: new Set(),
  view: "list",
  calMonth: "",
  calDay: "",
  calKinds: new Set(),
  calChips: new Map(),
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

// month 為 YYYY-MM
function shiftMonth(month, n) {
  const [y, m] = month.split("-").map(Number);
  return new Date(Date.UTC(y, m - 1 + n, 1)).toISOString().slice(0, 7);
}

const monthLast = (month) => addDays(`${shiftMonth(month, 1)}-01`, -1);
const daysBetween = (a, b) => (Date.parse(b) - Date.parse(a)) / 86400000;
const weekdayOf = (day) => new Date(`${day}T00:00:00Z`).getUTCDay();

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

const isNew = (e) => e.first_seen === state.latestDay;

// --- 標記 ---

// 無痕模式或封鎖網站資料時 localStorage 會丟例外，此時標記只在這次瀏覽有效
function loadMarks() {
  try {
    const m = JSON.parse(localStorage.getItem(MARK_KEY));
    return m && typeof m === "object" ? m : {};
  } catch {
    return {};
  }
}

function saveMarks() {
  try {
    localStorage.setItem(MARK_KEY, JSON.stringify(state.marks));
  } catch {}
}

// 對照目前的資料：去重後主 ID 若改變，從 aliases 找回標記；已結束或已下架的活動清掉
function syncMarks(events) {
  const saved = loadMarks();
  const today = taipeiToday();
  state.marks = {};
  for (const e of events) {
    if (dayOf(e.end) < today) continue;
    const id = [e.id, ...(e.aliases || [])].find((i) => MARK_LABELS[saved[i]]);
    if (id) state.marks[e.id] = saved[id];
  }
  saveMarks();
}

function toggleMark(e, kind) {
  if (state.marks[e.id] === kind) delete state.marks[e.id];
  else state.marks[e.id] = kind;
  saveMarks();
}

function updateMarkCounts() {
  const counts = {};
  for (const kind of Object.values(state.marks)) counts[kind] = (counts[kind] || 0) + 1;
  for (const chips of [state.markChips, state.calChips]) {
    for (const [kind, chip] of chips) chip.querySelector(".chip-count").textContent = counts[kind] || 0;
  }
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
    marks: state.markFilter,
    newOnly: state.newFilter.size > 0,
  };
}

function matches(e, f) {
  if (dayOf(e.start) > f.to || dayOf(e.end) < f.from) return false;
  if (f.district && e.district !== f.district) return false;
  if (f.fee && e.fee !== f.fee) return false;
  if (f.organizer_type && e.organizer_type !== f.organizer_type) return false;
  if (f.categories.size && !f.categories.has(e.category)) return false;
  if (f.sources.size && !e.sources.some((s) => f.sources.has(s))) return false;
  if (f.marks.size && !f.marks.has(state.marks[e.id])) return false;
  if (f.newOnly && !isNew(e)) return false;
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
  if (!f.marks.size && !f.newOnly && (f.from !== today || f.to !== addDays(today, DEFAULT_RANGE_DAYS))) n++;
  if (f.district) n++;
  if (f.fee) n++;
  if (f.organizer_type) n++;
  if (f.categories.size) n++;
  if (f.sources.size) n++;
  if (f.marks.size) n++;
  if (f.newOnly) n++;
  return n;
}

// --- 繪製 ---

const template = $("#event-template");

function renderEvent(e) {
  const node = template.content.firstElementChild.cloneNode(true);
  const key = catKey(e.category);
  node.dataset.cat = key;
  node.querySelector(".event-cat use").setAttribute("href", `#i-${key}`);
  node.querySelector(".event-cat span").textContent = e.category;

  const markBtns = node.querySelectorAll(".mark-btn");
  const syncMarkBtns = () => {
    for (const b of markBtns) b.setAttribute("aria-pressed", String(state.marks[e.id] === b.dataset.mark));
  };
  for (const b of markBtns) {
    b.setAttribute("aria-label", `${MARK_LABELS[b.dataset.mark]}：${e.title}`);
    b.addEventListener("click", () => {
      toggleMark(e, b.dataset.mark);
      syncMarkBtns();
      // 只看標記或月曆時，取消標記的活動要從畫面移除
      if (state.markFilter.size || state.view === "calendar") render();
      else updateMarkCounts();
    });
  }
  syncMarkBtns();

  const link = node.querySelector(".event-title a");
  link.textContent = e.title;
  const primary = safeUrl(e.links[0] && e.links[0].url);
  if (primary) link.href = primary;
  else link.removeAttribute("target");

  node.querySelector(".event-when span").textContent = whenText(e);

  const where = [e.venue || e.address, e.district].filter(Boolean);
  if (e.venue && e.address && !e.address.includes(e.venue)) where.splice(1, 0, e.address);
  const whereEl = node.querySelector(".event-where");
  if (where.length) whereEl.querySelector("span").textContent = [...new Set(where)].join(" · ");
  else whereEl.remove();

  const tags = node.querySelector(".tags");
  const addTag = (text, cls) => {
    const li = document.createElement("li");
    li.className = `tag ${cls || ""}`;
    li.textContent = text;
    tags.append(li);
  };
  if (isNew(e)) addTag("新增", "tag-new");
  if (e.fee === "免費") addTag("免費", "tag-free");
  else if (e.fee === "付費") addTag("付費");
  if (e.organizer_type === "政府") addTag("政府", "tag-gov");
  else if (e.organizer_type === "民間") addTag("民間", "tag-private");
  if (!tags.childElementCount) tags.remove();

  const org = node.querySelector(".event-org");
  if (e.organizer) org.querySelector("span").textContent = `主辦：${e.organizer}`;
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
  const cal = state.view === "calendar";
  $(".layout").classList.toggle("is-calendar", cal);
  $(".sidebar").hidden = $("#upcoming").hidden = cal;
  $("#cal-view").hidden = !cal;
  const toggle = $("#view-toggle");
  toggle.title = cal ? "回到首頁" : "月曆";
  toggle.setAttribute("aria-label", toggle.title);
  if (cal) {
    $("#ongoing-wrap").hidden = true;
    renderCalendar();
  } else {
    renderList();
  }
}

function renderList() {
  // 只看標記或新增時不限日期：停用的欄位不會出現在 FormData，readFilters 會改用預設值
  form.elements.from.disabled = form.elements.to.disabled = state.markFilter.size > 0 || state.newFilter.size > 0;
  const f = readFilters();
  const filtered = state.events.filter((e) => matches(e, f));
  const upcoming = filtered.filter((e) => dayOf(e.start) >= f.from);
  const ongoing = filtered
    .filter((e) => dayOf(e.start) < f.from)
    .sort((a, b) => a.end.localeCompare(b.end));

  updateSourceCounts(f);
  updateMarkCounts();

  const active = countActiveFilters(f);
  $("#active-count").textContent = active ? `（${active} 項）` : "";
  $("#summary").textContent = `即將開始 ${upcoming.length} 筆 · 進行中 ${ongoing.length} 筆`;

  const upcomingEl = $("#upcoming");
  upcomingEl.replaceChildren();
  if (!upcoming.length) upcomingEl.append(renderEmpty(active));

  const perDay = {};
  for (const e of upcoming) perDay[dayOf(e.start)] = (perDay[dayOf(e.start)] || 0) + 1;
  let currentDay = null;
  const frag = document.createDocumentFragment();
  for (const e of upcoming) {
    const day = dayOf(e.start);
    if (day !== currentDay) {
      currentDay = day;
      frag.append(renderDayHeading(day, perDay[day]));
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

// 日期標頭：大字日期 + 月份星期，今天、明天另外標示
function renderDayHeading(day, count) {
  const [y, m, d] = day.split("-").map(Number);
  const today = taipeiToday();
  const wd = WEEKDAYS[new Date(Date.UTC(y, m - 1, d)).getUTCDay()];
  const yearPart = y !== Number(today.slice(0, 4)) ? `${y} 年 ` : "";
  const rel = day === today ? "今天" : day === addDays(today, 1) ? "明天" : "";

  const h = document.createElement("h2");
  h.className = "day-heading";
  if (wd === "六" || wd === "日") h.classList.add("is-weekend");
  h.setAttribute("aria-label", `${fmtDay(day)}${rel ? "，" + rel : ""}，${count} 場`);
  const ticket = document.createElement("span");
  ticket.className = "day-ticket";
  ticket.setAttribute("aria-hidden", "true");
  ticket.innerHTML = `<span class="day-num"></span><span class="day-meta"><span class="day-month"></span><span class="day-wd"></span></span>`;
  ticket.querySelector(".day-num").textContent = d;
  ticket.querySelector(".day-month").textContent = `${yearPart}${m} 月`;
  ticket.querySelector(".day-wd").textContent = `週${wd}`;
  h.append(ticket);
  if (rel) {
    const r = document.createElement("span");
    r.className = "day-rel";
    r.setAttribute("aria-hidden", "true");
    r.textContent = rel;
    h.append(r);
  }
  const c = document.createElement("span");
  c.className = "day-count";
  c.setAttribute("aria-hidden", "true");
  c.textContent = `${count} 場`;
  h.append(c);
  return h;
}

function renderEmpty(activeFilters) {
  const box = document.createElement("div");
  box.className = "empty";
  box.innerHTML = `<svg class="empty-icon" viewBox="0 0 24 24" aria-hidden="true"><use href="#i-radar"/></svg><p></p>`;
  box.querySelector("p").textContent =
    state.markFilter.size && !Object.keys(state.marks).length
      ? "還沒有標記任何活動。點活動卡片上的「想去」或「已報名」就會出現在這裡。"
      : state.newFilter.size
        ? "這次更新沒有符合條件的新增活動。"
        : "這段期間沒有符合條件的新活動。";
  if (activeFilters) {
    const b = document.createElement("button");
    b.type = "button";
    b.className = "reset";
    b.textContent = "清除篩選";
    b.addEventListener("click", () => {
      resetFilters();
      render();
    });
    box.append(b);
  }
  return box;
}

// --- 月曆 ---

const isLong = (e) => daysBetween(dayOf(e.start), dayOf(e.end)) + 1 > LONG_EVENT_DAYS;
const overlaps = (e, from, to) => dayOf(e.start) <= to && dayOf(e.end) >= from;
// 已報名排在想去前面，再依開始時間
const markRank = (e) => (state.marks[e.id] === "going" ? 0 : 1);
const byMark = (a, b) => markRank(a) - markRank(b) || a.start.localeCompare(b.start);

function markedEvents() {
  return state.events.filter((e) => {
    const kind = state.marks[e.id];
    return kind && (!state.calKinds.size || state.calKinds.has(kind));
  });
}

function goMonth(month) {
  const today = taipeiToday();
  const first = `${month}-01`;
  if (month === today.slice(0, 7)) {
    state.calDay = today;
  } else {
    // 換到別的月份時，先選該月第一個有標記活動的日子
    const last = monthLast(month);
    const starts = markedEvents()
      .filter((e) => overlaps(e, first, last))
      .map((e) => (dayOf(e.start) < first ? first : dayOf(e.start)))
      .sort();
    state.calDay = starts[0] || first;
  }
  state.calMonth = month;
  render();
}

function renderCalendar() {
  updateMarkCounts();
  const today = taipeiToday();
  const month = state.calMonth;
  const first = `${month}-01`;
  const last = monthLast(month);
  const events = markedEvents().filter((e) => overlaps(e, first, last));
  const total = Object.keys(state.marks).length;

  const [y, m] = month.split("-").map(Number);
  $("#cal-title").textContent = `${y} 年 ${m} 月`;
  // 標記會在活動結束後清掉，往前翻沒有東西可看
  $("#cal-prev").disabled = month <= today.slice(0, 7);
  $("#cal-today").disabled = month === today.slice(0, 7);
  $("#summary").textContent = `已標記 ${total} 筆活動`;
  $("#cal-empty").hidden = total > 0;

  const head = document.createElement("div");
  head.className = "cal-weekdays";
  head.setAttribute("aria-hidden", "true");
  WEEKDAYS.forEach((wd, i) => {
    const s = document.createElement("span");
    if (i === 0 || i === 6) s.className = "is-weekend";
    s.textContent = wd;
    head.append(s);
  });
  const grid = $("#cal-grid");
  grid.replaceChildren(head);
  const short = events.filter((e) => !isLong(e));
  for (let start = addDays(first, -weekdayOf(first)); start <= last; start = addDays(start, 7)) {
    grid.append(renderWeek(start, short, events, month, today));
  }

  const agenda = $("#cal-agenda");
  const list = events.filter((e) => overlaps(e, state.calDay, state.calDay)).sort(byMark);
  agenda.replaceChildren(renderDayHeading(state.calDay, list.length), ...list.map(renderEvent));
  if (!list.length) {
    const p = document.createElement("p");
    p.className = "hint cal-none";
    p.textContent = "這天沒有標記的活動。";
    agenda.append(p);
  }

  const long = events.filter(isLong).sort((a, b) => a.end.localeCompare(b.end));
  $("#cal-long").hidden = !long.length;
  $("#cal-long-title").textContent = `本月可去的長期活動（${long.length}）`;
  $("#cal-long-list").replaceChildren(...long.map(renderEvent));
}

// 一週一列：底層是七個日期按鈕，上面疊跨日橫條（只是裝飾，點擊會穿透到日期）
function renderWeek(start, short, all, month, today) {
  const end = addDays(start, 6);
  const week = document.createElement("div");
  week.className = "cal-week";

  const segs = short
    .filter((e) => overlaps(e, start, end))
    .map((e) => {
      const s = dayOf(e.start) < start ? start : dayOf(e.start);
      const t = dayOf(e.end) > end ? end : dayOf(e.end);
      return { e, s, t, from: daysBetween(start, s), span: daysBetween(s, t) + 1 };
    })
    // 已報名先排，才不會被想去的多日活動擠到「+N」裡
    .sort((a, b) => markRank(a.e) - markRank(b.e) || a.from - b.from || b.span - a.span || a.e.start.localeCompare(b.e.start));

  // 依序放進第一條整段都空著的 lane，放不下的算進當天的「+N」
  const lanes = [];
  const hidden = Array(7).fill(0);
  const bars = [];
  for (const seg of segs) {
    const cols = [...Array(seg.span).keys()].map((i) => seg.from + i);
    let lane = lanes.findIndex((used) => cols.every((c) => !used[c]));
    if (lane < 0 && lanes.length < CAL_LANES) lane = lanes.push(Array(7).fill(false)) - 1;
    if (lane < 0) {
      for (const c of cols) hidden[c]++;
      continue;
    }
    for (const c of cols) lanes[lane][c] = true;
    bars.push(renderBar(seg, lane));
  }

  for (let i = 0; i < 7; i++) {
    const day = addDays(start, i);
    const cell = document.createElement("button");
    cell.type = "button";
    cell.className = "cal-day";
    cell.style.gridColumn = i + 1;
    if (day.slice(0, 7) !== month) cell.classList.add("is-outside");
    if (day < today) cell.classList.add("is-past");
    if (day === today) cell.classList.add("is-today");
    cell.setAttribute("aria-pressed", String(day === state.calDay));

    const onDay = all.filter((e) => overlaps(e, day, day));
    const going = onDay.filter((e) => state.marks[e.id] === "going").length;
    const want = onDay.length - going;
    const parts = [going && `已報名 ${going} 筆`, want && `想去 ${want} 筆`].filter(Boolean);
    cell.setAttribute("aria-label", `${fmtDay(day)}${day === today ? "，今天" : ""}，${parts.join("、") || "沒有標記"}`);

    cell.innerHTML = `<span class="cal-num" aria-hidden="true"></span>`;
    cell.firstChild.textContent = Number(day.slice(8));
    if (hidden[i]) cell.insertAdjacentHTML("beforeend", `<span class="cal-more" aria-hidden="true">+${hidden[i]}</span>`);

    cell.addEventListener("click", () => {
      state.calMonth = day.slice(0, 7);
      state.calDay = day;
      render();
      // 窄螢幕的當日清單在月曆下方，捲過去才看得到
      if (!window.matchMedia("(min-width: 1000px)").matches) $("#cal-agenda").scrollIntoView({ block: "start" });
    });
    week.append(cell);
  }
  week.append(...bars);
  return week;
}

function renderBar({ e, s, t, from, span }, lane) {
  const kind = state.marks[e.id];
  const bar = document.createElement("div");
  bar.className = "cal-bar";
  bar.dataset.mark = kind;
  bar.setAttribute("aria-hidden", "true");
  bar.style.gridColumn = `${from + 1} / span ${span}`;
  bar.style.gridRow = lane + 2;
  // 跨週的活動在接續的那一側不畫圓角
  if (s > dayOf(e.start)) bar.classList.add("cont-left");
  if (t < dayOf(e.end)) bar.classList.add("cont-right");
  bar.innerHTML = `<svg class="icon"><use href="#i-${kind}"/></svg><span></span>`;
  const time = timeOf(e.start);
  const showTime = s === dayOf(e.start) && time !== "00:00";
  bar.querySelector("span").textContent = `${showTime ? time + " " : ""}${e.title}`;
  return bar;
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

// 想去／已報名 chip：附圖示與筆數，chips 用來讓 updateMarkCounts 找到它們
function makeMarkChips(container, selected, chips) {
  for (const [kind, label] of Object.entries(MARK_LABELS)) {
    const b = makeChip(selected, kind, label);
    b.classList.add("chip-mark");
    b.dataset.mark = kind;
    b.insertAdjacentHTML("afterbegin", `<svg class="icon" aria-hidden="true"><use href="#i-${kind}"/></svg>`);
    const count = document.createElement("span");
    count.className = "chip-count";
    b.append(" ", count);
    chips.set(kind, b);
    container.append(b);
  }
}

// 最近一次更新是今天就叫「今天新增」，否則標出日期，避免更新中斷時誤以為是今天
function newLabel() {
  const [, m, d] = state.latestDay.split("-").map(Number);
  return state.latestDay === taipeiToday() ? "今天新增" : `${m}/${d} 新增`;
}

function setupFilters() {
  makeMarkChips($("#mark-chips"), state.markFilter, state.markChips);

  const newChip = makeChip(state.newFilter, "new", newLabel());
  newChip.classList.add("chip-new");
  const newCount = document.createElement("span");
  newCount.className = "chip-count";
  newCount.textContent = state.events.filter((e) => isNew(e) && dayOf(e.end) >= taipeiToday()).length;
  newChip.append(" ", newCount);
  $("#new-chips").append(newChip);

  const chips = $("#category-chips");
  for (const c of CATEGORIES) {
    const b = makeChip(state.categories, c, c);
    b.classList.add("chip-cat");
    b.dataset.cat = catKey(c);
    b.insertAdjacentHTML("afterbegin", `<svg class="icon" aria-hidden="true"><use href="#i-${catKey(c)}"/></svg>`);
    chips.append(b);
  }

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
  state.markFilter.clear();
  state.newFilter.clear();
  form.querySelectorAll(".chip").forEach((b) => b.setAttribute("aria-pressed", "false"));
}

const viewFromHash = () => (location.hash === "#calendar" ? "calendar" : "list");

function setupCalendar() {
  const today = taipeiToday();
  state.calMonth = today.slice(0, 7);
  state.calDay = today;
  state.view = viewFromHash();
  makeMarkChips($("#cal-legend"), state.calKinds, state.calChips);
  $("#cal-prev").addEventListener("click", () => goMonth(shiftMonth(state.calMonth, -1)));
  $("#cal-next").addEventListener("click", () => goMonth(shiftMonth(state.calMonth, 1)));
  $("#cal-today").addEventListener("click", () => goMonth(taipeiToday().slice(0, 7)));
  // 視圖記在網址，重新整理或按上一頁都會回到同一個視圖
  $("#view-toggle").addEventListener("click", () => {
    location.hash = state.view === "calendar" ? "" : "calendar";
  });
  window.addEventListener("hashchange", () => {
    state.view = viewFromHash();
    render();
  });
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
    state.latestDay = dayOf(data.generated_at);
    syncMarks(data.events);
    renderStatus(status);
    const newCount = data.events.filter(isNew).length;
    $("#meta").textContent = `更新於 ${fmtDateTime(data.generated_at)} · 共 ${data.events.length} 筆活動${newCount ? ` · 新增 ${newCount} 筆` : ""}`;
    setupFilters();
    setupCalendar();
    render();
  } catch (err) {
    $("#meta").textContent = `資料載入失敗：${err.message}`;
  }
}

main();
