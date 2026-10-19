"""來源：高雄旅遊網活動 XML（高雄市政府觀光局）。

資料都在 <Info> 的屬性裡；Description、Website、Charge 實測都是空的或「無」。
"""

from __future__ import annotations

import defusedxml.ElementTree as ET
from datetime import datetime

from .. import http
from ..classify import category_by_keywords, organizer_type_of
from ..geo import district_of, is_kaohsiung
from ..model import Event, Link, parse_local

NAME = "khh_travel"
LABEL = "高雄旅遊網"
URL = "https://khh.travel/zh-tw/OpenData/EventNgisXML"
DETAIL_URL = "https://khh.travel/zh-tw/event/calendardetail/{num}/"


def fetch() -> bytes:
    return http.get(URL).content


def _detail_url(event_id: str) -> str:
    # Id 形如 C2_397000000A_008107，網頁版詳情頁為 calendardetail/8107/
    tail = event_id.rsplit("_", 1)[-1]
    return DETAIL_URL.format(num=int(tail)) if tail.isdigit() else "https://khh.travel/zh-tw/event/calendar/"


def parse(content: bytes, now: datetime) -> list[Event]:
    root = ET.fromstring(content)  # 傳 bytes，讓解析器依 XML 檔頭判斷編碼
    events = []
    for info in root.iter("Info"):
        a = info.attrib
        try:
            start = parse_local(a["Start"])
            end = parse_local(a.get("End") or a["Start"])
        except (KeyError, ValueError):
            continue
        if end < now:
            continue
        address = a.get("Add", "").strip()
        if not is_kaohsiung(address):
            continue
        title = a.get("Name", "").strip()
        organizer = a.get("Org", "").strip()
        description = a.get("Description", "").strip()
        events.append(
            Event(
                id=f"{NAME}:{a['Id']}",
                title=title,
                start=start,
                end=end,
                venue="",
                address=address,
                district=district_of(address),
                category=category_by_keywords(title, default="節慶／觀光"),
                fee="未知",
                organizer=organizer,
                organizer_type=organizer_type_of(organizer),
                description="" if description == "無" else description,
                links=[Link(source=NAME, url=_detail_url(a["Id"]))],
                lat=_float(a.get("Py")),
                lng=_float(a.get("Px")),
            )
        )
    return events


def _float(value: str | None) -> float | None:
    try:
        return float(value) if value else None
    except ValueError:
        return None
