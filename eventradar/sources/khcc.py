"""來源：高雄市政府文化局官網「文化中心展演活動」。

文化局四個館舍（高雄市文化中心、岡山文化中心、高雄市音樂館、大東文化藝術中心）的展覽與演出，
列表依館舍分頁，每筆有名稱、時間、地點，演出另有演出單位。
主辦單位、入場方式（免票／售票／特定對象）與展覽簡介要讀詳情頁；上次讀過的沿用舊資料，不重抓。

已知限制：
- 展覽只有起訖日期，時間視為整天
- 入場方式為「特定對象」的演出（典禮、公會活動等）不對外開放，不收
- 展覽詳情頁沒有寫費用，費用標「未知」
"""

from __future__ import annotations

import html
import json
import re
import time
from datetime import datetime
from datetime import time as dtime

from .. import http
from ..classify import category_by_keywords, organizer_type_of
from ..model import TAIPEI, Event, Link

NAME = "khcc"
LABEL = "文化局展演（文化中心）"
BASE = "https://khcc.kcg.gov.tw/"
LIST_URL = BASE + "rwd_home03.aspx?ID=$M102&IDK=2&EXEC=L&AP=$M102_TYPE-^$M102_HISTORY-0^$M102_KEYWORD-^$M102_ORG-{org}^$M102_PAGE-{page}"
MAX_PAGES = 20
DETAIL_DELAY = 0.5
MAX_NEW_DETAILS = 200

# 館舍代碼（列表「館舍」選單）：館名、地址、行政區
HALLS = {
    "01": ("高雄市文化中心", "高雄市苓雅區五福一路67號", "苓雅區"),
    "02": ("岡山文化中心", "高雄市岡山區岡山路42號", "岡山區"),
    "03": ("高雄市音樂館", "高雄市鹽埕區河西路99號", "鹽埕區"),
    "04": ("大東文化藝術中心", "高雄市鳳山區光遠路161號", "鳳山區"),
}
# 地點欄位寫法如「大東展覽館  每日10-17時,周一無休」，開放時間不放進場地名稱
_HOURS_RE = re.compile(r"[\s,，]*每日.*$")

_BOX_RE = re.compile(r'<div class="row m101_box"[^>]*>(.*?)(?=<div class="row m101_box"|<table|\Z)', re.S)
_LINK_RE = re.compile(r'<a href="(rwd_home03\.aspx\?ID=\$M102&IDK=2&EXEC=D&DATA=(-?\d+)[^"]*)"><span[^>]*>(.*?)</span></a>', re.S)
_PAGE_RE = re.compile(r"GoPage5700\((\d+)\)")
_DATE_RE = re.compile(r"(\d{2,3})/(\d{1,2})/(\d{1,2})")
_CLOCK_RANGE_RE = re.compile(r"(\d{1,2}):(\d{2})\s*~\s*(\d{1,2}):(\d{2})")


def _text(fragment: str) -> str:
    return " ".join(html.unescape(re.sub(r"<[^>]+>", " ", fragment)).split())


def _fields(fragment: str) -> dict[str, str]:
    """把「標籤:值」的各行讀成 dict；冒號全形半形都有。"""
    fields = {}
    for line in re.split(r"<div[^>]*>", fragment):
        m = re.match(r"([^:：]{2,6})[:：](.*)", _text(line))
        if m:
            fields[m.group(1).strip()] = m.group(2).strip()
    return fields


def parse_list(page: str, org: str) -> list[dict]:
    items = []
    for box in _BOX_RE.findall(page):
        m = _LINK_RE.search(box)
        if not m:
            continue
        # 標題沒有跳脫，可能含「<午茶絲竹吧>」這種角括號，直接取 span 內的原始文字
        title = " ".join(html.unescape(m.group(3)).split())
        fields = _fields(box)
        kind = "exhibition" if "展覽名稱" in fields else "performance"
        items.append({
            "org": org,
            "kind": kind,
            "data": m.group(2),
            "url": BASE + html.unescape(m.group(1)),
            "title": title,
            "when": fields.get("展覽時間") or fields.get("演出時間") or "",
            "place": fields.get("展覽地點") or fields.get("演出地點") or "",
            "type": fields.get("類型名稱", ""),
            "performer": fields.get("演出單位", ""),
        })
    return items


def _last_page(page: str) -> int:
    return max((int(n) for n in _PAGE_RE.findall(page)), default=1)


def parse_detail(page: str) -> dict:
    """從詳情頁讀出主辦單位、入場方式；展覽另有簡介。"""
    start = page.find('id="toplink"')
    body = page[start if start >= 0 else 0:]
    end = body.find("BACK")
    body = body[:end if end >= 0 else None]
    segs = [s for s in (_text(p) for p in re.split(r"<(?:div|p|br|li|td)[^>]*>", body)) if s]
    detail = {"organizer": "", "admission": "", "description": ""}
    desc = []
    for s in segs:
        m = re.match(r"(主辦單位|入場方式)[:：]\s*(.*)", s)
        if m:
            detail["organizer" if m.group(1) == "主辦單位" else "admission"] = m.group(2).strip()
        elif s.startswith("截止日期"):
            desc = []  # 簡介從截止日期之後開始
        elif not re.match(r"(活動型態|展覽地點|開始日期|演出時間|演出地點|演出單位|聯絡電話|售票系統)[:：]", s):
            desc.append(s)
    if any("截止日期" in s for s in segs):
        detail["description"] = "\n".join(desc)
    return detail


_ADMISSION_FEE = {"免票": "免費", "售票": "付費"}
_FEE_ADMISSION = {v: k for k, v in _ADMISSION_FEE.items()}


def _fee(admission: str) -> str:
    # 「索票 (於服務台索取…)」是免費索取的票券
    return "免費" if admission.startswith("索票") else _ADMISSION_FEE.get(admission, "未知")


def fetch(previous=None) -> bytes:
    items = []
    for org in HALLS:
        last = 1
        page = 1
        while page <= min(last, MAX_PAGES):
            text = http.get(LIST_URL.format(org=org, page=page)).text
            items.extend(parse_list(text, org))
            last = _last_page(text)
            page += 1
    known = {}
    for e in previous or []:
        if e.links:
            # 演出的簡介是由演出單位組成，不是詳情頁內容
            desc = "" if e.description.startswith(_PERFORMER_PREFIX) else e.description
            known[e.links[0].url] = {"organizer": e.organizer, "admission": _FEE_ADMISSION.get(e.fee, ""), "description": desc}
    details, fetched = {}, 0
    for item in items:
        url = item["url"]
        if url in details:
            continue
        if url in known:
            details[url] = known[url]
        elif fetched < MAX_NEW_DETAILS:
            try:
                details[url] = parse_detail(http.get(url).text)
            except Exception:
                details[url] = {}
            fetched += 1
            time.sleep(DETAIL_DELAY)
    return json.dumps({"items": items, "details": details}, ensure_ascii=False).encode("utf-8")


_PERFORMER_PREFIX = "演出單位："


def _roc_date(m: re.Match) -> datetime:
    return datetime(int(m.group(1)) + 1911, int(m.group(2)), int(m.group(3)), tzinfo=TAIPEI)


def _span(item: dict) -> tuple[datetime, datetime] | None:
    dates = list(_DATE_RE.finditer(item["when"]))
    if not dates:
        return None
    try:
        first, last = _roc_date(dates[0]), _roc_date(dates[-1])
    except ValueError:
        return None
    clocks = [tuple(map(int, c)) for c in _CLOCK_RANGE_RE.findall(item["when"])]
    if item["kind"] == "performance" and clocks:
        # 同一天多場，例如「19:30~22:00, 15:00~17:30」：取最早開始到最晚結束
        start = min(dtime(h1, m1) for h1, m1, _, _ in clocks)
        end = max(dtime(23, 59, 59) if h2 >= 24 else dtime(h2, m2) for _, _, h2, m2 in clocks)
        return datetime.combine(first.date(), start, TAIPEI), datetime.combine(last.date(), end, TAIPEI)
    return first, datetime.combine(last.date(), dtime(23, 59, 59), TAIPEI)


def parse(content: bytes, now: datetime) -> list[Event]:
    raw = json.loads(content)
    details = raw.get("details") or {}
    events, seen = [], set()
    for item in raw.get("items") or []:
        event = _parse_item(item, details.get(item["url"]) or {}, now)
        if event and event.id not in seen:
            seen.add(event.id)
            events.append(event)
    return events


def _parse_item(item: dict, detail: dict, now: datetime) -> Event | None:
    span = _span(item)
    if not span or span[1] < now or not item["title"]:
        return None
    if detail.get("admission") == "特定對象":
        return None
    start, end = span
    hall, address, district = HALLS[item["org"]]
    place = _HOURS_RE.sub("", item["place"]).strip()
    # 大東的地點多已帶館名（「大東演藝廳」），音樂館的地點就寫「音樂館」，都不重複加
    if place in hall:
        venue = hall
    elif place.startswith(hall[:2]):
        venue = place
    else:
        venue = f"{hall} {place}"
    if item["kind"] == "exhibition":
        event_id = f"{NAME}:{item['data']}"
        category = "展覽"
        description = detail.get("description", "")
    else:
        # 同一檔演出跨多天時，每天的 DATA 相同，以日期區分
        event_id = f"{NAME}:{item['data']}:{start:%Y%m%d}"
        category = category_by_keywords(item["title"], default="表演／音樂")
        description = f"{_PERFORMER_PREFIX}{item['performer']}" if item["performer"] else ""
    organizer = detail.get("organizer", "")
    return Event(
        id=event_id,
        title=item["title"],
        start=start,
        end=end,
        venue=venue,
        address=address,
        district=district,
        category=category,
        fee=_fee(detail.get("admission", "")),
        organizer=organizer,
        organizer_type=organizer_type_of(organizer),
        description=description,
        links=[Link(source=NAME, url=item["url"])],
    )
