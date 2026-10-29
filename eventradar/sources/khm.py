"""來源：高雄市立歷史博物館官網「活動報名」。

列表有標題與活動日期；詳情頁的「活動場次」表格有每個場次的活動時間、地點與費用，
沒有場次表（改用外部表單報名）的活動，地點從「活動資訊」內文的「地點：」讀。
活動數量很少，每次都重抓全部詳情頁。展覽已由文化部 iCulture 收錄，這裡不收。

已知限制：
- 多個場次合併成一筆，起訖為第一場到最後一場
- 沒有場次表的活動只有日期，視為整天，費用標「未知」
"""

from __future__ import annotations

import html
import json
import re
import time
from datetime import datetime
from datetime import time as dtime

from .. import http
from ..classify import category_by_keywords
from ..geo import district_of
from ..model import TAIPEI, Event, Link

NAME = "khm"
LABEL = "高雄市立歷史博物館"
LIST_URL = "https://www.khm.org.tw/tw/event?page={page}"
MAX_PAGES = 5
DETAIL_DELAY = 0.5
DESCRIPTION_LIMIT = 300
ORGANIZER = "高雄市立歷史博物館"
MUSEUM = "高雄市立歷史博物館"
MUSEUM_ADDRESS = "高雄市鹽埕區中正四路272號"

_ITEM_RE = re.compile(
    r'<a href="(https://www\.khm\.org\.tw/tw/event/detail/(\d+))" class="list-link".*?'
    r'<h3 class="item-title">(.*?)</h3>.*?<span class="item-date">(.*?)</span>',
    re.S,
)
_ROW_RE = re.compile(r"<tr>(.*?)</tr>", re.S)
_CELL_RE = re.compile(r'<td data-title="([^"]+)">(.*?)</td>', re.S)
_DATE_RE = re.compile(r"(\d{4})\.(\d{1,2})\.(\d{1,2})(?:\s+(\d{1,2}):(\d{2}))?")
_PLACE_RE = re.compile(r"^地點[:：]\s*(.+)")


def _text(fragment: str) -> str:
    return " ".join(html.unescape(re.sub(r"<[^>]+>", " ", fragment)).split())


def parse_list(page: str) -> list[dict]:
    return [
        {"id": m.group(2), "url": m.group(1), "title": _text(m.group(3)), "dates": _text(m.group(4))}
        for m in _ITEM_RE.finditer(page)
    ]


def parse_detail(page: str) -> dict:
    sessions = []
    table = page[page.find("Event Session"):page.find("Information")]
    for row in _ROW_RE.findall(table):
        cells = {k: _text(v) for k, v in _CELL_RE.findall(row)}
        if cells.get("活動時間"):
            sessions.append({"time": cells["活動時間"], "place": cells.get("活動地點", ""), "fee": cells.get("活動費用", "")})
    start = page.find("Information")
    end = page.find("Reminders", start)
    info = page[start:end] if start >= 0 else ""
    lines = [_text(s) for s in re.split(r"<(?:br|p|div|li|h\d)[^>]*>", info)]
    lines = [s for s in lines if s and s not in ("Information", "活動資訊")]
    return {"sessions": sessions, "info": "\n".join(lines)}


def fetch(previous=None) -> bytes:
    items, seen = [], set()
    for page in range(1, MAX_PAGES + 1):
        new = [i for i in parse_list(http.get(LIST_URL.format(page=page)).text) if i["id"] not in seen]
        if not new:
            break
        seen.update(i["id"] for i in new)
        items.extend(new)
    details = {}
    for item in items:
        try:
            details[item["id"]] = parse_detail(http.get(item["url"]).text)
        except Exception:
            details[item["id"]] = {}
        time.sleep(DETAIL_DELAY)
    return json.dumps({"items": items, "details": details}, ensure_ascii=False).encode("utf-8")


def _datetimes(text: str) -> list[datetime]:
    result = []
    for y, mo, d, h, mi in _DATE_RE.findall(text):
        try:
            result.append(datetime(int(y), int(mo), int(d), int(h or 0), int(mi or 0), tzinfo=TAIPEI))
        except ValueError:
            pass
    return result


def _span(item: dict, sessions: list[dict]) -> tuple[datetime, datetime] | None:
    times = [t for s in sessions for t in _datetimes(s["time"])]
    if times:
        return min(times), max(times)
    dates = _datetimes(item["dates"])
    if not dates:
        return None
    return dates[0], datetime.combine(dates[-1].date(), dtime(23, 59, 59), TAIPEI)


def _fee(sessions: list[dict]) -> str:
    amounts = [int(s["fee"]) for s in sessions if s["fee"].isdigit()]
    if not amounts:
        return "未知"
    return "付費" if any(amounts) else "免費"


def _truncate(text: str) -> str:
    text = " ".join(text.split())
    return text if len(text) <= DESCRIPTION_LIMIT else text[:DESCRIPTION_LIMIT] + "…"


def parse(content: bytes, now: datetime) -> list[Event]:
    raw = json.loads(content)
    details = raw.get("details") or {}
    events, seen = [], set()
    for item in raw.get("items") or []:
        if item["id"] in seen or not item["title"]:
            continue
        detail = details.get(item["id"]) or {}
        sessions = detail.get("sessions") or []
        info = detail.get("info", "")
        span = _span(item, sessions)
        if not span or span[1] < now:
            continue
        seen.add(item["id"])
        place = next((s["place"] for s in sessions if s["place"]), "")
        if not place:
            place = next((m.group(1) for m in map(_PLACE_RE.match, info.splitlines()) if m), "")
        if not place:
            # 附屬館舍的活動標題以館名開頭，如「舊打狗驛故事館-濱濱有旅」
            prefix = item["title"].split("-")[0]
            place = prefix if prefix != item["title"] and district_of(prefix) else ""
        events.append(Event(
            id=f"{NAME}:{item['id']}",
            title=item["title"],
            start=span[0],
            end=span[1],
            venue=place or MUSEUM,
            address="" if place else MUSEUM_ADDRESS,
            district=district_of(place) if place else "鹽埕區",
            category=category_by_keywords(item["title"], default="講座／課程"),
            fee=_fee(sessions),
            organizer=ORGANIZER,
            organizer_type="政府",
            description=_truncate(info),
            links=[Link(source=NAME, url=item["url"])],
        ))
    return events
