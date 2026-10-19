"""來源：衛武營國家藝術文化中心官網。

使用官網前端呼叫的 /api/programs/list（未公開文件化），分「節目」與「學習推廣」兩類，
另外抓分類與廳院清單把代碼轉成名稱。
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta

from .. import http
from ..classify import category_by_keywords, organizer_type_of
from ..model import TAIPEI, Event, Link

NAME = "weiwuying"
LABEL = "衛武營"
API = "https://www.npac-weiwuying.org/api"
PROGRAM_URL = "https://www.npac-weiwuying.org/programs/{id}"
ORGANIZER = "衛武營國家藝術文化中心"
ADDRESS = "高雄市鳳山區三多一路1號"
DISTRICT = "鳳山區"
CATALOG_TYPES = ["program", "education"]
LOOKAHEAD_DAYS = 365
PAGE_SIZE = 100
MAX_PAGES = 20
DESCRIPTION_LIMIT = 300

PERFORMANCE_CATALOGS = {"音樂", "戲劇", "舞蹈", "馬戲", "歌劇", "音樂劇"}


def fetch(previous=None) -> bytes:
    now = int(datetime.now(TAIPEI).timestamp())
    catalogs = http.get(f"{API}/programcatalogs", params={"page": 1, "size": 0}).json().get("rows", [])
    venues = http.get(f"{API}/venues", params={"page": 1, "size": 0}).json().get("rows", [])
    programs: dict[str, list[dict]] = {}
    for catalog_type in CATALOG_TYPES:
        rows: list[dict] = []
        for page in range(1, MAX_PAGES + 1):
            data = http.get(
                f"{API}/programs/list",
                params={
                    "size": PAGE_SIZE,
                    "start": now,
                    "end": now + LOOKAHEAD_DAYS * 86400,
                    "catalog_type": catalog_type,
                    "page": page,
                    "chineseOnShelf": "true",
                },
            ).json()
            rows += data.get("rows") or []
            if not data.get("rows") or len(rows) >= int(data.get("count") or 0):
                break
        programs[catalog_type] = rows
    return json.dumps(
        {
            "catalogs": {c["_id"]: _zh_name(c) for c in catalogs},
            "venues": {v["_id"]: _zh_name(v) for v in venues},
            "programs": programs,
        },
        ensure_ascii=False,
    ).encode("utf-8")


def _zh_name(row: dict) -> str:
    zh = row.get("chinese")
    if isinstance(zh, str):
        return zh
    return (zh or {}).get("name") or (zh or {}).get("title") or ""


def parse(content: bytes, now: datetime) -> list[Event]:
    raw = json.loads(content)
    catalogs, venues = raw.get("catalogs") or {}, raw.get("venues") or {}
    events, seen = [], set()
    for catalog_type, rows in (raw.get("programs") or {}).items():
        for row in rows:
            if row.get("_id") in seen:
                continue
            seen.add(row.get("_id"))
            event = _parse_row(row, catalog_type, catalogs, venues, now)
            if event:
                events.append(event)
    return events


def _time_range(dt: dict) -> tuple[datetime, datetime] | None:
    if dt.get("type") == "continuous" and dt.get("continuous"):
        c = dt["continuous"]
        if not c.get("start") or not c.get("end"):
            return None
        start = datetime.fromtimestamp(c["start"], TAIPEI)
        end = datetime.fromtimestamp(c["end"], TAIPEI)
        if end.hour == 0 and end.minute == 0:
            end = end.replace(hour=23, minute=59, second=59)  # 結束日當天整天有效
        return start, end
    times = [d["time"] for d in dt.get("discrete") or [] if d.get("time")]
    if not times and dt.get("first"):
        times = [dt["first"]]
    if not times:
        return None
    return datetime.fromtimestamp(min(times), TAIPEI), datetime.fromtimestamp(max(times), TAIPEI)


def _fee(activity: dict) -> str:
    kind = activity.get("type")
    if kind == "free":
        return "免費"
    if kind == "ticket":
        prices = [p for p in (activity.get("ticket") or {}).get("price") or [] if isinstance(p, (int, float))]
        return "免費" if prices and max(prices) == 0 else "付費"
    return "未知"  # signup 等：沒有費用資訊


def _category(title: str, names: list[str], catalog_type: str) -> str:
    if "親子" in names:
        return "親子"
    if "市集" in names:
        return "市集"
    if "展覽" in names:
        return "展覽"
    if PERFORMANCE_CATALOGS & set(names):
        return "表演／音樂"
    if catalog_type == "education":
        return "講座／課程"
    return category_by_keywords(title)


def _parse_row(row: dict, catalog_type: str, catalogs: dict, venues: dict, now: datetime) -> Event | None:
    zh = row.get("chinese") or {}
    title = (zh.get("title") or "").strip()
    if not title or zh.get("onShelf") is False:
        return None
    span = _time_range(row.get("dateTime") or {})
    if not span:
        return None
    start, end = span
    if end < now or end - start > timedelta(days=LOOKAHEAD_DAYS * 2):
        return None

    site = zh.get("site") or {}
    hall = (site.get("other") if site.get("isOther") else venues.get(site.get("site"), "")) or ""
    hall = hall.strip()
    venue = hall if hall.startswith("衛武營") else f"衛武營 {hall}".strip()
    organizer = ORGANIZER if row.get("host") else ""
    names = [catalogs.get(c, "") for c in row.get("catalogs") or []]

    return Event(
        id=f"{NAME}:{row['_id']}",
        title=title,
        start=start,
        end=max(start, end),
        venue=venue,
        address=ADDRESS,
        district=DISTRICT,
        category=_category(title, names, catalog_type),
        fee=_fee(row.get("activity") or {}),
        organizer=organizer,
        organizer_type=organizer_type_of(organizer),
        description=_truncate(zh.get("description") or ""),
        links=[Link(source=NAME, url=PROGRAM_URL.format(id=row["_id"]))],
    )


def _truncate(text: str) -> str:
    text = " ".join(text.split())
    return text if len(text) <= DESCRIPTION_LIMIT else text[:DESCRIPTION_LIMIT] + "…"
