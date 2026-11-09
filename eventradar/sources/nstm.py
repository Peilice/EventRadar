"""來源：國立科學工藝博物館（科工館）的推廣教育活動報名系統與官網展覽列表。

活動：報名系統 serv.nstm.gov.tw/act_query 預設列出今天起約 8 個月的活動，全部在同一頁，
每列有活動期間、時段、名稱、對象、地點、費用，不必抓詳情頁。
特展：官網「展覽資訊」列表（www.nstm.gov.tw/ExhibitionList.aspx）有起訖日期。

官網「活動資訊」是新聞公告列表，日期是發布日、活動時間只寫在內文，
其中的講座與手作活動報名系統都有，所以不收。

已知限制：
- 同一活動拆成多個梯次（「--第3梯」「--上午場」）時，同名同一天的梯次合併成一筆，
  起訖為當天第一梯到最後一梯；不同天的分開
- 標題標「(課程中)」的學期課程已開課、不再收報名，不收
- 常設展與「不定期結束」的體驗設施不收，只收有起訖日期的特展
- 特展的費用列表上沒有，標「未知」
"""

from __future__ import annotations

import html
import json
import re
from datetime import datetime
from datetime import time as dtime

from .. import http
from ..classify import category_by_keywords
from ..geo import district_of
from ..model import TAIPEI, Event, Link

NAME = "nstm"
LABEL = "國立科學工藝博物館"
SERV_BASE = "https://serv.nstm.gov.tw/"
ACT_URL = SERV_BASE + "act_query"
SITE_BASE = "https://www.nstm.gov.tw/"
EXHIBITION_URL = SITE_BASE + "ExhibitionList.aspx?Pindex={page}"
MAX_PAGES = 10
DESCRIPTION_LIMIT = 300
ORGANIZER = "國立科學工藝博物館"
DISTRICT = "三民區"
NORTH = ("國立科學工藝博物館", "高雄市三民區九如一路720號")
SOUTH = ("國立科學工藝博物館南館", "高雄市三民區九如一路797號")

_ROW_RE = re.compile(
    r'_Label2_\d+"[^>]*>(?P<dates>.*?)</span>.*?_Label1_\d+"[^>]*>(?P<times>.*?)</span>.*?'
    r'href="(?P<url>act_detail\.aspx\?act_no=(?P<no>\d+)&amp;act_seq=(?P<seq>\d+))"[^>]*>(?P<name>.*?)</a>.*?'
    r'_Label5_\d+"[^>]*>(?P<audience>.*?)</span>.*?_Label7_\d+"[^>]*>(?P<field>.*?)</span>.*?'
    r'_Label3_\d+"[^>]*>(?P<place>.*?)</span>.*?_Label22_\d+"[^>]*>(?P<fee>.*?)</span>',
    re.S,
)
_EXHIBITION_RE = re.compile(
    r'exhi_word-tit">(?P<title>.*?)</h3>\s*<p>(?P<desc>.*?)</p>.*?展覽日期：</i>(?P<dates>.*?)</span>.*?'
    r'href="/?(?P<url>Exhibition\.aspx\?KeyID=(?P<id>[0-9a-f-]+))"',
    re.S,
)
_ROC_DATE_RE = re.compile(r"(\d{2,3})[/-](\d{1,2})[/-](\d{1,2})")
_CLOCK_RE = re.compile(r"([01]?\d|2[0-3]):([0-5]\d)")
# 名稱後面的梯次標記：「--第3梯」「--僅1梯」「--上午場」「--1/1」「--5梯」，以及名稱內的「(第5梯)」「-第一梯」
_SESSION_SUFFIX_RE = re.compile(r"--\s*(?:第?\s*[\d一二三四五六七八九十]+\s*梯|僅\s*[1一]\s*梯|[上下]午場|\d+(?:/\d+)?)\s*$")
_SESSION_INNER_RE = re.compile(r"\s*[(（]第\s*[\d一二三四五六七八九十]+\s*梯[)）]|-第[\d一二三四五六七八九十]+梯$")
_STATUS_RE = re.compile(r"\s*[(（](?:招生中|課程中)[)）]")
_TERM_CODE_RE = re.compile(r"^\d+-")


def _text(fragment: str) -> str:
    return " ".join(html.unescape(re.sub(r"<[^>]+>", " ", fragment)).split())


def parse_activities(page: str) -> list[dict]:
    return [
        {
            "no": m["no"],
            "seq": m["seq"],
            "url": SERV_BASE + html.unescape(m["url"]),
            "name": _text(m["name"]),
            "dates": _text(m["dates"]),
            "times": _text(m["times"]),
            "audience": _text(m["audience"]),
            "field": _text(m["field"]),
            "place": _text(m["place"]),
            "fee": _text(m["fee"]),
        }
        for m in _ROW_RE.finditer(page)
    ]


def parse_exhibitions(page: str) -> list[dict]:
    return [
        {
            "id": m["id"],
            "url": SITE_BASE + html.unescape(m["url"]),
            "title": _text(m["title"]),
            "description": _text(m["desc"]),
            "dates": _text(m["dates"]),
        }
        for m in _EXHIBITION_RE.finditer(page)
    ]


def fetch(previous=None) -> bytes:
    activities = parse_activities(http.get(ACT_URL).text)
    exhibitions, seen = [], set()
    for page in range(1, MAX_PAGES + 1):
        new = [e for e in parse_exhibitions(http.get(EXHIBITION_URL.format(page=page)).text) if e["id"] not in seen]
        if not new:
            break
        seen.update(e["id"] for e in new)
        exhibitions.extend(new)
    return json.dumps({"activities": activities, "exhibitions": exhibitions}, ensure_ascii=False).encode("utf-8")


def _roc_dates(text: str) -> list[datetime]:
    dates = []
    for y, m, d in _ROC_DATE_RE.findall(text):
        try:
            dates.append(datetime(int(y) + 1911, int(m), int(d), tzinfo=TAIPEI))
        except ValueError:
            pass
    return dates


def _activity_span(row: dict) -> tuple[datetime, datetime] | None:
    dates = _roc_dates(row["dates"])
    if not dates:
        return None
    first, last = dates[0], dates[-1]
    clocks = _CLOCK_RE.findall(row["times"])
    if not clocks:
        return first, datetime.combine(last.date(), dtime(23, 59, 59), TAIPEI)
    start = first.replace(hour=int(clocks[0][0]), minute=int(clocks[0][1]))
    end = last.replace(hour=int(clocks[-1][0]), minute=int(clocks[-1][1]))
    return start, max(start, end)


def _title(name: str) -> str:
    name = _TERM_CODE_RE.sub("", name.strip())
    name = _STATUS_RE.sub("", name)
    name = _SESSION_SUFFIX_RE.sub("", name)
    name = _SESSION_INNER_RE.sub("", name)
    return name.replace("--", "：").strip()


def _site(place: str) -> tuple[str, str, str]:
    """回傳場地、地址、行政區。地點寫了高雄其他地方（校外走讀、營隊）時改用該地點。"""
    if "高雄" in place:
        address = place if re.search(r"[路街道].*號", place) else ""
        return place, address, district_of(place)
    if place[:1] in "(（" and place[-1:] in ")）":
        place = place[1:-1]
    name, address = SOUTH if "南館" in place else NORTH
    place = place.removeprefix("南館").removeprefix("北館").strip()
    return f"{name} {place}".strip(), address, DISTRICT


def _activity_category(text: str) -> str:
    # 報名系統的活動都是課程、手作或講座；關鍵字只用來挑出親子與運動類
    category = category_by_keywords(text)
    return category if category in ("親子", "運動") else "講座／課程"


def _fee(text: str) -> str:
    digits = text.replace(",", "").strip()
    if not digits.isdigit():
        return "未知"
    return "免費" if int(digits) == 0 else "付費"


def _truncate(text: str) -> str:
    text = " ".join(text.split())
    return text if len(text) <= DESCRIPTION_LIMIT else text[:DESCRIPTION_LIMIT] + "…"


def _activity_events(rows: list[dict], now: datetime) -> list[Event]:
    # 同名同一天的梯次合併；保留網站上的順序（依開始日期排列）
    groups: dict[tuple[str, str], list[tuple[dict, datetime, datetime]]] = {}
    for row in rows:
        if "課程中" in row["name"]:
            continue
        span = _activity_span(row)
        title = _title(row["name"])
        if not span or not title:
            continue
        groups.setdefault((title, span[0].date().isoformat()), []).append((row, *span))
    events = []
    for (title, _), sessions in groups.items():
        start = min(s[1] for s in sessions)
        end = max(s[2] for s in sessions)
        if end < now:
            continue
        first = min(sessions, key=lambda s: s[1])[0]
        venue, address, district = _site(first["place"])
        fees = {_fee(s[0]["fee"]) for s in sessions}
        fee = fees.pop() if len(fees) == 1 else ("付費" if "付費" in fees else "未知")
        audience = "、".join(dict.fromkeys(s[0]["audience"] for s in sessions if s[0]["audience"]))
        description = "；".join(part for part in (f"對象：{audience}" if audience else "", f"領域：{first['field']}" if first["field"] else "") if part)
        events.append(Event(
            id=f"{NAME}:{first['no']}-{first['seq']}",
            title=title,
            start=start,
            end=end,
            venue=venue,
            address=address,
            district=district,
            category=_activity_category(f"{title} {audience}"),
            fee=fee,
            organizer=ORGANIZER,
            organizer_type="政府",
            description=description,
            links=[Link(source=NAME, url=first["url"])],
        ))
    return events


def _exhibition_events(items: list[dict], now: datetime) -> list[Event]:
    events = []
    for item in items:
        dates = _roc_dates(item["dates"])
        if len(dates) < 2:  # 常設展、「不定期結束」的設施
            continue
        start = dates[0]
        end = datetime.combine(dates[-1].date(), dtime(23, 59, 59), TAIPEI)
        if end < now or not item["title"]:
            continue
        events.append(Event(
            id=f"{NAME}:{item['id']}",
            title=item["title"],
            start=start,
            end=end,
            venue=NORTH[0],
            address=NORTH[1],
            district=DISTRICT,
            category="展覽",
            fee="未知",
            organizer=ORGANIZER,
            organizer_type="政府",
            description=_truncate(item["description"]),
            links=[Link(source=NAME, url=item["url"])],
        ))
    return events


def parse(content: bytes, now: datetime) -> list[Event]:
    raw = json.loads(content)
    events = _activity_events(raw.get("activities") or [], now) + _exhibition_events(raw.get("exhibitions") or [], now)
    seen, unique = set(), []
    for e in events:
        if e.id not in seen:
            seen.add(e.id)
            unique.append(e)
    return unique
