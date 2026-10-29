"""來源：拓元售票 tixcraft「節目資訊」列表。

/activity 列出所有售票中的節目（日期、名稱、場館），只取場館在高雄的。
詳情頁有防機器人驗證（回 401），所以只用列表的資料。

已知限制：
- 只有日期沒有時間，視為整天
- 沒有主辦單位與票價；列在拓元上的都是售票活動，費用標「付費」
- 列表頁也擋 GitHub Actions 機房 IP（403），改由本機 runner 抓取，每日更新以 --skip 沿用快取
"""

from __future__ import annotations

import html
import json
import re
from datetime import datetime
from datetime import time as dtime

from .. import http
from ..classify import category_by_keywords
from ..geo import district_of, is_kaohsiung
from ..model import TAIPEI, Event, Link

NAME = "tixcraft"
LABEL = "拓元售票"
BASE = "https://tixcraft.com"
LIST_URL = BASE + "/activity"

_ROW_RE = re.compile(
    r'<div class="text-small date">(.*?)</div>\s*'
    r'<div class="text-bold[^"]*"><a href="(/activity/detail/([^"]+))">(.*?)</a></div>\s*'
    r'<div class="text-small[^"]*">(.*?)</div>',
    re.S,
)
_DATE_RE = re.compile(r"(\d{4})/(\d{1,2})/(\d{1,2})")
# 信用卡、會員預售專區是同一場活動的重複項目
_ZONE_RE = re.compile(r"專區")


def _text(fragment: str) -> str:
    return " ".join(html.unescape(re.sub(r"<[^>]+>", " ", fragment)).split())


def parse_list(page: str) -> list[dict]:
    return [
        {"slug": m.group(3), "url": BASE + m.group(2), "dates": _text(m.group(1)), "title": _text(m.group(4)), "venue": _text(m.group(5))}
        for m in _ROW_RE.finditer(page)
    ]


def fetch(previous=None) -> bytes:
    rows = parse_list(http.get(LIST_URL).text)
    if not rows:
        raise ValueError("拓元節目列表沒有資料，網站可能改版")
    return json.dumps({"rows": rows}, ensure_ascii=False).encode("utf-8")


def parse(content: bytes, now: datetime) -> list[Event]:
    events, seen = [], set()
    for row in json.loads(content).get("rows") or []:
        if row["slug"] in seen or not row["title"] or _ZONE_RE.search(row["title"]):
            continue
        if not is_kaohsiung(row["venue"]):
            continue
        dates = _DATE_RE.findall(row["dates"])
        if not dates:
            continue
        try:
            first = datetime(*map(int, dates[0]), tzinfo=TAIPEI)
            last = datetime(*map(int, dates[-1]), tzinfo=TAIPEI)
        except ValueError:
            continue
        end = datetime.combine(last.date(), dtime(23, 59, 59), TAIPEI)
        if end < now:
            continue
        seen.add(row["slug"])
        events.append(Event(
            id=f"{NAME}:{row['slug']}",
            title=row["title"],
            start=first,
            end=end,
            venue=row["venue"],
            district=district_of(row["venue"]),
            category=category_by_keywords(row["title"], default="表演／音樂"),
            fee="付費",
            links=[Link(source=NAME, url=row["url"])],
        ))
    return events
