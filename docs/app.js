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
// 列表與篩選空間有限，用短的分類名
const SHORT_CATEGORY = { "表演／音樂": "表演", "講座／課程": "講座", "節慶／觀光": "節慶" };
const catShort = (c) => SHORT_CATEGORY[c] || c;
const WEEKDAYS = ["日", "一", "二", "三", "四", "五", "六"];
// 個人標記：存在瀏覽器的 localStorage，格式 { 活動 ID: "want" | "going" }
const MARK_KEY = "eventradar.marks";
const MARK_LABELS = { want: "想去", going: "已報名" };
// 展期超過這個天數的活動歸到「長期展覽」，月曆上也不畫在格子裡；月曆每週最多畫幾條橫條
const LONG_EVENT_DAYS = 14;
const CAL_LANES = 3;
// 每天先列幾筆，其餘收進「還有 N 場」；只多幾筆時直接全列
const DAY_LIMIT = 12;
const DAY_LIMIT_SLACK = 3;
// 手機一次看一天，日期條從今天起列幾天
const MOBILE_DAYS = 60;
const mobileQuery = window.matchMedia("(max-width: 640px)");
const isMobile = () => mobileQuery.matches;
const RANGES = [
  ["today", "今天"],
  ["tomorrow", "明天"],
  ["weekend", "本週末"],
  ["nextweekend", "下週末"],
  ["week", "7 天內"],
  ["month", "30 天內"],
];
const DEFAULT_RANGE = "weekend";

const state = {
  events: [],
  sourceLabels: {},
  // 最近一次更新的日期；first_seen 等於這天的活動就是這次新增的
  latestDay: "",
  today: "",
  view: "list",
  range: DEFAULT_RANGE,
  // 自訂日期 [from, to]，range 為 "custom" 時使用
  custom: null,
  tab: "day",
  group: "day",
  // 手機選取的日期
  day: "",
  q: "",
  categories: new Set(),
  fees: new Set(),
  sources: new Set(),
  district: "",
  newOnly: false,
  markFilter: new Set(),
  marks: {},
  expanded: new Set(),
  // 同名同場地的所有場次（不受篩選影響），詳情裡列出全部場次用
  series: new Map(),
  calMonth: "",
  calDay: "",
  calKinds: new Set(),
  calChips: new Map(),
};
let model = null;

const $ = (sel) => document.querySelector(sel);

function el(tag, cls, text) {
  const n = document.createElement(tag);
  if (cls) n.className = cls;
  if (text != null) n.textContent = text;
  return n;
}

function icon(id, cls = "icon") {
  const ns = "http://www.w3.org/2000/svg";
  const svg = document.createElementNS(ns, "svg");
  svg.setAttribute("class", cls);
  svg.setAttribute("aria-hidden", "true");
  const use = document.createElementNS(ns, "use");
  use.setAttribute("href", `#${id}`);
  svg.append(use);
  return svg;
}

// --- 日期 ---

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
const daysBetween = (a, b) => Math.round((Date.parse(b) - Date.parse(a)) / 86400000);
const weekdayOf = (day) => new Date(`${day}T00:00:00Z`).getUTCDay();
const isWeekend = (day) => [0, 6].includes(weekdayOf(day));

function fmtDay(day) {
  const [y, m, d] = day.split("-").map(Number);
  const thisYear = Number(state.today.slice(0, 4));
  return `${y !== thisYear ? y + "/" : ""}${m}/${d}（${WEEKDAYS[weekdayOf(day)]}）`;
}

const md = (day) => `${Number(day.slice(5, 7))}/${Number(day.slice(8, 10))}`;

// 事件時間以 +08:00 的 ISO 字串儲存，直接切字串即為台灣當地日期與時間
const dayOf = (iso) => iso.slice(0, 10);
const timeOf = (iso) => iso.slice(11, 16);
const isAllDay = (e) => timeOf(e.start) === "00:00" && ["23:59", "00:00"].includes(timeOf(e.end));
const isMultiDay = (e) => dayOf(e.start) !== dayOf(e.end);
const isLong = (e) => daysBetween(dayOf(e.start), dayOf(e.end)) + 1 > LONG_EVENT_DAYS;
const overlaps = (e, from, to) => dayOf(e.start) <= to && dayOf(e.end) >= from;
const seriesKey = (e) => `${e.title.trim()}|${e.venue}`;

function whenText(e) {
  const sd = dayOf(e.start), ed = dayOf(e.end);
  const st = timeOf(e.start), et = timeOf(e.end);
  if (sd === ed) {
    if (isAllDay(e)) return fmtDay(sd);
    return `${fmtDay(sd)} ${st}${et !== st ? "–" + et : ""}`;
  }
  return isAllDay(e) ? `${fmtDay(sd)} – ${fmtDay(ed)}` : `${fmtDay(sd)} ${st} – ${fmtDay(ed)} ${et}`;
}

function safeUrl(url) {
  return /^https?:\/\//i.test(url || "") ? url : null;
}

const isNew = (e) => e.first_seen === state.latestDay;

function rangeOf(key) {
  const t = state.today;
  const w = weekdayOf(t);
  // 這個週末的週六（今天是週日就是昨天）
  const sat = w === 0 ? addDays(t, -1) : addDays(t, 6 - w);
  switch (key) {
    case "today": return [t, t];
    case "tomorrow": return [addDays(t, 1), addDays(t, 1)];
    case "weekend": return [sat < t ? t : sat, addDays(sat, 1)];
    case "nextweekend": return [addDays(sat, 7), addDays(sat, 8)];
    case "week": return [t, addDays(t, 6)];
    case "custom": return state.custom;
    default: return [t, addDays(t, 29)];
  }
}

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
function syncMarks(events, saved = loadMarks()) {
  state.marks = {};
  for (const e of events) {
    if (dayOf(e.end) < state.today) continue;
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

// --- 跨裝置同步：把標記編進網址的 #sync=，在另一台裝置打開就合併進去 ---

const SYNC_PREFIX = "#sync=";

// 標記物件 → JSON → base64url，網址裡不會出現需要跳脫的字元
function encodeMarks(marks) {
  const bytes = new TextEncoder().encode(JSON.stringify(marks));
  return btoa(String.fromCharCode(...bytes)).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}

function decodeMarks(code) {
  try {
    const bin = atob(code.replace(/-/g, "+").replace(/_/g, "/"));
    const m = JSON.parse(new TextDecoder().decode(Uint8Array.from(bin, (c) => c.charCodeAt(0))));
    return m && typeof m === "object" ? m : null;
  } catch {
    return null;
  }
}

const syncLink = () => `${location.origin}${location.pathname}${SYNC_PREFIX}${encodeMarks(state.marks)}`;

// 網址帶 #sync= 時合併進已存的標記（同一活動以連結裡的為準），並把 #sync= 從網址拿掉，
// 免得重新整理又匯入一次。回傳合併後的標記與匯入筆數；網址沒帶或格式不對回傳 null
function importSyncHash() {
  if (!location.hash.startsWith(SYNC_PREFIX)) return null;
  const incoming = decodeMarks(location.hash.slice(SYNC_PREFIX.length));
  history.replaceState(null, "", location.pathname + location.search);
  if (!incoming) return { marks: loadMarks(), count: -1 };
  const marks = loadMarks();
  let count = 0;
  for (const [id, kind] of Object.entries(incoming)) {
    if (!MARK_LABELS[kind]) continue;
    marks[id] = kind;
    count++;
  }
  return { marks, count };
}

function syncMessage(imported) {
  if (imported.count < 0) return "同步連結格式不對，沒有匯入標記";
  return `已從同步連結匯入 ${imported.count} 筆標記`;
}

async function shareSyncLink() {
  const msg = $("#sync-msg");
  const out = $("#sync-link");
  out.hidden = true;
  if (!Object.keys(state.marks).length) {
    msg.textContent = "還沒有標記任何活動。";
    return;
  }
  const url = syncLink();
  // 手機用系統分享（可直接傳到 LINE 給自己），桌機複製到剪貼簿
  if (navigator.share && window.matchMedia("(pointer: coarse)").matches) {
    try {
      await navigator.share({ title: "高雄活動雷達：我的標記", url });
      msg.textContent = "在另一台裝置打開這個連結，就會匯入標記。";
      return;
    } catch (err) {
      if (err.name === "AbortError") return;
    }
  }
  try {
    await navigator.clipboard.writeText(url);
    msg.textContent = "已複製連結。在另一台裝置打開，就會匯入標記。";
  } catch {
    // 剪貼簿被擋時改顯示連結讓使用者自己複製
    out.value = url;
    out.hidden = false;
    out.select();
    msg.textContent = "無法自動複製，請手動複製下方連結。";
  }
}

const markCount = (kind) => Object.values(state.marks).filter((k) => k === kind).length;

function updateMarkCounts() {
  for (const [kind, chip] of state.calChips) chip.querySelector(".chip-count").textContent = markCount(kind);
}

// --- 篩選 ---

function matches(e) {
  if (state.categories.size && !state.categories.has(e.category)) return false;
  if (state.fees.size && !state.fees.has(e.fee)) return false;
  if (state.district && e.district !== state.district) return false;
  if (state.sources.size && !e.sources.some((s) => state.sources.has(s))) return false;
  if (state.markFilter.size && !state.markFilter.has(state.marks[e.id])) return false;
  if (state.newOnly && !isNew(e)) return false;
  if (state.q) {
    const hay = [e.title, e.venue, e.address, e.organizer, e.description].join(" ").toLowerCase();
    if (!state.q.split(/\s+/).every((w) => hay.includes(w))) return false;
  }
  return true;
}

// 只看標記或新增時不限日期
const ignoresRange = () => state.newOnly || state.markFilter.size > 0;

// 有時間的場次在前，接著全天，多日活動（多半是延續中的）排最後
const sortTime = (e) => (isMultiDay(e) ? "~2" : isAllDay(e) ? "~1" : timeOf(e.start));
// 不用 localeCompare：它會把「~」排到數字前面
const cmp = (a, b) => (a < b ? -1 : a > b ? 1 : 0);

function compute() {
  let [from, to] = isMobile() ? [state.day, state.day] : rangeOf(state.range);
  const filtered = state.events.filter(matches);
  if (ignoresRange()) {
    from = state.today;
    to = filtered.reduce((m, e) => (dayOf(e.end) > m ? dayOf(e.end) : m), state.today);
  }
  const inRange = filtered.filter((e) => overlaps(e, from, to));
  const long = inRange.filter(isLong).sort((a, b) => cmp(a.end, b.end));

  // 同一天、同名同場地的多個時段併成一列；多日活動放在範圍內的第一天
  const rows = new Map();
  const seriesDays = new Map();
  for (const e of inRange) {
    if (isLong(e)) continue;
    const day = dayOf(e.start) < from ? from : dayOf(e.start);
    const k = `${day}|${seriesKey(e)}`;
    if (!rows.has(k)) rows.set(k, { day, events: [] });
    rows.get(k).events.push(e);
    if (!seriesDays.has(seriesKey(e))) seriesDays.set(seriesKey(e), new Set());
    seriesDays.get(seriesKey(e)).add(day);
  }
  const dayRows = [...rows.values()];
  for (const r of dayRows) {
    r.events.sort((a, b) => cmp(a.start, b.start));
    r.otherDays = seriesDays.get(seriesKey(r.events[0])).size - 1;
  }
  dayRows.sort((a, b) =>
    cmp(a.day, b.day) || cmp(sortTime(a.events[0]), sortTime(b.events[0])) || a.events[0].title.localeCompare(b.events[0].title)
  );

  // 依活動：同名同場地只出現一次，排在第一個日期
  const bySeries = new Map();
  for (const r of dayRows) {
    const k = seriesKey(r.events[0]);
    if (!bySeries.has(k)) bySeries.set(k, { day: r.day, events: [], days: [] });
    const g = bySeries.get(k);
    g.events.push(...r.events);
    g.days.push(r.day);
  }
  return { from, to, filtered, dayRows, seriesRows: [...bySeries.values()], long };
}

// 手機日期條：每天點進去會看到幾列（多日活動在每一天都算，同一天同名合併）
function countsPerDay(filtered, from, to) {
  const keys = {};
  const wantLong = state.tab === "long";
  for (const e of filtered) {
    if (!overlaps(e, from, to) || isLong(e) !== wantLong) continue;
    const last = dayOf(e.end) > to ? to : dayOf(e.end);
    for (let d = dayOf(e.start) < from ? from : dayOf(e.start); d <= last; d = addDays(d, 1)) {
      (keys[d] ||= new Set()).add(wantLong ? e.id : seriesKey(e));
    }
  }
  return Object.fromEntries(Object.entries(keys).map(([d, s]) => [d, s.size]));
}

// --- 繪製 ---

function render() {
  const cal = state.view === "calendar";
  document.body.classList.toggle("is-calendar", cal);
  $("#cal-view").hidden = !cal;
  $("#list-view").hidden = cal;
  const toggle = $("#view-toggle");
  toggle.title = cal ? "回到列表" : "我的標記月曆";
  toggle.setAttribute("aria-label", toggle.title);
  renderActiveFilters();
  if (cal) {
    $("#ranges").hidden = $("#strip-wrap").hidden = true;
    renderCalendar();
    return;
  }
  $("#ranges").hidden = false;
  model = compute();
  renderRanges();
  renderStrip();
  renderTabs();
  const list = $("#list");
  list.replaceChildren();
  if (state.tab === "long") renderLong(list);
  else if (state.group === "event" && !isMobile()) renderSeries(list);
  else renderDays(list);
  updateCurrentDay();
  updateApplyButton();
}

// 重繪後維持在原本的位置（標記時不要跳回頂端）
function keepScroll(fn) {
  const y = window.scrollY;
  fn();
  window.scrollTo({ top: y });
}

function renderRanges() {
  const nav = $("#ranges");
  nav.replaceChildren();
  const off = ignoresRange();
  const keys = state.custom ? [...RANGES, ["custom", `${md(state.custom[0])} – ${md(state.custom[1])}`]] : RANGES;
  for (const [key, label] of keys) {
    const b = el("button", "range", label);
    b.type = "button";
    b.setAttribute("aria-pressed", String(!off && state.range === key));
    b.disabled = off;
    const [f, t] = rangeOf(key);
    b.title = f === t ? fmtDay(f) : `${fmtDay(f)} – ${fmtDay(t)}`;
    b.addEventListener("click", () => {
      state.range = key;
      if (key !== "custom") state.custom = null;
      state.expanded.clear();
      render();
      window.scrollTo({ top: 0 });
    });
    nav.append(b);
  }
  if (off) nav.append(el("span", "range-note", "只看標記或新增時不限日期"));
}

function renderStrip() {
  const strip = $("#strip");
  const wrap = $("#strip-wrap");
  strip.replaceChildren();
  const mobile = isMobile();
  let from, to, counts;
  if (mobile) {
    from = state.today;
    to = addDays(state.today, MOBILE_DAYS - 1);
    counts = countsPerDay(model.filtered, from, to);
  } else {
    ({ from, to } = model);
    counts = {};
    for (const r of model.dayRows) counts[r.day] = (counts[r.day] || 0) + 1;
  }
  const n = daysBetween(from, to) + 1;
  // 桌機一兩天的範圍，時段按鈕已經說明了，不用日期條
  wrap.hidden = ignoresRange() || (!mobile && (state.tab === "long" || state.group === "event" || n <= 2 || n > 62));
  if (wrap.hidden) return;
  $("#day-prev").disabled = state.day <= from;
  $("#day-next").disabled = state.day >= to;
  const max = Math.max(1, ...Object.values(counts));
  for (let i = 0; i < n; i++) {
    const day = addDays(from, i);
    const c = counts[day] || 0;
    const b = el("button", "strip-day");
    b.type = "button";
    b.dataset.day = day;
    if (isWeekend(day)) b.classList.add("is-weekend");
    // 手機可以選沒有活動的日子（箭頭也會走到），桌機沒有位置可捲所以停用
    if (mobile) {
      b.setAttribute("aria-pressed", String(day === state.day));
      b.classList.toggle("is-current", day === state.day);
    } else {
      b.disabled = !c;
    }
    b.setAttribute("aria-label", `${fmtDay(day)}，${c} 場`);
    b.append(el("span", "sd-wd", day === state.today ? "今" : WEEKDAYS[weekdayOf(day)]));
    b.append(el("span", "sd-num", String(Number(day.slice(8)))));
    const meter = el("span", "sd-meter");
    const fill = el("span", "sd-fill");
    fill.style.setProperty("--h", c ? Math.max(0.12, c / max) : 0);
    meter.append(fill);
    b.append(meter, el("span", "sd-count", c ? String(c) : "–"));
    b.addEventListener("click", () => (mobile ? selectDay(day) : jumpTo(day)));
    strip.append(b);
  }
  if (mobile) centerStripDay(state.day);
}

// 把日期條上的某一天捲到中間
function centerStripDay(day) {
  const strip = $("#strip");
  const b = strip.querySelector(`[data-day="${day}"]`);
  if (b) strip.scrollTo({ left: b.offsetLeft - strip.offsetLeft - strip.clientWidth / 2 + b.offsetWidth / 2 });
}

function selectDay(day) {
  state.day = day;
  state.expanded.clear();
  render();
  window.scrollTo({ top: 0 });
}

function renderTabs() {
  $("#n-day").textContent = state.group === "event" && !isMobile() ? model.seriesRows.length : model.dayRows.length;
  $("#n-long").textContent = model.long.length;
  for (const b of document.querySelectorAll("[data-tab]")) b.setAttribute("aria-selected", String(b.dataset.tab === state.tab));
  for (const b of document.querySelectorAll("[data-group]")) b.setAttribute("aria-pressed", String(b.dataset.group === state.group));
  // 手機一次只看一天，不需要「依活動」
  $("#group-toggle").hidden = state.tab === "long" || isMobile();
}

function renderDays(list) {
  if (!model.dayRows.length) return list.append(renderEmpty());
  const byDay = new Map();
  for (const r of model.dayRows) {
    if (!byDay.has(r.day)) byDay.set(r.day, []);
    byDay.get(r.day).push(r);
  }
  for (const [day, rows] of byDay) {
    const sec = el("section", "day");
    sec.id = `d-${day}`;
    sec.append(dayHeading(day, rows.length));
    const ul = el("ul", "rows");
    const open = state.expanded.has(day) || rows.length <= DAY_LIMIT + DAY_LIMIT_SLACK;
    for (const r of open ? rows : rows.slice(0, DAY_LIMIT)) ul.append(renderRow(r, "day"));
    sec.append(ul);
    if (!open) {
      const more = el("button", "more", `還有 ${rows.length - DAY_LIMIT} 場，全部展開`);
      more.type = "button";
      more.addEventListener("click", () => {
        state.expanded.add(day);
        ul.replaceChildren(...rows.map((r) => renderRow(r, "day")));
        more.remove();
      });
      sec.append(more);
    }
    list.append(sec);
  }
}

// 日期標頭：大字日期 + 月份星期，今天、明天另外標示
function dayHeading(day, count) {
  const h = el("h2", "day-head");
  if (isWeekend(day)) h.classList.add("is-weekend");
  const rel = day === state.today ? "今天" : day === addDays(state.today, 1) ? "明天" : "";
  h.setAttribute("aria-label", `${fmtDay(day)}${rel ? "，" + rel : ""}，${count} 場`);
  const meta = el("span", "dh-meta");
  const y = Number(day.slice(0, 4));
  meta.append(
    el("span", "dh-month", `${y !== Number(state.today.slice(0, 4)) ? y + " 年 " : ""}${Number(day.slice(5, 7))} 月`),
    el("span", "dh-wd", `週${WEEKDAYS[weekdayOf(day)]}`)
  );
  h.append(el("span", "dh-num", String(Number(day.slice(8)))), meta);
  if (rel) h.append(el("span", "dh-rel", rel));
  h.append(el("span", "dh-count", `${count} 場`));
  for (const c of h.children) c.setAttribute("aria-hidden", "true");
  return h;
}

function renderSeries(list) {
  if (!model.seriesRows.length) return list.append(renderEmpty());
  const sec = el("section", "day flat");
  const ul = el("ul", "rows");
  for (const r of model.seriesRows) ul.append(renderRow(r, "event"));
  sec.append(ul);
  list.append(sec);
}

function renderLong(list) {
  if (!model.long.length) return list.append(renderEmpty());
  list.append(longBox(model.long, "展期超過 14 天的活動（多為展覽），依結束日期排序。"));
}

function longBox(events, hint) {
  const sec = el("section", "day flat");
  if (hint) sec.append(el("p", "hint", hint));
  const ul = el("ul", "rows");
  for (const e of events) ul.append(renderRow({ day: dayOf(e.start), events: [e] }, "long"));
  sec.append(ul);
  return sec;
}

function timeLabel(r, mode) {
  const e = r.events[0];
  if (mode === "long") return [`至 ${md(dayOf(e.end))}`, dayOf(e.start) > state.today ? `${md(dayOf(e.start))} 起` : "展出中"];
  if (mode === "event") return [md(r.days[0]), `週${WEEKDAYS[weekdayOf(r.days[0])]}`];
  if (isMultiDay(e)) return ["多日", `至 ${md(dayOf(e.end))}`];
  if (isAllDay(e)) return ["全天", ""];
  const times = [...new Set(r.events.map((x) => timeOf(x.start)))];
  return [times[0], times.length > 1 ? `+${times.length - 1} 場` : ""];
}

// 一列一筆：時間、標題與地點（點開詳情）、標籤、愛心
function renderRow(r, mode) {
  const e = r.events[0];
  const kind = state.marks[e.id];
  const li = el("li", "row");
  li.dataset.cat = catKey(e.category);
  if (kind) li.classList.add(`is-${kind}`);

  const [t1, t2] = timeLabel(r, mode);
  const time = el("span", "r-time");
  time.append(el("span", "rt-main", t1));
  if (t2) time.append(el("span", "rt-sub", t2));

  const main = el("button", "r-main");
  main.type = "button";
  const sub = el("span", "r-sub");
  sub.append(el("span", "r-cat", catShort(e.category)), el("span", "r-place", e.venue || e.district || "地點未提供"));
  if (e.district && e.venue && !e.venue.includes(e.district.replace(/區$/, ""))) sub.append(el("span", "r-dist", e.district));
  main.append(el("span", "r-title", e.title), sub);
  main.addEventListener("click", () => openDetail(e));

  const tags = el("span", "r-tags");
  if (e.fee === "免費") tags.append(el("span", "tag tag-free", "免費"));
  if (isNew(e)) tags.append(el("span", "tag tag-new", "新增"));
  if (mode === "event" && r.days.length > 1) tags.append(el("span", "tag", `${r.days.length} 天`));
  if (mode === "day" && r.otherDays > 0) tags.append(el("span", "tag", `另 ${r.otherDays} 天`));

  // 愛心只切換「想去」；已報名在詳情裡設定，這裡點一下就取消
  const mark = el("button", "r-mark");
  mark.type = "button";
  mark.append(icon(kind === "going" ? "i-going" : "i-want"));
  mark.setAttribute("aria-pressed", String(!!kind));
  mark.setAttribute("aria-label", kind ? `${MARK_LABELS[kind]}：${e.title}（點一下取消）` : `想去：${e.title}`);
  mark.title = kind ? `${MARK_LABELS[kind]}（點一下取消）` : "想去";
  mark.addEventListener("click", () => {
    if (kind) delete state.marks[e.id];
    else state.marks[e.id] = "want";
    saveMarks();
    keepScroll(render);
  });

  li.append(time, main, tags, mark);
  return li;
}

function renderEmpty() {
  const box = el("div", "empty");
  box.append(icon("i-radar", "empty-icon"));
  box.append(
    el(
      "p",
      "",
      state.markFilter.size && !Object.keys(state.marks).length
        ? "還沒有標記任何活動。點活動右邊的愛心就會出現在這裡。"
        : state.newOnly
          ? "這次更新沒有符合條件的新增活動。"
          : isMobile()
            ? "這天沒有符合條件的活動。"
            : "這段期間沒有符合條件的活動。"
    )
  );
  const action = (label, fn) => {
    const b = el("button", "reset", label);
    b.type = "button";
    b.addEventListener("click", fn);
    box.append(b);
  };
  const next = isMobile() && !ignoresRange() ? nextBusyDay() : null;
  if (next) action(`跳到下一個有活動的日子：${fmtDay(next)}`, () => selectDay(next));
  else if (activeFilterList().length) action("清除篩選", () => { resetFilters(); render(); });
  else if (!isMobile() && state.range !== "month") action("改看 30 天內", () => { state.range = "month"; state.custom = null; render(); });
  return box;
}

function nextBusyDay() {
  const counts = countsPerDay(model.filtered, addDays(state.day, 1), addDays(state.today, MOBILE_DAYS - 1));
  return Object.keys(counts).sort()[0] || null;
}

// --- 已套用的篩選條件：顯示在列表上方，可以逐一移除 ---

function activeFilterList() {
  const out = [];
  if (state.q) out.push([`「${state.q}」`, () => { state.q = ""; $("#q").value = ""; }]);
  for (const c of state.categories) out.push([catShort(c), () => state.categories.delete(c)]);
  for (const f of state.fees) out.push([f, () => state.fees.delete(f)]);
  if (state.district) out.push([state.district, () => { state.district = ""; }]);
  for (const s of state.sources) out.push([state.sourceLabels[s] || s, () => state.sources.delete(s)]);
  if (state.newOnly) out.push([newLabel(), () => { state.newOnly = false; }]);
  for (const k of state.markFilter) out.push([MARK_LABELS[k], () => state.markFilter.delete(k)]);
  return out;
}

function renderActiveFilters() {
  const box = $("#active-filters");
  box.replaceChildren();
  const list = activeFilterList();
  const badge = $("#filter-count");
  badge.hidden = !list.length;
  badge.textContent = list.length;
  for (const [label, remove] of list) {
    const b = el("button", "af");
    b.type = "button";
    b.append(el("span", "", label), icon("i-x"));
    b.setAttribute("aria-label", `移除篩選：${label}`);
    b.addEventListener("click", () => {
      remove();
      render();
      syncSheet();
    });
    box.append(b);
  }
  if (list.length > 1) {
    const b = el("button", "af-clear", "全部清除");
    b.type = "button";
    b.addEventListener("click", () => {
      resetFilters();
      render();
    });
    box.append(b);
  }
  box.hidden = !list.length;
}

function resetFilters() {
  state.q = "";
  $("#q").value = "";
  state.categories.clear();
  state.fees.clear();
  state.sources.clear();
  state.markFilter.clear();
  state.district = "";
  state.newOnly = false;
  if (state.range === "custom") state.range = DEFAULT_RANGE;
  state.custom = null;
  syncSheet();
}

// --- 篩選面板 ---

function makeChip(label, pressed, onClick, count) {
  const b = el("button", "chip");
  b.type = "button";
  b.append(el("span", "", label));
  if (count != null) b.append(el("span", "chip-count", String(count)));
  b.setAttribute("aria-pressed", String(pressed));
  b.addEventListener("click", () => {
    // chips 會整組重建，記下位置好把焦點還給新的那顆
    const parent = b.parentElement;
    const idx = [...parent.children].indexOf(b);
    onClick();
    state.expanded.clear();
    render();
    syncSheet();
    parent.children[idx]?.focus({ preventScroll: true });
  });
  return b;
}

const toggleIn = (set, value) => () => (set.has(value) ? set.delete(value) : set.add(value));

// 最近一次更新是今天就叫「今天新增」，否則標出日期，避免更新中斷時誤以為是今天
function newLabel() {
  return state.latestDay === state.today ? "今天新增" : `${md(state.latestDay)} 新增`;
}

// 篩選面板的 chips 每次依目前狀態重建，筆數也一起更新
function syncSheet() {
  $("#f-cats").replaceChildren(
    ...CATEGORIES.map((c) => {
      const b = makeChip(catShort(c), state.categories.has(c), toggleIn(state.categories, c));
      b.classList.add("chip-cat");
      b.dataset.cat = catKey(c);
      b.prepend(icon(`i-${catKey(c)}`));
      return b;
    })
  );
  $("#f-fee").replaceChildren(...["免費", "付費", "未知"].map((f) => makeChip(f, state.fees.has(f), toggleIn(state.fees, f))));

  const marks = Object.keys(MARK_LABELS).map((k) => {
    const b = makeChip(MARK_LABELS[k], state.markFilter.has(k), toggleIn(state.markFilter, k), markCount(k));
    b.classList.add("chip-mark");
    b.dataset.mark = k;
    b.prepend(icon(`i-${k}`));
    return b;
  });
  const newCount = state.events.filter(isNew).length;
  const newChip = makeChip(newLabel(), state.newOnly, () => { state.newOnly = !state.newOnly; }, newCount);
  newChip.classList.add("chip-new");
  $("#f-marks").replaceChildren(...marks, newChip);

  // 來源依 status.json 的順序排列，再補上 status 裡沒有的來源；筆數是套用其他條件後的結果
  const others = new Set(state.sources);
  state.sources.clear();
  const counts = {};
  for (const e of state.events) {
    if (!matches(e)) continue;
    for (const s of e.sources) counts[s] = (counts[s] || 0) + 1;
  }
  for (const s of others) state.sources.add(s);
  const names = [...new Set([...Object.keys(state.sourceLabels), ...state.events.flatMap((e) => e.sources)])];
  $("#f-srcs").replaceChildren(
    ...names.map((s) => makeChip(state.sourceLabels[s] || s, state.sources.has(s), toggleIn(state.sources, s), counts[s] || 0))
  );

  $("#f-district").value = state.district;
  $("#f-from").value = state.custom ? state.custom[0] : "";
  $("#f-to").value = state.custom ? state.custom[1] : "";
  updateApplyButton();
}

function updateApplyButton() {
  if (!model) return;
  const n = state.tab === "long" ? model.long.length : model.dayRows.length;
  $("#f-apply").textContent = `顯示 ${n} 筆活動`;
}

function onCustomDates() {
  const from = $("#f-from").value;
  const to = $("#f-to").value;
  if (!from && !to) {
    state.custom = null;
    if (state.range === "custom") state.range = DEFAULT_RANGE;
  } else {
    const a = from || state.today;
    const b = to || addDays(a, 29);
    state.custom = a <= b ? [a, b] : [b, a];
    state.range = "custom";
  }
  state.expanded.clear();
  render();
}

// --- 活動詳情 ---

function openDetail(e) {
  const body = $("#drawer-body");
  body.replaceChildren();
  body.dataset.cat = catKey(e.category);

  const head = el("div", "d-cat");
  const pill = el("span", "d-cat-pill");
  pill.append(icon(`i-${catKey(e.category)}`), el("span", "", e.category));
  head.append(pill);
  if (isNew(e)) head.append(el("span", "tag tag-new", "新增"));
  body.append(head, el("h2", "d-title", e.title));

  const marks = el("div", "d-marks");
  for (const k of Object.keys(MARK_LABELS)) {
    const b = el("button", "chip chip-mark");
    b.type = "button";
    b.dataset.mark = k;
    b.append(icon(`i-${k}`), el("span", "", MARK_LABELS[k]));
    b.setAttribute("aria-pressed", String(state.marks[e.id] === k));
    b.addEventListener("click", () => {
      toggleMark(e, k);
      keepScroll(render);
      for (const x of marks.children) x.setAttribute("aria-pressed", String(state.marks[e.id] === x.dataset.mark));
    });
    marks.append(b);
  }
  body.append(marks);

  const facts = el("dl", "d-facts");
  const fact = (ic, label, node) => {
    const dt = el("dt");
    dt.append(icon(ic), el("span", "sr-only", label));
    const dd = el("dd");
    dd.append(node);
    facts.append(dt, dd);
  };

  const series = (state.series.get(seriesKey(e)) || [e]).filter((x) => dayOf(x.end) >= state.today);
  const when = el("div", "d-stack");
  if (series.length > 1) {
    when.append(el("span", "d-strong", `共 ${series.length} 個場次`));
    const ul = el("ul", "d-sessions");
    for (const x of series) ul.append(el("li", x.id === e.id ? "is-current" : "", whenText(x)));
    when.append(ul);
  } else {
    when.append(el("span", "d-strong", whenText(e)));
  }
  fact("i-clock", "時間", when);

  const where = el("div", "d-stack");
  where.append(el("span", "d-strong", [e.venue, e.district].filter(Boolean).join(" · ") || "地點未提供"));
  if (e.address && e.address !== e.venue) where.append(el("span", "d-muted", e.address));
  fact("i-pin", "地點", where);

  const org = el("div", "d-stack d-inline");
  org.append(el("span", "", e.organizer || "主辦單位未提供"));
  if (e.organizer_type === "政府") org.append(el("span", "tag tag-gov", "政府"));
  else if (e.organizer_type === "民間") org.append(el("span", "tag tag-private", "民間"));
  fact("i-org", "主辦", org);
  body.append(facts);

  const fee = el("p", "d-fee");
  fee.append(el("span", `tag ${e.fee === "免費" ? "tag-free" : ""}`, e.fee === "未知" ? "費用未知" : e.fee));
  body.append(fee);

  if (e.description) body.append(el("h3", "d-sub", "簡介"), el("p", "d-desc", e.description));

  const links = el("div", "d-links");
  for (const l of e.links) {
    const href = safeUrl(l.url);
    if (!href) continue;
    const a = el("a", "d-link");
    a.href = href;
    a.target = "_blank";
    a.rel = "noopener noreferrer";
    a.append(el("span", "", `在「${state.sourceLabels[l.source] || l.source}」查看`), icon("i-link"));
    links.append(a);
  }
  if (links.childElementCount) body.append(links);

  showPanel("#drawer");
}

// --- 面板開關 ---

let lastFocus = null;

function showPanel(sel) {
  if ($("#scrim").hidden) lastFocus = document.activeElement;
  for (const p of document.querySelectorAll(".panel")) p.hidden = p !== $(sel);
  $("#scrim").hidden = false;
  document.body.classList.add("has-panel");
  $(sel).querySelector(".drawer-body, .sheet-body").scrollTo(0, 0);
  $(sel).querySelector("[data-close]").focus({ preventScroll: true });
}

function closePanels() {
  for (const p of document.querySelectorAll(".panel")) p.hidden = true;
  $("#scrim").hidden = true;
  document.body.classList.remove("has-panel");
  if (lastFocus && document.contains(lastFocus)) lastFocus.focus({ preventScroll: true });
}

// --- 捲動 ---

const stickyHeight = () => $("#top").getBoundingClientRect().height;

function jumpTo(day) {
  const sec = document.getElementById(`d-${day}`);
  if (!sec) return;
  const y = sec.getBoundingClientRect().top + window.scrollY - stickyHeight() + 1;
  window.scrollTo({ top: y, behavior: window.matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth" });
}

// 桌機日期條標出目前看到的那一天，並捲到看得見
function updateCurrentDay() {
  const strip = $("#strip");
  if ($("#strip-wrap").hidden || isMobile() || state.view === "calendar") return;
  const line = stickyHeight() + 40;
  let current = null;
  for (const sec of document.querySelectorAll(".day[id]")) {
    if (sec.getBoundingClientRect().top > line) break;
    current = sec.id.slice(2);
  }
  for (const b of strip.children) {
    const on = b.dataset.day === current;
    if (on && !b.classList.contains("is-current")) {
      const r = b.getBoundingClientRect(), sr = strip.getBoundingClientRect();
      if (r.left < sr.left || r.right > sr.right) strip.scrollBy({ left: r.left - sr.left - sr.width / 2 + r.width / 2 });
    }
    b.classList.toggle("is-current", on);
  }
}

// --- 月曆 ---

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
  const first = `${month}-01`;
  if (month === state.today.slice(0, 7)) {
    state.calDay = state.today;
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
  const today = state.today;
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
  $("#meta").textContent = `已標記 ${total} 筆活動`;
  $("#cal-empty").hidden = total > 0;

  const head = el("div", "cal-weekdays");
  head.setAttribute("aria-hidden", "true");
  WEEKDAYS.forEach((wd, i) => head.append(el("span", i === 0 || i === 6 ? "is-weekend" : "", wd)));
  const grid = $("#cal-grid");
  grid.replaceChildren(head);
  const short = events.filter((e) => !isLong(e));
  for (let start = addDays(first, -weekdayOf(first)); start <= last; start = addDays(start, 7)) {
    grid.append(renderWeek(start, short, events, month, today));
  }

  const list = events.filter((e) => overlaps(e, state.calDay, state.calDay)).sort(byMark);
  const box = el("section", "day");
  box.append(dayHeading(state.calDay, list.length));
  if (list.length) {
    const ul = el("ul", "rows");
    for (const e of list) ul.append(renderRow({ day: state.calDay, events: [e] }, isLong(e) ? "long" : "cal"));
    box.append(ul);
  } else {
    box.append(el("p", "hint cal-none", "這天沒有標記的活動。"));
  }
  $("#cal-agenda").replaceChildren(box);

  const long = events.filter(isLong).sort((a, b) => a.end.localeCompare(b.end));
  $("#cal-long").hidden = !long.length;
  $("#cal-long-title").textContent = `本月可去的長期活動（${long.length}）`;
  $("#cal-long-list").replaceChildren(longBox(long));
}

// 一週一列：底層是七個日期按鈕，上面疊跨日橫條（只是裝飾，點擊會穿透到日期）
function renderWeek(start, short, all, month, today) {
  const end = addDays(start, 6);
  const week = el("div", "cal-week");

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
    const cell = el("button", "cal-day");
    cell.type = "button";
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

    const num = el("span", "cal-num", String(Number(day.slice(8))));
    num.setAttribute("aria-hidden", "true");
    cell.append(num);
    if (hidden[i]) {
      const more = el("span", "cal-more", `+${hidden[i]}`);
      more.setAttribute("aria-hidden", "true");
      cell.append(more);
    }

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
  const bar = el("div", "cal-bar");
  bar.dataset.mark = kind;
  bar.setAttribute("aria-hidden", "true");
  bar.style.gridColumn = `${from + 1} / span ${span}`;
  bar.style.gridRow = lane + 2;
  // 跨週的活動在接續的那一側不畫圓角
  if (s > dayOf(e.start)) bar.classList.add("cont-left");
  if (t < dayOf(e.end)) bar.classList.add("cont-right");
  const time = timeOf(e.start);
  const showTime = s === dayOf(e.start) && time !== "00:00";
  bar.append(icon(`i-${kind}`), el("span", "", `${showTime ? time + " " : ""}${e.title}`));
  return bar;
}

// 月曆圖例：想去／已報名，附筆數
function setupCalendar() {
  state.calMonth = state.today.slice(0, 7);
  state.calDay = state.today;
  for (const [kind, label] of Object.entries(MARK_LABELS)) {
    const b = el("button", "chip chip-mark");
    b.type = "button";
    b.dataset.mark = kind;
    b.append(icon(`i-${kind}`), el("span", "", label), el("span", "chip-count"));
    b.setAttribute("aria-pressed", "false");
    b.addEventListener("click", () => {
      toggleIn(state.calKinds, kind)();
      b.setAttribute("aria-pressed", String(state.calKinds.has(kind)));
      render();
    });
    state.calChips.set(kind, b);
    $("#cal-legend").append(b);
  }
  $("#cal-prev").addEventListener("click", () => goMonth(shiftMonth(state.calMonth, -1)));
  $("#cal-next").addEventListener("click", () => goMonth(shiftMonth(state.calMonth, 1)));
  $("#cal-today").addEventListener("click", () => goMonth(state.today.slice(0, 7)));
}

// --- 資料來源狀態 ---

function renderStatus(status) {
  const body = $("#status-body");
  body.replaceChildren();
  for (const [name, s] of Object.entries(status.sources || {})) {
    state.sourceLabels[name] = s.label || name;
    const tr = el("tr", !s.ok || !s.count ? "bad" : "");
    const tdName = el("td", "", s.label || name);
    if (s.error) tdName.append(el("span", "err", `本次失敗：${s.error}`));
    else if (!s.count) tdName.append(el("span", "err", "本次抓到 0 筆，可能網站改版"));
    const tdTime = el("td", "", s.last_success ? fmtDateTime(s.last_success) : "從未成功");
    const tdCount = el("td", "", s.ok ? s.count : `${s.cached_count ?? 0}（舊資料）`);
    tr.append(tdName, tdTime, tdCount);
    body.append(tr);
  }
}

function fmtDateTime(iso) {
  return `${fmtDay(dayOf(iso))} ${timeOf(iso)}`;
}

// --- 初始化 ---

let metaText = "";

function setupControls() {
  let qTimer;
  $("#q").addEventListener("input", (ev) => {
    clearTimeout(qTimer);
    qTimer = setTimeout(() => {
      state.q = ev.target.value.trim().toLowerCase();
      state.expanded.clear();
      render();
    }, 180);
  });

  const districts = [...new Set(state.events.map((e) => e.district).filter(Boolean))].sort((a, b) =>
    a.localeCompare(b, "zh-Hant-TW")
  );
  for (const d of districts) $("#f-district").append(new Option(d, d));
  $("#f-district").addEventListener("change", (ev) => {
    state.district = ev.target.value;
    render();
    syncSheet();
  });
  $("#f-from").addEventListener("change", onCustomDates);
  $("#f-to").addEventListener("change", onCustomDates);
  $("#sync-share").addEventListener("click", shareSyncLink);

  for (const b of document.querySelectorAll("[data-tab]")) {
    b.addEventListener("click", () => {
      state.tab = b.dataset.tab;
      render();
    });
  }
  for (const b of document.querySelectorAll("[data-group]")) {
    b.addEventListener("click", () => {
      state.group = b.dataset.group;
      render();
    });
  }
  $("#day-prev").addEventListener("click", () => selectDay(addDays(state.day, -1)));
  $("#day-next").addEventListener("click", () => selectDay(addDays(state.day, 1)));

  $("#open-filters").addEventListener("click", () => {
    syncSheet();
    showPanel("#sheet");
  });
  $("#f-reset").addEventListener("click", () => {
    resetFilters();
    render();
    syncSheet();
  });
  $("#scrim").addEventListener("click", closePanels);
  for (const b of document.querySelectorAll("[data-close]")) b.addEventListener("click", closePanels);
  document.addEventListener("keydown", (ev) => {
    if (ev.key === "Escape" && !$("#scrim").hidden) closePanels();
  });

  // 視圖記在網址，重新整理或按上一頁都會回到同一個視圖
  $("#view-toggle").addEventListener("click", () => {
    location.hash = state.view === "calendar" ? "" : "calendar";
  });
  window.addEventListener("hashchange", () => {
    // 已開著的分頁直接貼上同步連結時，只會觸發 hashchange 不會重新載入
    const imported = importSyncHash();
    if (imported) {
      syncMarks(state.events, imported.marks);
      $("#sync-msg").textContent = syncMessage(imported);
    }
    state.view = viewFromHash();
    if (state.view === "list") $("#meta").textContent = metaText;
    render();
    window.scrollTo({ top: 0 });
  });

  mobileQuery.addEventListener("change", () => render());
  let ticking = false;
  window.addEventListener(
    "scroll",
    () => {
      if (ticking) return;
      ticking = true;
      requestAnimationFrame(() => {
        ticking = false;
        updateCurrentDay();
      });
    },
    { passive: true }
  );
  // 日期標頭黏在頂部區塊下方
  new ResizeObserver(() => document.documentElement.style.setProperty("--stick", `${stickyHeight()}px`)).observe($("#top"));
}

const viewFromHash = () => (location.hash === "#calendar" ? "calendar" : "list");

async function main() {
  try {
    const [eventsRes, statusRes] = await Promise.all([
      fetch("data/events.json", { cache: "no-cache" }),
      fetch("data/status.json", { cache: "no-cache" }),
    ]);
    if (!eventsRes.ok) throw new Error(`events.json ${eventsRes.status}`);
    const data = await eventsRes.json();
    const status = statusRes.ok ? await statusRes.json() : { sources: {} };
    state.today = state.day = taipeiToday();
    state.events = data.events.filter((e) => dayOf(e.end) >= state.today);
    state.latestDay = dayOf(data.generated_at);
    for (const e of state.events) {
      const k = seriesKey(e);
      if (!state.series.has(k)) state.series.set(k, []);
      state.series.get(k).push(e);
    }
    for (const list of state.series.values()) list.sort((a, b) => a.start.localeCompare(b.start));
    const imported = importSyncHash();
    syncMarks(data.events, imported?.marks);
    renderStatus(status);
    const newCount = state.events.filter(isNew).length;
    metaText = `更新於 ${fmtDateTime(data.generated_at)} · 共 ${state.events.length} 筆活動${newCount ? ` · 新增 ${newCount} 筆` : ""}`;
    if (imported) metaText += ` · ${syncMessage(imported)}`;
    $("#meta").textContent = metaText;
    state.view = viewFromHash();
    setupControls();
    setupCalendar();
    render();
    syncSheet();
  } catch (err) {
    $("#meta").textContent = `資料載入失敗：${err.message}`;
    throw err;
  }
}

main();
