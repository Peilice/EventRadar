"""來源：高雄市立美術館官網「活動資訊」。

列表（當期活動，約 2 頁）有標題與起訖日期；地點（本館／兒美館／園區）與內文要讀詳情頁。
活動數量不多，每次都重抓全部詳情頁。

已知限制：
- 時間只從標題讀（如「11/1(日) 14:00 高美講堂」），沒有結束時間時結束時間視同開始時間；
  標題沒寫時間的活動視為整天
- 費用只看內文中提到票價、報名費、免費的行，判斷不出來標「未知」
- 徵件、訂閱優惠、團體洽詢合作這類不是活動的項目不收
"""

from __future__ import annotations

import html
import json
import re
import time
from datetime import datetime
from datetime import time as dtime

from .. import http
from ..classify import category_by_keywords, fee_of
from ..model import TAIPEI, Event, Link

NAME = "kmfa"
LABEL = "高雄市立美術館"
BASE = "https://www.kmfa.gov.tw/"
LIST_URL = BASE + "OnlineApplyListC001200.aspx?PIndex={page}"
MAX_PAGES = 10
DETAIL_DELAY = 0.5
DESCRIPTION_LIMIT = 300
ORGANIZER = "高雄市立美術館"
DISTRICT = "鼓山區"

# 詳情頁地點的第一個詞：場館名稱與地址
SITES = {
    "本館": ("高雄市立美術館", "高雄市鼓山區美術館路80號"),
    "園區": ("高雄市立美術館園區", "高雄市鼓山區美術館路80號"),
    "兒美館": ("高雄兒童美術館", "高雄市鼓山區馬卡道路330號"),
}
_NOT_EVENT_RE = re.compile(r"徵件|訂閱|訂戶|來信洽詢")
_FEE_LINE_RE = re.compile(r"票價|報名費|參加費|材料費|免費")

_ITEM_RE = re.compile(
    r'<a href="/?(OnlineApplyDetailC001200\.aspx\?Cond=([0-9a-f-]+))"[^>]*class="exhibition_item".*?'
    r'<h4 class="exhibition_title">(.*?)</h4>\s*<span class="exhibition_date">(.*?)</span>',
    re.S,
)
_DATE_RE = re.compile(r"(\d{4})/(\d{1,2})/(\d{1,2})")
_CLOCK_RE = re.compile(r"(?<![\d/])([01]?\d|2[0-3]):([0-5]\d)")


def _text(fragment: str) -> str:
    return " ".join(html.unescape(re.sub(r"<[^>]+>", " ", fragment)).split())


def parse_list(page: str) -> list[dict]:
    return [
        {"id": m.group(2), "url": BASE + html.unescape(m.group(1)), "title": _text(m.group(3)), "dates": _text(m.group(4))}
        for m in _ITEM_RE.finditer(page)
    ]


def parse_detail(page: str) -> dict:
    site = re.search(r'<span class="exhibitionIn_site">(.*?)</span>', page, re.S)
    start = page.find('class="exhibitionIn_content')
    end = page.find("<!--報名資訊", start)
    content = page[start:end] if start >= 0 else ""
    content = content[content.find(">") + 1:]
    lines = [_text(s) for s in re.split(r"<(?:br|p|div|li|tr|h\d)[^>]*>", content)]
    return {"site": _text(site.group(1)) if site else "", "content": "\n".join(s for s in lines if s)}


def fetch(previous=None) -> bytes:
    items, seen = [], set()
    for page in range(1, MAX_PAGES + 1):
        new = [i for i in parse_list(http.get(LIST_URL.format(page=page)).text) if i["id"] not in seen]
        # 超過最後一頁時網站會回傳第一頁
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


def _span(item: dict) -> tuple[datetime, datetime] | None:
    dates = _DATE_RE.findall(item["dates"])
    if not dates:
        return None
    try:
        first = datetime(*map(int, dates[0]), tzinfo=TAIPEI)
        last = datetime(*map(int, dates[-1]), tzinfo=TAIPEI)
    except ValueError:
        return None
    clock = _CLOCK_RE.search(item["title"])
    if clock and first.date() == last.date():
        start = first.replace(hour=int(clock.group(1)), minute=int(clock.group(2)))
        return start, start
    return first, datetime.combine(last.date(), dtime(23, 59, 59), TAIPEI)


def _site(text: str) -> tuple[str, str]:
    key, _, rest = text.partition(" ")
    if "高雄市" in rest:  # 兒美館的地點後面接的是地址
        rest = ""
    if key in SITES:
        name, address = SITES[key]
        return f"{name} {rest}".strip(), address
    name, address = SITES["本館"]
    return f"{name} {text}".strip(), address


def _truncate(text: str) -> str:
    text = " ".join(text.split())
    return text if len(text) <= DESCRIPTION_LIMIT else text[:DESCRIPTION_LIMIT] + "…"


def parse(content: bytes, now: datetime) -> list[Event]:
    raw = json.loads(content)
    details = raw.get("details") or {}
    events, seen = [], set()
    for item in raw.get("items") or []:
        if item["id"] in seen or not item["title"] or _NOT_EVENT_RE.search(item["title"]):
            continue
        span = _span(item)
        if not span or span[1] < now:
            continue
        seen.add(item["id"])
        detail = details.get(item["id"]) or {}
        body = detail.get("content", "")
        venue, address = _site(detail.get("site", ""))
        fee_lines = [line for line in body.splitlines() if _FEE_LINE_RE.search(line)]
        events.append(Event(
            id=f"{NAME}:{item['id']}",
            title=item["title"],
            start=span[0],
            end=span[1],
            venue=venue,
            address=address,
            district=DISTRICT,
            category=category_by_keywords(item["title"], default="講座／課程"),
            fee=fee_of(*fee_lines),
            organizer=ORGANIZER,
            organizer_type="政府",
            description=_truncate(body),
            links=[Link(source=NAME, url=item["url"])],
        ))
    return events
