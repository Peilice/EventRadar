"""來源：台灣市集整合資訊網（twmarket.tw，WordPress REST API 的「高雄市集」分類）。

文章多為市集主辦的攤商招募文，標題格式固定為「2026.10.31~11.29 高雄市-地點-市集名稱」，
內文格式不一，從中盡量讀出場次日期、時間、地址與主辦單位。

一篇文章常涵蓋多個場次（例如每週六日），能讀出場次日期時拆成每天一筆，
讓每個市集日都出現在當天；讀不出場次就以標題的日期範圍當一筆。

已知限制：
- 場次日期是從自由文字推斷，可能漏抓或混入其他日期（只採用標題範圍內的日期）
- 同一市集常被不同人重複貼文，名稱相似且同一天的只留最新一篇
- 標題的地區不含「高雄」的（如「多縣市」）不收
"""

from __future__ import annotations

import html
import json
import re
from datetime import date, datetime, time, timedelta

from .. import http
from ..classify import category_by_keywords, organizer_type_of
from ..dedupe import titles_match
from ..geo import DISTRICTS, district_of
from ..model import TAIPEI, Event, Link

NAME = "twmarket"
LABEL = "台灣市集整合資訊網"
API_URL = "https://www.twmarket.tw/wp-json/wp/v2/posts"
KAOHSIUNG_CATEGORY = 72
PER_PAGE = 100
MAX_PAGES = 5
# 文章多在市集前一兩個月發布，發布超過這麼久的文章不再往回翻
LOOKBACK_DAYS = 180
# 「9/25~9/28」這種短區間視為連續幾天都有場次；更長的區間多半是重述整體檔期，不展開
MAX_EXPAND_DAYS = 4

_TITLE_RE = re.compile(
    r"^\s*(20\d\d)\.(\d{1,2})\.(\d{1,2})"
    r"(?:\s*[~～\-－]\s*(?:(20\d\d)\.)?(\d{1,2})\.(\d{1,2}))?\s*(.*)$"
)
_TITLE_SEP_RE = re.compile(r"\s*[-－]\s*")
# 不是給民眾逛的市集活動
_EXCLUDE_RE = re.compile(r"寄賣|販賣機|黃昏市場|傳統市場|經紀|股份有限公司|說明會")

_WEEKDAY_CHARS = "一二三四五六日"
_SESSION_RE = re.compile(
    # 前面不能是「2026.」「10/」這類日期的一部分，但「１.10/31」這種編號列表要能比對
    r"(?<![0-9/／])(?<![0-9]\.)(?:(20[0-9][0-9])\s*[/.／年]\s*)?([0-9]{1,2})\s*[/.／月]\s*([0-9]{1,2})(?![0-9:])\s*日?"
    r"(?:\s*[（(][一二三四五六日天、,\s]+[)）])?"
    r"(?:\s*[-~～－–至]\s*(?:([0-9]{1,2})\s*[/.／月]\s*)?([0-9]{1,2})(?![0-9:/.／])\s*日?)?"
)
_WEEKLY_RE = re.compile(r"每(?:週|周|星期|個?禮拜)\s*([一二三四五六日天、和及與]+)")
# 沒列出場次、只說「限假日」「每逢週末」時，視為範圍內的每個週六日
_WEEKEND_RE = re.compile(r"假日|週末|周末")
_TIME_RANGE_RE = re.compile(r"(\d{1,2})\s*[:：]\s*(\d{2})\s*[-~～－–—至到]\s*(\d{1,2})\s*[:：]\s*(\d{2})")
# 攤商用的時間，不是民眾逛市集的時間
_SETUP_TIME_RE = re.compile(r"進場|報到|設攤|擺攤|撤場|退場|簽到|佈置|布置|截止|聯絡|客服")
_ADDRESS_RE = re.compile(
    r"(?:高雄市\s*)?(?:" + "|".join(DISTRICTS) + r")區[^\s，,。；;（）()|▹、]{1,30}?號"
    r"|高雄市[^\s，,。；;（）()|▹、]{2,30}?號"
)
_DISTRICT_TAG_RE = re.compile(r"#\s*((?:" + "|".join(DISTRICTS) + r")區)")
_ORGANIZER_RE = re.compile(r"主辦(?:單位)?\s*[▹:：|｜>＞]+\s*([^\n]{2,60})")
_NOT_ORGANIZER_RE = re.compile(r"保留|有權|不負|審核|通知|決定")
_FREE_ENTRY_RE = re.compile(r"免費入場|免門票|免費參觀|自由入場|免費參加")


def fetch(previous=None) -> bytes:
    cutoff = datetime.now(TAIPEI) - timedelta(days=LOOKBACK_DAYS)
    posts = []
    for page in range(1, MAX_PAGES + 1):
        rows = http.get(
            API_URL,
            params={
                "categories": KAOHSIUNG_CATEGORY,
                "per_page": PER_PAGE,
                "page": page,
                "_fields": "id,date,link,title,content",
            },
        ).json()
        if not rows:
            break
        posts += [
            {
                "id": row["id"],
                "date": row.get("date", ""),
                "link": row.get("link", ""),
                "title": html.unescape((row.get("title") or {}).get("rendered", "")),
                "text": _plain_text((row.get("content") or {}).get("rendered", "")),
            }
            for row in rows
        ]
        oldest = min(row.get("date", "") for row in rows)
        if len(rows) < PER_PAGE or oldest < cutoff.strftime("%Y-%m-%d"):
            break
    if not posts:
        raise ValueError("twmarket 沒有回傳任何文章，網站可能改版")
    return json.dumps({"posts": posts}, ensure_ascii=False).encode("utf-8")


def _plain_text(content: str) -> str:
    text = re.sub(r"<br\s*/?>|</(?:p|li|h\d|div)>", "\n", content)
    text = html.unescape(re.sub(r"<[^>]+>", "", text))
    return "\n".join(line.strip() for line in text.splitlines() if line.strip())


def parse_title(title: str) -> dict | None:
    """「2026.10.31~11.29 高雄市-地點-名稱」→ 起訖日、地區、地點、名稱。"""
    m = _TITLE_RE.match(title)
    if not m:
        return None
    y1, m1, d1, y2, m2, d2, rest = m.groups()
    try:
        start = date(int(y1), int(m1), int(d1))
        end = date(int(y2 or y1), int(m2), int(d2)) if d2 else start
    except ValueError:
        return None
    if end < start:  # 「2026.10.09~2026.02.08」這類跨年筆誤，或省略年份的跨年
        end = end.replace(year=end.year + 1)
    parts = _TITLE_SEP_RE.split(rest.strip(), maxsplit=2)
    if len(parts) < 3 or not parts[2]:
        return None
    region, venue, name = parts
    return {"start": start, "end": end, "region": region, "venue": venue, "name": name.strip()}


def _in_range(month: int, day: int, year: int | None, start: date, end: date) -> date | None:
    for y in ([year] if year else [start.year, start.year + 1]):
        try:
            d = date(y, month, day)
        except ValueError:
            continue
        if start <= d <= end:
            return d
    return None


def _dates_in(text: str, start: date, end: date) -> set[date]:
    found: set[date] = set()
    for m in _SESSION_RE.finditer(text):
        year, month, day, end_month, end_day = m.groups()
        first = _in_range(int(month), int(day), int(year) if year else None, start, end)
        if not first:
            continue
        last = None
        if end_day:
            last = _in_range(int(end_month or month), int(end_day), None, first, end)
        if last and (last - first).days > MAX_EXPAND_DAYS:
            continue  # 重述整體檔期，不是場次
        found.update(first + timedelta(days=i) for i in range(((last or first) - first).days + 1))
    return found


def session_dates(text: str, start: date, end: date) -> list[date]:
    """從內文找出落在標題日期範圍內的場次日期。"""
    found = _dates_in(text, start, end)
    weekdays: set[int] = set()
    for m in _WEEKLY_RE.finditer(text):
        weekdays |= {_WEEKDAY_CHARS.index(c) for c in m.group(1).replace("天", "日") if c in _WEEKDAY_CHARS}
    if not weekdays and not found and (end - start).days > MAX_EXPAND_DAYS and _WEEKEND_RE.search(text):
        weekdays = {5, 6}
    d = start
    while weekdays and d <= end:
        if d.weekday() in weekdays:
            found.add(d)
        d += timedelta(days=1)
    return sorted(found)


Hours = tuple[time, time]


def _hours_in(line: str) -> Hours | None:
    m = _TIME_RANGE_RE.search(line)
    if not m:
        return None
    h1, m1, h2, m2 = map(int, m.groups())
    if not (h1 < 24 and h2 <= 24 and m1 < 60 and m2 < 60):
        return None
    t1 = time(h1, m1)
    t2 = time(23, 59, 59) if h2 == 24 else time(h2, m2)
    return (t1, t2) if t2 > t1 else (t1, time(23, 59, 59))


def market_hours(text: str, start: date, end: date) -> tuple[Hours | None, dict[date, Hours]]:
    """市集營業時間：回傳 (整體時間, 各日時間)。

    與日期寫在同一行的時間只套用到那幾天；整體時間先找寫著「時間」的那行。
    進場、報到、聯絡等攤商用的時間都跳過。
    """
    lines = [line for line in text.splitlines() if not _SETUP_TIME_RE.search(line)]
    per_day: dict[date, Hours] = {}
    for line in lines:
        hours = _hours_in(line)
        if hours:
            for d in _dates_in(line, start, end):
                per_day.setdefault(d, hours)
    overall = next(filter(None, map(_hours_in, [l for l in lines if "時間" in l] + lines)), None)
    return overall, per_day


def _organizer(text: str) -> str:
    for m in _ORGANIZER_RE.finditer(text):
        value = m.group(1).strip(" *▹:：|｜")
        if value and not _NOT_ORGANIZER_RE.search(value):
            return value
    return ""


def _venue_key(venue: str) -> str:
    return re.sub(r"[\W_]+|高雄市?|國家藝術文化中心", "", venue)


def _same_market(a: Event, b: Event) -> bool:
    """同一天的兩篇貼文：名稱相似，或地點互相包含，視為同一個市集。"""
    if titles_match(a.title, b.title):
        return True
    va, vb = _venue_key(a.venue), _venue_key(b.venue)
    short, long_ = sorted((va, vb), key=len)
    return len(short) >= 4 and short in long_


def _fmt_day(d: date) -> str:
    return f"{d.month}/{d.day}（{_WEEKDAY_CHARS[d.weekday()]}）"


def _fmt_hours(hours: Hours) -> str:
    return f"{hours[0]:%H:%M}–{hours[1]:%H:%M}"


def _description(sessions: list[date], hours: Hours | None, per_day: dict[date, Hours], address: str) -> str:
    lines = []
    if sessions:
        lines.append("場次：" + "、".join(_fmt_day(d) for d in sessions))
    if per_day and len(set(per_day.values())) > 1:
        lines.append("時間：" + "、".join(f"{_fmt_day(d)} {_fmt_hours(h)}" for d, h in sorted(per_day.items())))
    elif hours or per_day:
        lines.append("時間：" + _fmt_hours(hours or next(iter(per_day.values()))))
    if address:
        lines.append(f"地址：{address}")
    lines.append("資料整理自攤商招募文，實際場次以主辦公告為準。")
    return "\n".join(lines)


def parse(content: bytes, now: datetime) -> list[Event]:
    posts = sorted(json.loads(content).get("posts") or [], key=lambda p: p.get("id", 0), reverse=True)
    events: list[Event] = []
    by_day: dict[date, list[Event]] = {}  # 同來源重複貼文：同一天的同一市集只留最新一篇
    for post in posts:
        for event in _parse_post(post, now):
            day = event.start.date()
            if any(_same_market(event, other) for other in by_day.get(day, [])):
                continue
            by_day.setdefault(day, []).append(event)
            events.append(event)
    return events


def _parse_post(post: dict, now: datetime) -> list[Event]:
    info = parse_title(post.get("title", ""))
    if not info or "高雄" not in info["region"]:
        return []
    if _EXCLUDE_RE.search(info["name"]) or _EXCLUDE_RE.search(info["venue"]):
        return []
    if datetime.combine(info["end"], time(23, 59, 59), TAIPEI) < now:
        return []

    text = post.get("text", "")
    address_match = _ADDRESS_RE.search(text)
    address = address_match.group(0).replace(" ", "") if address_match else ""
    district = district_of(address, info["venue"], " ".join(_DISTRICT_TAG_RE.findall(text)))
    organizer = _organizer(text)
    hours, per_day = market_hours(text, info["start"], info["end"])
    sessions = session_dates(text, info["start"], info["end"])
    name = info["name"]
    common = dict(
        title=name,
        venue=info["venue"],
        address=address,
        district=district,
        category=category_by_keywords(name, default="市集"),
        fee="免費" if _FREE_ENTRY_RE.search(text) else "未知",  # 內文的金額多是攤位費，不能當入場費
        organizer=organizer,
        organizer_type=organizer_type_of(organizer),
        description=_description(sessions, hours, per_day, address),
        links=[Link(source=NAME, url=post.get("link", ""))],
    )

    def span(first: date, last: date) -> tuple[datetime, datetime]:
        t1 = (per_day.get(first) or hours or (time(0, 0),))[0]
        t2 = (per_day.get(last) or hours or (None, time(23, 59, 59)))[1]
        return datetime.combine(first, t1, TAIPEI), datetime.combine(last, t2, TAIPEI)

    if not sessions:
        start, end = span(info["start"], info["end"])
        return [Event(id=f"{NAME}:{post['id']}", start=start, end=end, **common)] if end >= now else []
    events = []
    for d in sessions:
        start, end = span(d, d)
        if end >= now:
            events.append(Event(id=f"{NAME}:{post['id']}:{d:%Y%m%d}", start=start, end=end, **common))
    return events
