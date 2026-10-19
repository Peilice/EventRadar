"""來源：文化部 iCulture 藝文活動 API（全國，篩出有高雄場次的活動）。

一筆活動的 showInfo 可能含多個城市的場次，只保留高雄的場次計算起訖與場地。
"""

from __future__ import annotations

import json
from urllib.parse import urlsplit
from datetime import datetime

from .. import http
from ..classify import category_by_keywords, fee_of, mentions_free, organizer_type_of
from ..geo import district_of, is_kaohsiung, is_online
from ..model import Event, Link, parse_local

NAME = "iculture"
LABEL = "文化部藝文活動"
URL = "https://cloud.culture.tw/frontsite/trans/SearchShowAction.do"
DETAIL_URL = "https://cloud.culture.tw/frontsite/inquiry/eventInquiryAction.do?method=showEventDetail&uid={uid}"

# iCulture 類別代碼 → 統一分類；None 表示改用關鍵字判斷
CATEGORY_MAP = {
    "1": "表演／音樂",  # 音樂
    "2": "表演／音樂",  # 戲劇
    "3": "表演／音樂",  # 舞蹈
    "4": "親子",
    "5": "表演／音樂",  # 獨立音樂
    "6": "展覽",
    "7": "講座／課程",  # 講座
    "8": "表演／音樂",  # 電影
    "11": "表演／音樂",  # 綜藝
    "17": "表演／音樂",  # 演唱會
    "19": "講座／課程",  # 研習課程
    "200": "講座／課程",  # 閱讀
}

DESCRIPTION_LIMIT = 300


def fetch() -> bytes:
    return http.get(URL, params={"method": "doFindTypeJ", "category": "all"}, timeout=120).content


def parse(content: bytes, now: datetime) -> list[Event]:
    events = []
    for item in json.loads(content):
        event = _parse_item(item, now)
        if event:
            events.append(event)
    return events


def _parse_item(item: dict, now: datetime) -> Event | None:
    shows = [
        s
        for s in item.get("showInfo") or []
        if is_kaohsiung(s.get("location", ""), s.get("locationName", ""))
        and not is_online(s.get("location", ""), s.get("locationName", ""))
    ]
    if not shows:
        return None

    starts, ends = [], []
    for s in shows:
        try:
            start = parse_local(s["time"])
        except (KeyError, ValueError):
            continue
        try:
            end = parse_local(s["endTime"]) if s.get("endTime") else start
        except ValueError:
            end = start
        starts.append(start)
        ends.append(max(start, end))
    if not starts:
        return None
    start, end = min(starts), max(ends)
    if end < now:
        return None

    title = (item.get("title") or "").strip()
    description = (item.get("descriptionFilterHtml") or "").strip()
    organizer = "、".join(u.strip() for u in item.get("masterUnit") or [] if u.strip())
    venues = list(dict.fromkeys(s.get("locationName", "").strip() for s in shows if s.get("locationName")))
    address = shows[0].get("location", "").strip()

    fee = fee_of(*(s.get("price", "") for s in shows))
    if fee == "未知":
        if mentions_free(title) or mentions_free(description):
            fee = "免費"
        elif any(s.get("onSales") == "Y" for s in shows):
            fee = "付費"

    category = CATEGORY_MAP.get(str(item.get("category"))) or category_by_keywords(title)
    url = next(
        (u.strip() for u in (item.get("sourceWebPromote"), item.get("webSales")) if _is_specific_url(u)),
        DETAIL_URL.format(uid=item["UID"]),
    )

    return Event(
        id=f"{NAME}:{item['UID']}",
        title=title,
        start=start,
        end=end,
        venue=_join_venues(venues),
        address=address,
        district=district_of(address, *venues),
        category=category,
        fee=fee,
        organizer=organizer,
        organizer_type=organizer_type_of(organizer),
        description=_truncate(description),
        links=[Link(source=NAME, url=url.strip())],
        lat=_float(shows[0].get("latitude")),
        lng=_float(shows[0].get("longitude")),
    )


def _is_specific_url(url: str | None) -> bool:
    """排除只有網域的網址（例如 https://kktix.com/），那種連結點了找不到活動。"""
    if not url or not url.strip().startswith("http"):
        return False
    return urlsplit(url.strip()).path.strip("/") != ""


def _join_venues(venues: list[str]) -> str:
    if len(venues) <= 3:
        return "、".join(venues)
    return "、".join(venues[:3]) + f" 等 {len(venues)} 處"


def _truncate(text: str) -> str:
    text = " ".join(text.split())
    return text if len(text) <= DESCRIPTION_LIMIT else text[:DESCRIPTION_LIMIT] + "…"


def _float(value) -> float | None:
    try:
        return float(value) if value else None
    except (TypeError, ValueError):
        return None
