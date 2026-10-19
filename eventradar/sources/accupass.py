"""來源：Accupass 活動通。

- 列表：api.accupass.com/v3/search/SearchEvents（網站前端使用的 API），
  篩「高雄（城市代碼 12）+ 實體活動」，並分免費、付費各查一次，費用直接採用
- 詳情：活動頁裡的 schema.org JSON-LD，取場地、地址、主辦單位、簡介

列表只有城市名稱，地址要開詳情頁才有；為減少請求，上次已抓過詳情的活動直接沿用。
"""

from __future__ import annotations

import json
import re
import time
from datetime import datetime, timedelta

from .. import http
from ..classify import category_by_keywords, organizer_type_of
from ..geo import district_of
from ..model import TAIPEI, Event, Link

NAME = "accupass"
LABEL = "Accupass 活動通"
SEARCH_URL = "https://api.accupass.com/v3/search/SearchEvents"
EVENT_URL = "https://www.accupass.com/event/{id}"

KAOHSIUNG_CITY_CODE = "12"
OFFLINE_PLACE_TYPE = "1"
PRICE_TYPES = {"免費": "1", "付費": "2"}

# Accupass 分類代碼 → 統一分類。一個活動可能有多個分類，依此順序取第一個對得到的
CATEGORY_MAP = {
    "15": "親子",  # family
    "22": "表演／音樂",  # music
    "23": "表演／音樂",  # film
    "6": "表演／音樂",  # entertainment
    "3": "運動",  # sports
    "4": "節慶／觀光",  # travel
    "1": "展覽",  # arts
    "7": "講座／課程",  # learning
    "5": "講座／課程",  # technology
    "11": "講座／課程",  # business
    "17": "講座／課程",  # startup
    "18": "講座／課程",  # investment
    "14": "講座／課程",  # blockchain
    "12": "講座／課程",  # health
    "19": "講座／課程",  # design
    "10": "講座／課程",  # photography
    "20": "講座／課程",  # handmade（手作課）
    "2": "其他",  # food
    "8": "其他",  # fashion
    "9": "其他",  # charitable
    "16": "其他",  # pet
    "21": "其他",  # game
}
MAX_PAGES = 40  # 每頁 25 筆
MAX_NEW_DETAILS = 400
DETAIL_DELAY = 0.5  # 秒，抓詳情頁之間的間隔
MAX_DURATION = timedelta(days=365)
DESCRIPTION_LIMIT = 300

_LD_RE = re.compile(r'<script type="application/ld\+json">(.*?)</script>', re.S)


def _search(price_type: str | None, index: int, category: str | None = None) -> dict:
    body = {
        "categoryTypeList": [category] if category else [],
        "simpleEventPlaceTypeList": [OFFLINE_PLACE_TYPE],
        "cityLocationList": [KAOHSIUNG_CITY_CODE],
        "sortBy": None,
        "startTime": None,
        "endTime": None,
        "ticketPriceType": price_type,
        "timeType": None,
        "keyword": "",
        "currentIndex": index,
    }
    return http.post_json(SEARCH_URL, body)


def _fetch_detail(event_id: str) -> dict | None:
    html = http.get(EVENT_URL.format(id=event_id)).text
    for block in _LD_RE.findall(html):
        try:
            data = json.loads(block)
        except json.JSONDecodeError:
            continue
        if isinstance(data, dict) and data.get("@type") == "Event":
            return data
    return None


def _detail_from_event(e: Event) -> dict:
    """把上次解析好的活動轉回 JSON-LD 的形狀，讓 parse 只需處理一種格式。"""
    return {
        "location": {"name": e.venue, "address": e.address},
        "organizer": {"name": e.organizer},
        "description": e.description,
    }


def _search_all(price_type: str | None, category: str | None = None) -> list[dict]:
    items: list[dict] = []
    for index in range(MAX_PAGES):
        page = _search(price_type, index, category)
        items += page.get("items") or []
        if not page.get("items") or len(items) >= int(page.get("total") or 0):
            break
    return items


def fetch(previous: list[Event] | None = None) -> bytes:
    lists = {fee: _search_all(code) for fee, code in PRICE_TYPES.items()}

    # 列表沒有分類欄位，改為逐一分類查詢，記下每個活動屬於哪些分類
    categories: dict[str, list[str]] = {}
    for code in CATEGORY_MAP:
        for item in _search_all(None, code):
            categories.setdefault(item["eventIdNumber"], []).append(code)

    known = {e.id.split(":", 1)[1]: e for e in previous or [] if e.address or e.venue}
    details: dict[str, dict | None] = {}
    fetched = 0
    for item in (i for items in lists.values() for i in items):
        event_id = item["eventIdNumber"]
        if event_id in details:
            continue
        if event_id in known:
            details[event_id] = _detail_from_event(known[event_id])
        elif fetched < MAX_NEW_DETAILS:
            try:
                details[event_id] = _fetch_detail(event_id)
            except Exception:
                details[event_id] = None  # 單頁失敗就只用列表資料
            fetched += 1
            time.sleep(DETAIL_DELAY)
    return json.dumps(
        {"lists": lists, "categories": categories, "details": details}, ensure_ascii=False
    ).encode("utf-8")


def _parse_time(text: str) -> datetime:
    # 列表時間為 UTC，例如 2026-10-23T11:30:00Z
    dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=TAIPEI)
    return dt.astimezone(TAIPEI)


def parse(content: bytes, now: datetime) -> list[Event]:
    raw = json.loads(content)
    details = raw.get("details") or {}
    categories = raw.get("categories") or {}
    events, seen = [], set()
    for fee, items in (raw.get("lists") or {}).items():
        for item in items:
            event_id = item.get("eventIdNumber")
            if not event_id or event_id in seen:
                continue
            seen.add(event_id)
            event = _parse_item(item, details.get(event_id) or {}, categories.get(event_id) or [], fee, now)
            if event:
                events.append(event)
    return events


def _category(title: str, tags: str, codes: list[str]) -> str:
    """標題關鍵字優先；對不到再用 Accupass 分類。"""
    by_keyword = category_by_keywords(f"{title} {tags}")
    if by_keyword != "其他":
        return by_keyword
    return next((CATEGORY_MAP[c] for c in CATEGORY_MAP if c in codes), "其他")


def _parse_item(item: dict, detail: dict, codes: list[str], fee: str, now: datetime) -> Event | None:
    if item.get("eventPlaceType") != "Offline" or item.get("location") != "Kaohsiung City":
        return None
    try:
        start = _parse_time(item["startDateTime"])
        end = _parse_time(item.get("endDateTime") or item["startDateTime"])
    except (KeyError, ValueError):
        return None
    if end < now or end - start > MAX_DURATION:
        return None

    title = (item.get("name") or "").strip()
    location = detail.get("location") or {}
    venue = (location.get("name") or "").strip()
    address = " ".join((location.get("address") or "").split())
    organizer = ((detail.get("organizer") or {}).get("name") or "").strip()
    tags = " ".join(t.get("name", "") for t in item.get("tags") or [])

    return Event(
        id=f"{NAME}:{item['eventIdNumber']}",
        title=title,
        start=start,
        end=max(start, end),
        venue=venue,
        address=address,
        district=district_of(address, venue),
        category=_category(title, tags, codes),
        fee=fee,
        organizer=organizer,
        organizer_type=organizer_type_of(organizer),
        description=_truncate(detail.get("description") or ""),
        links=[Link(source=NAME, url=EVENT_URL.format(id=item["eventIdNumber"]))],
    )


def _truncate(text: str) -> str:
    text = " ".join(text.split())
    return text if len(text) <= DESCRIPTION_LIMIT else text[:DESCRIPTION_LIMIT] + "…"
