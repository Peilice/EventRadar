"""來源：OPENTIX 兩廳院文化生活（網站前端的搜尋 API）。

search.opentix.life/search 以城市「高雄」篩選，每次回傳 15 個節目，用 offset 翻頁。
每個節目的 eventVenues 列出各場館的城市、名稱與場次（起訖時間、票價），只取高雄的場館，
同一場館同一天的場次合併成一筆。

已知限制：
- 沒有地址，行政區由場館名稱比對地標判斷
- 搜尋 API 不是公開文件化的 API，網站改版時可能失效
- 衛武營的節目也在 OPENTIX 上，與衛武營來源重複的部分由去重合併
"""

from __future__ import annotations

import json
import re
from datetime import datetime

from curl_cffi import requests

from .. import http
from ..classify import category_by_keywords, organizer_type_of
from ..geo import district_of
from ..model import TAIPEI, Event, Link

NAME = "opentix"
LABEL = "OPENTIX"
SEARCH_URL = "https://search.opentix.life/search"
EVENT_URL = "https://www.opentix.life/event/{id}"
CITY = "高雄"
MAX_PAGES = 60
DESCRIPTION_LIMIT = 300
_HEADERS = {"Origin": "https://www.opentix.life", "Referer": "https://www.opentix.life/", "Accept-Language": "zh-TW"}

CATEGORY_MAP = {"音樂": "表演／音樂", "戲劇": "表演／音樂", "舞蹈": "表演／音樂", "親子": "親子", "展覽": "展覽", "活動/學習": "講座／課程"}
# 工程師測試用的假節目、票券專區頁，不是活動
_NOT_EVENT_RE = re.compile(r"工程師專用|非正式節目")
_ZONE_RE = re.compile(r"專區$")


def _search(offset: int) -> dict:
    body = {"language": "zh-CHT", "cityFilter": [CITY]}
    if offset:
        body["offset"] = offset
    last_error: Exception | None = None
    for _ in range(3):
        try:
            resp = requests.post(SEARCH_URL, json=body, timeout=60, impersonate=http.IMPERSONATE, headers=_HEADERS)
            resp.raise_for_status()
            return resp.json()["result"]
        except Exception as e:
            last_error = e
    assert last_error is not None
    raise last_error


def _slim(source: dict) -> dict:
    """只留解析用得到的欄位，場館只留高雄。"""
    return {
        "id": source.get("id"),
        "title": source.get("title", ""),
        "displayCategory": source.get("displayCategory", ""),
        "organizers": source.get("organizers", ""),
        "description": (source.get("description") or "")[:DESCRIPTION_LIMIT * 2],
        "eventVenues": [v for v in source.get("eventVenues") or [] if v.get("city") == CITY],
    }


def fetch(previous=None) -> bytes:
    programs = []
    for _ in range(MAX_PAGES):
        result = _search(len(programs))
        found = result.get("found") or []
        if not found:
            break
        programs.extend(_slim(f.get("source") or {}) for f in found)
        if len(programs) >= result.get("hitsCount", 0):
            break
    return json.dumps({"programs": programs}, ensure_ascii=False).encode("utf-8")


def _fee(times: list[dict]) -> str:
    if any((t.get("minPrice") or 0) > 0 for t in times):
        return "付費"
    if times and all((t.get("maxPrice") or 0) == 0 for t in times):
        return "免費"
    return "未知"


def _truncate(text: str) -> str:
    text = " ".join(text.split())
    return text if len(text) <= DESCRIPTION_LIMIT else text[:DESCRIPTION_LIMIT] + "…"


def parse(content: bytes, now: datetime) -> list[Event]:
    events, seen = [], set()
    for program in json.loads(content).get("programs") or []:
        title = " ".join((program.get("title") or "").split())
        description = program.get("description") or ""
        if not title or _ZONE_RE.search(title) or _NOT_EVENT_RE.search(description):
            continue
        category = CATEGORY_MAP.get(program.get("displayCategory")) or category_by_keywords(title, default="表演／音樂")
        organizer = program.get("organizers") or ""
        for venue in program.get("eventVenues") or []:
            days: dict = {}
            for t in venue.get("times") or []:
                start = datetime.fromtimestamp(t["start"] / 1000, TAIPEI)
                end = datetime.fromtimestamp(t["end"] / 1000, TAIPEI)
                days.setdefault(start.date(), []).append((start, end, t))
            for day, sessions in sorted(days.items()):
                start = min(s for s, _, _ in sessions)
                end = max(max(e, s) for s, e, _ in sessions)
                event_id = f"{NAME}:{program['id']}:{day:%Y%m%d}"
                if end < now or event_id in seen:
                    continue
                seen.add(event_id)
                name = venue.get("name", "")
                events.append(Event(
                    id=event_id,
                    title=title,
                    start=start,
                    end=end,
                    venue=name,
                    district=district_of(name),
                    category=category,
                    fee=_fee([t for _, _, t in sessions]),
                    organizer=organizer,
                    organizer_type=organizer_type_of(organizer),
                    description=_truncate(description),
                    links=[Link(source=NAME, url=EVENT_URL.format(id=program["id"]))],
                    lat=_float((venue.get("location") or {}).get("lat")),
                    lng=_float((venue.get("location") or {}).get("lon")),
                ))
    return events


def _float(value) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
