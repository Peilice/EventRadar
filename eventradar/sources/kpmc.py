"""來源：高雄流行音樂中心（高流）官網。

節目清單直接嵌在 /program/ 頁面的 `var items = {...}`（依月份分組），每個節目只有開始時間。
主辦單位與票價要讀節目詳情頁；上次已讀過的節目沿用舊資料，不重抓。

已知限制：
- 沒有結束時間，結束時間視同開始時間
- 開始時間已過的節目（多為進行中的展覽）無法判斷是否還在進行，一律不收
"""

from __future__ import annotations

import html
import json
import re
import time
from datetime import datetime

from .. import http
from ..classify import category_by_keywords, fee_of, mentions_free, organizer_type_of
from ..model import TAIPEI, Event, Link

NAME = "kpmc"
LABEL = "高雄流行音樂中心"
LIST_URL = "https://kpmc.com.tw/program/"
ADDRESS = "高雄市鹽埕區真愛路1號"
DISTRICT = "鹽埕區"
# 鯨魚堤岸在愛河對岸，屬苓雅區
WHALE_ADDRESS = "高雄市苓雅區海邊路"
WHALE_DISTRICT = "苓雅區"
_AMOUNT_RE = re.compile(r"\d[\d,]*")
DETAIL_DELAY = 0.5
MAX_NEW_DETAILS = 120

CATEGORY_MAP = {134: "表演／音樂", 136: "展覽", 401: "市集", 140: "講座／課程"}
_ANNOUNCEMENT_RE = re.compile(r"節目總表|公告")
_ITEMS_RE = re.compile(r"var\s+items\s*=\s*")
_DATE_RE = re.compile(r"(\d{1,2})\.(\d{1,2}).*?(\d{1,2}):(\d{2})")


def _list_items(page: str) -> list[dict]:
    m = _ITEMS_RE.search(page)
    if not m:
        raise ValueError("找不到 var items，高流網站可能改版")
    data = json.JSONDecoder().raw_decode(page[m.end():])[0]
    months = data.values() if isinstance(data, dict) else [data]
    return [item for month in months if month for item in month]


def _segments(page: str) -> list[str]:
    text = re.sub(r"<script.*?</script>|<style.*?</style>", "", page, flags=re.S)
    return [html.unescape(s).strip() for s in re.split(r"<[^>]+>", text) if s.strip()]


def parse_detail(page: str) -> dict:
    """從詳情頁讀出主辦單位與票價文字。"""
    seg = _segments(page)
    organizer, prices = "", []
    if "主辦單位" in seg:
        i = seg.index("主辦單位")
        organizer = seg[i + 1] if i + 1 < len(seg) and seg[i + 1] != "票價資訊" else ""
    if "票價資訊" in seg:
        for s in seg[seg.index("票價資訊") + 1:]:
            if s.startswith("將此活動加入") or s in ("share:", "前往購票"):
                break
            prices.append(s)
    return {"organizer": organizer, "price": " ".join(prices)}


def fetch(previous=None) -> bytes:
    items = [i for i in _list_items(http.get(LIST_URL).text) if not _ANNOUNCEMENT_RE.search(i.get("desc", ""))]
    known = {
        e.links[0].url: {"organizer": e.organizer, "price": _price_from_description(e.description)}
        for e in previous or []
        if e.links
    }
    details, fetched = {}, 0
    for item in items:
        link = item.get("link", "")
        if link in details:
            continue
        if link in known:
            details[link] = known[link]
        elif fetched < MAX_NEW_DETAILS:
            try:
                details[link] = parse_detail(http.get(link).text)
            except Exception:
                details[link] = {}
            fetched += 1
            time.sleep(DETAIL_DELAY)
    return json.dumps({"items": items, "details": details}, ensure_ascii=False).encode("utf-8")


_PRICE_PREFIX = "票價："


def _description(performer: str, price: str) -> str:
    parts = []
    if performer:
        parts.append(f"演出：{performer}")
    if price:
        parts.append(f"{_PRICE_PREFIX}{price}")
    return "\n".join(parts)


def _price_from_description(description: str) -> str:
    for line in description.splitlines():
        if line.startswith(_PRICE_PREFIX):
            return line[len(_PRICE_PREFIX):]
    return ""


def parse(content: bytes, now: datetime) -> list[Event]:
    raw = json.loads(content)
    details = raw.get("details") or {}
    events, seen = [], set()
    for item in raw.get("items") or []:
        if item.get("id") in seen or _ANNOUNCEMENT_RE.search(item.get("desc", "")):
            continue
        seen.add(item.get("id"))
        event = _parse_item(item, details.get(item.get("link", "")) or {}, now)
        if event:
            events.append(event)
    return events


def _parse_item(item: dict, detail: dict, now: datetime) -> Event | None:
    m = _DATE_RE.search(item.get("date_time", ""))
    if not m or not str(item.get("year", "")).isdigit():
        return None
    month, day, hour, minute = map(int, m.groups())
    try:
        start = datetime(int(item["year"]), month, day, hour, minute, tzinfo=TAIPEI)
    except ValueError:
        return None
    if start < now:
        return None

    title = " ".join(html.unescape(item.get("desc", "")).split())
    location = html.unescape(item.get("location") or "").strip()
    venue = location if location.startswith("高雄流行音樂中心") else f"高雄流行音樂中心 {location}".strip()
    organizer = detail.get("organizer", "")
    price = detail.get("price", "")
    fee = fee_of(price)
    if fee == "未知":
        # 票價欄位專門寫票價，有大於 0 的數字即為付費
        if any(int(a.replace(",", "") or 0) > 0 for a in _AMOUNT_RE.findall(price)):
            fee = "付費"
        elif mentions_free(price):
            fee = "免費"
    whale = "鯨魚堤岸" in location
    category = CATEGORY_MAP.get(item.get("show_category")) or category_by_keywords(title)
    performer = html.unescape(item.get("performer") or "").strip()

    return Event(
        id=f"{NAME}:{item['id']}",
        title=title,
        start=start,
        end=start,
        venue=venue,
        address=WHALE_ADDRESS if whale else ADDRESS,
        district=WHALE_DISTRICT if whale else DISTRICT,
        category=category,
        fee=fee,
        organizer=organizer,
        organizer_type=organizer_type_of(organizer),
        # 票價放在簡介中，下次執行可從這裡讀回，不必重抓詳情頁
        description=_description(performer, price),
        links=[Link(source=NAME, url=item.get("link", ""))],
    ) if title else None
