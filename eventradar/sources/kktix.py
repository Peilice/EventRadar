"""來源：KKTIX 售票／報名平台。

結合兩個端點：
- api/v2/events：結構化的時間、地址、分類、票種（沒有票價與主辦單位）
- events.json（公開 feed）：主辦單位名稱與摘要，用活動 slug 對應

搜尋「高雄」會混入外縣市場次與辦公室出租廣告，要再過濾。
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timedelta

from .. import http
from ..classify import category_by_keywords, fee_of, mentions_free, organizer_type_of
from ..geo import district_of, is_kaohsiung, is_online
from ..model import TAIPEI, Event, Link

NAME = "kktix"
LABEL = "KKTIX"
API_URL = "https://kktix.com/api/v2/events"
FEED_URL = "https://kktix.com/events.json"
SEARCH = "高雄"
PER_PAGE = 50
MAX_PAGES = 10

CATEGORY_MAP = {2: "講座／課程", 4: "表演／音樂", 11: "展覽", 12: "親子", 5: "運動"}

# 非活動的商業刊登
_NOT_EVENT_RE = re.compile(r"出租|租借|場地租|場租|辦公室|營業登記|設立公司|借址|商務中心|一對一")
# 售票型票種名稱，出現即視為付費
_PAID_TICKET_RE = re.compile(r"預售|全票|早鳥|VIP|搖滾區|座位|優惠票|愛心票|學生票|敬老票|雙人票|套票|現場票", re.IGNORECASE)
MAX_DURATION = timedelta(days=365)
DESCRIPTION_LIMIT = 300


def fetch(previous=None) -> bytes:
    pages = []
    page = 1
    while page <= MAX_PAGES:
        data = http.get(API_URL, params={"search": SEARCH, "page": page, "per_page": PER_PAGE}).json()
        pages.append(data)
        if page >= int(data.get("total_pages") or 1):
            break
        page += 1
    try:
        feed = http.get(FEED_URL, params={"search": SEARCH}).json()
    except Exception:
        feed = {}  # feed 只用來補主辦單位，失敗不影響主要資料
    return json.dumps({"api_pages": pages, "feed": feed}, ensure_ascii=False).encode("utf-8")


def _slug_of(url: str) -> str:
    return url.rstrip("/").rsplit("/", 1)[-1]


def parse(content: bytes, now: datetime) -> list[Event]:
    raw = json.loads(content)
    items = [e for page in raw.get("api_pages", []) for e in page.get("data", [])]
    feed = {_slug_of(e.get("url", "")): e for e in (raw.get("feed") or {}).get("entry", [])}

    # 有子場次出現在結果中的系列活動（CollectionEvent）略過，以子場次為準
    child_parents = {e.get("parent_event_slug") for e in items if e.get("parent_event_slug")}

    events, seen = [], set()
    for item in items:
        if item["slug"] in seen:
            continue
        seen.add(item["slug"])
        if item.get("type") == "CollectionEvent" and item["slug"] in child_parents:
            continue
        event = _parse_item(item, feed.get(item["slug"], {}), now)
        if event:
            events.append(event)
    return events


def _parse_item(item: dict, entry: dict, now: datetime) -> Event | None:
    title = (item.get("name") or "").strip()
    venue = (item.get("location") or "").strip()
    address = (item.get("location_address") or "").strip()
    if not is_kaohsiung(address, venue) or is_online(address, venue):
        return None
    if _NOT_EVENT_RE.search(title):
        return None
    if not item.get("start_at"):
        return None
    start = datetime.fromtimestamp(item["start_at"], TAIPEI)
    end = datetime.fromtimestamp(item.get("end_at") or item["start_at"], TAIPEI)
    if end < now or end - start > MAX_DURATION:
        return None

    tickets = [t.get("name", "") for t in item.get("tickets") or []]
    description = (entry.get("summary") or item.get("description") or "").strip()
    fee = fee_of(*tickets)
    if fee == "未知":
        if mentions_free(title) or any(mentions_free(t) for t in tickets):
            fee = "免費"
        elif any(_PAID_TICKET_RE.search(t) for t in tickets):
            fee = "付費"

    organizer = ((entry.get("author") or {}).get("name") or "").strip()
    category = CATEGORY_MAP.get(item.get("event_category_id")) or category_by_keywords(title)
    if venue == address:
        venue = ""

    return Event(
        id=f"{NAME}:{item['slug']}",
        title=title,
        start=start,
        end=max(start, end),
        venue=venue,
        address=address,
        district=district_of(address, venue),
        category=category,
        fee=fee,
        organizer=organizer,
        organizer_type=organizer_type_of(organizer),
        description=_truncate(description),
        links=[Link(source=NAME, url=entry.get("url") or item.get("url") or "")],
        lat=item.get("geo_lat"),
        lng=item.get("geo_long"),
    )


def _truncate(text: str) -> str:
    text = " ".join(text.split())
    return text if len(text) <= DESCRIPTION_LIMIT else text[:DESCRIPTION_LIMIT] + "…"
