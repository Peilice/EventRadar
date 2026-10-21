"""來源：高雄市立圖書館官網「最新活動」。

列表只取「活動」類（排除公告），共約 6 頁：第一頁是卡片版面，之後是表格版面，
兩者都有「活動日期」欄，但這欄只有一天（多為開始日）且常空白。
活動時間、地點、費用都寫在詳情頁內文裡，格式各館不一，從「時間：」「地點：」這類行讀出。
每次都重抓全部詳情頁（約 100 頁）：判斷時間需要內文，舊結果裡沒有存。

已知限制：
- 一篇公告含多個場次（系列講座、每週課程）時合併成一筆，起訖為第一場到最後一場
- 只寫在表格或圖片裡的場次讀不到，只能用列表的活動日期當作單日活動
- 館外活動（走讀）只寫集合地點時，行政區常判斷不出來
"""

from __future__ import annotations

import html
import json
import re
import time
from datetime import date, datetime, timedelta
from datetime import time as dtime

from .. import http
from ..classify import category_by_keywords, fee_of
from ..geo import district_of
from ..model import TAIPEI, Event, Link

NAME = "ksml"
LABEL = "高雄市立圖書館"
BASE = "https://www.ksml.edu.tw/LibNews/"
LIST_URL = BASE + "List.aspx?Parser=9,4,33,,,,,,,,{page},1"  # 最後的 1 = 只取「活動」類
DETAIL_URL = BASE + "Details.aspx?Parser=9,4,33,,,,{id}"
MAX_PAGES = 20
DETAIL_DELAY = 0.5
LIBRARY = "高雄市立圖書館"
# 內文的日期離開始日太遠，多半是筆誤（例如 115 寫成 117）
MAX_SPAN = timedelta(days=400)

# 分館名錄（官網「認識本館 > 分館名錄」，2026-10-21）
BRANCHES = {
    "總館": "前鎮區新光路61號",
    "高雄文學館": "前金區民生二路39號",
    "李科永紀念圖書館": "前金區民生二路37號",
    "鼓山分館": "鼓山區鼓山三路19-3號",
    "旗津分館": "旗津區中洲三路528號",
    "右昌分館": "楠梓區藍昌路72號",
    "左營分館": "左營區啟文路12號",
    "三民分館": "三民區十全一路220號",
    "新興分館": "新興區中正三路34號3樓",
    "新興民眾閱覽室": "新興區民生一路271號",
    "鹽埕分館": "鹽埕區大仁路179號",
    "前鎮分館": "前鎮區保泰路303號",
    "寶珠分館": "三民區大順二路468號4樓",
    "南鼓山分館": "鼓山區延平街87-13號4樓",
    "苓雅分館": "苓雅區青年二路101號",
    "翠屏分館": "楠梓區德惠路55號3樓",
    "陽明分館": "三民區陽明路300號3樓",
    "草衙分館": "前鎮區新衙路17號",
    "河堤分館": "三民區裕誠路1號",
    "楠仔坑分館": "楠梓區楠梓路262號",
    "左新分館": "左營區博愛三路453號",
    "小港分館": "小港區博學路365號",
    "高雄市文化中心分館": "苓雅區五福一路67號",
    "中崙分館": "鳳山區中崙五路1號",
    "鳳山二館": "鳳山區自強一路119巷75號",
    "鳳山曹公分館": "鳳山區曹公路23號",
    "大東藝術圖書館": "鳳山區光遠路161號",
    "大樹分館": "大樹區中興西路50號",
    "大樹二館": "大樹區久堂路97之1號",
    "大樹三館": "大樹區溪埔路77號3樓",
    "仁武分館": "仁武區中正路80號4樓",
    "澄觀分館": "仁武區澄仁路200號",
    "大社分館": "大社區自強街11號",
    "鳥松分館": "鳥松區大仁北路10號",
    "大寮分館": "大寮區進學路133號",
    "中庄分館": "大寮區光明路3段1437號",
    "林園分館": "林園區林園北路236號",
    "林園二館": "林園區西溪路56-20號",
    "岡山分館": "岡山區公園路2之1號",
    "岡山文化中心分館": "岡山區岡山南路43號",
    "燕巢分館": "燕巢區中民路592號",
    "橋頭分館": "橋頭區隆豐路7號",
    "梓官分館": "梓官區梓官路263號",
    "梓官赤東分館": "梓官區赤崁東路48-5號2樓",
    "彌陀分館": "彌陀區四維路1之1號",
    "彌陀公園分館": "彌陀區中正路281巷50號",
    "永安分館": "永安區保安路16巷5號",
    "茄萣分館": "茄萣區濱海路4段31巷1號",
    "路竹分館": "路竹區國昌路86巷9號",
    "湖內分館": "湖內區保生路101號",
    "阿蓮分館": "阿蓮區中正路381巷35號2樓",
    "田寮分館": "田寮區崗安路71-1號",
    "旗山分館": "旗山區中學路42號",
    "美濃分館": "美濃區中正路一段59號",
    "甲仙分館": "甲仙區中山路48號",
    "內門分館": "內門區中正路115巷18-1號",
    "內門內埔分館": "內門區內埔140-1號",
    "內門木柵分館": "內門區木柵3-1號",
    "內門溝坪分館": "內門區頂庄9-1號",
    "杉林分館": "杉林區山仙路75號",
    "六龜分館": "六龜區光復路70號",
}
# 內文常見的簡稱
BRANCH_ALIASES = {
    "李科永": "李科永紀念圖書館",
    "高市圖總館": "總館",
    "總圖": "總館",
    "文化中心分館": "高雄市文化中心分館",
    "鳳二": "鳳山二館",
    "大東藝術圖館": "大東藝術圖書館",
    "大東文化藝術中心": "大東藝術圖書館",
    "大東": "大東藝術圖書館",
}
# 名稱長的先比對，避免「岡山文化中心分館」被當成「文化中心分館」、「南鼓山分館」被當成「鼓山分館」
_BRANCH_NAMES = sorted([*BRANCHES, *BRANCH_ALIASES], key=len, reverse=True)
# 總館的組室（公布單位寫部門而非館名）
_DEPARTMENT_RE = re.compile(r"(部|組)$")

_CARD_RE = re.compile(
    r'href="Details\.aspx\?Parser=9,4,33,,,,(\d+)"\s+class="news_img">.*?'
    r'news_img_item">\s*<span>(.*?)</span>.*?news_img_date">\s*(.*?)\s*</div>',
    re.S,
)
_ROW_RE = re.compile(
    r'href="Details\.aspx\?Parser=9,4,33,,,,(\d+)".*?'
    r'latestevent_location2"[^>]*>(.*?)</div>.*?latestevent_date2">(.*?)</div>',
    re.S,
)
_CONTENT_START = '<div class="content_title">'
_CONTENT_ENDS = ("更多最新消息", "社群分享")

# 「活動時間：」「⏰時間｜」「日期/時間」「課程日期：」等；「報名時間」「開放時間」不算
_TIME_LINE_RE = re.compile(r"^[^\w]*(?:\d[.、])?\s*[\w/]{0,4}(?:日期|時間|期間|展期)")
_NOT_EVENT_TIME_RE = re.compile(r"公布|報名|預約|開放時間|截止|退[費款]|公告|兌換|抽獎")
_VENUE_LINE_RE = re.compile(r"^[^\w]*(?:\d[.、])?\s*([\w]{0,4}地點)\s*[:：｜|│]?\s*(.*)")
_FEE_LINE_RE = re.compile(r"費|免費|自由入場|自由參加|\d\s*元")

_FULL_DATE_RE = re.compile(r"(?<!\d)(\d{3,4})\s*[/.\-年]\s*(\d{1,2})\s*[/.\-月]\s*(\d{1,2})(?!\d)")
_SLASH_DATE_RE = re.compile(r"(?<![\d/])(\d{1,2})\s*/\s*(\d{1,2})(?![\d/])")
_CJK_DATE_RE = re.compile(r"(?<!\d)(\d{1,2})\s*月\s*(\d{1,2})(?!\d)")
_CLOCK_RE = re.compile(r"(上午|下午|晚上)?\s*(\d{1,2})\s*[:：]\s*(\d{2})")
_LIST_DATE_RE = re.compile(r"(\d{4})/(\d{1,2})/(\d{1,2})")
_PUBLISHED_RE = re.compile(r"公布日期：\s*(\d{4})-(\d{1,2})-(\d{1,2})")
_UNIT_RE = re.compile(r"公布單位</label>：\s*([^<]+)")
_TAG_RE = re.compile(r"【([^】]+)】|\[([^\]]+)\]")


def _list_items(page: str) -> list[dict]:
    items = []
    for pattern in (_CARD_RE, _ROW_RE):
        for item_id, unit, list_date in pattern.findall(page):
            items.append({"id": item_id, "unit": html.unescape(unit).strip(), "date": list_date.strip()})
    return items


def fetch(previous=None) -> bytes:
    items, seen, last_ids = [], set(), None
    for page in range(MAX_PAGES):
        page_items = _list_items(http.get(LIST_URL.format(page=page)).text)
        ids = [i["id"] for i in page_items]
        # 超過最後一頁時網站會一直回傳最後一頁
        if not page_items or ids == last_ids:
            break
        last_ids = ids
        for item in page_items:
            if item["id"] not in seen:
                seen.add(item["id"])
                items.append(item)
    details = {}
    for item in items:
        try:
            details[item["id"]] = _content_html(http.get(DETAIL_URL.format(id=item["id"])).text)
        except Exception:
            details[item["id"]] = ""
        time.sleep(DETAIL_DELAY)
    return json.dumps({"items": items, "details": details}, ensure_ascii=False).encode("utf-8")


def _content_html(page: str) -> str:
    """只留詳情頁的內文區塊，去掉選單與「更多最新消息」；圖片（有的是內嵌 base64）與標籤屬性也拿掉。"""
    start = page.find(_CONTENT_START)
    if start < 0:
        return ""
    ends = [i for i in (page.find(e, start) for e in _CONTENT_ENDS) if i >= 0]
    content = page[start:min(ends) if ends else len(page)]
    content = re.sub(r"<script.*?</script>|<style.*?</style>|<img[^>]*>", "", content, flags=re.S | re.I)
    content = re.sub(r"<(/?\w+)[^>]*>", r"<\1>", content)
    # 原始碼裡的換行在網頁上不會換行，只有 <br>、<p> 等才算
    return re.sub(r"\s+", " ", content)


def _lines(content: str) -> list[str]:
    text = re.sub(r"<script.*?</script>|<style.*?</style>", "", content, flags=re.S)
    text = re.sub(r"<br\s*/?>|</(?:p|div|li|tr|td|th|h\d)>", "\n", text, flags=re.I)
    text = html.unescape(re.sub(r"<[^>]+>", "", text)).replace("\xa0", " ")
    return [" ".join(line.split()) for line in text.split("\n") if line.strip()]


def _infer_year(month: int, day: int, ref: date) -> date | None:
    """沒寫年份的日期：取最接近參考日的年份（參考日前三個月以前的視為明年）。"""
    try:
        d = date(ref.year, month, day)
        return date(ref.year + 1, month, day) if d < ref - timedelta(days=90) else d
    except ValueError:
        return None


def dates_in(text: str, ref: date) -> list[date]:
    """讀出文字裡的日期：西元或民國年月日、M/D、M月D日。"""
    found = []

    def full(m: re.Match) -> str:
        year, month, day = map(int, m.groups())
        if 100 <= year < 200:
            year += 1911
        if 1990 <= year <= 2100:
            try:
                found.append(date(year, month, day))
            except ValueError:
                pass
        return " "

    text = _FULL_DATE_RE.sub(full, text)
    for pattern in (_SLASH_DATE_RE, _CJK_DATE_RE):
        for month, day in pattern.findall(text):
            if 1 <= int(month) <= 12:
                d = _infer_year(int(month), int(day), ref)
                if d:
                    found.append(d)
    return found


def clock_times(line: str) -> list[dtime]:
    times, last_meridiem = [], ""
    for meridiem, hour, minute in _CLOCK_RE.findall(line):
        hour, minute = int(hour), int(minute)
        # 「下午 2:30~5:00」的結束時間沿用前面的「下午」
        meridiem = meridiem or last_meridiem
        last_meridiem = meridiem
        if meridiem in ("下午", "晚上") and hour < 12:
            hour += 12
        if hour <= 23 and minute <= 59:
            times.append(dtime(hour, minute))
    return times


def _branch_of(*texts: str) -> str:
    for text in texts:
        for name in _BRANCH_NAMES:
            if name in text:
                return BRANCH_ALIASES.get(name, name)
    return ""


def _parse_date(text: str) -> date | None:
    m = _LIST_DATE_RE.search(text or "")
    if not m:
        return None
    try:
        return date(*map(int, m.groups()))
    except ValueError:
        return None


def parse(content: bytes, now: datetime) -> list[Event]:
    raw = json.loads(content)
    details = raw.get("details") or {}
    events = []
    for item in raw.get("items") or []:
        event = _parse_item(item, details.get(item["id"]) or "", now)
        if event:
            events.append(event)
    return events


def _parse_item(item: dict, content: str, now: datetime) -> Event | None:
    lines = _lines(content)
    if not lines:
        return None
    title = lines[0]
    m = _PUBLISHED_RE.search(content)
    published = date(*map(int, m.groups())) if m else None
    list_date = _parse_date(item.get("date", ""))
    ref = list_date or published
    if not ref:
        return None

    body = lines[1:]
    time_lines = [l for l in body if _TIME_LINE_RE.search(l) and not _NOT_EVENT_TIME_RE.search(l)]
    found = dates_in(title, ref)
    for line in time_lines:
        found += dates_in(line, ref)
        if "即日起" in line and published:
            found.append(published)

    start_day = list_date or (min(found) if found else None)
    if not start_day:
        return None
    later = [d for d in found if start_day <= d <= start_day + MAX_SPAN]
    end_day = max(later, default=start_day)

    clocks = next((c for c in map(clock_times, time_lines) if c), [])
    start_time = clocks[0] if clocks else dtime(0, 0)
    end_time = clocks[1] if len(clocks) > 1 and (clocks[1] > start_time or end_day > start_day) else dtime(23, 59, 59)
    start = datetime.combine(start_day, start_time, TAIPEI)
    end = datetime.combine(end_day, end_time, TAIPEI)
    if end < now:
        return None

    unit_m = _UNIT_RE.search(content)
    unit = html.unescape(unit_m.group(1)).strip() if unit_m else item.get("unit", "")
    unit = unit.removeprefix(LIBRARY)
    venue_label, venue_text = "", ""
    for line in body:
        vm = _VENUE_LINE_RE.match(line)
        if vm and vm.group(2):
            venue_label, venue_text = vm.groups()
            break
    tags = " ".join(a or b for a, b in _TAG_RE.findall(title))
    venue_branch = _branch_of(venue_text)
    branch = venue_branch or _branch_of(tags, unit, title) or ("總館" if _DEPARTMENT_RE.search(unit) else "")

    venue_district = district_of(venue_text)
    venue, address, district = venue_text, "", ""
    if venue_district and not venue_branch:
        # 內文寫了館外的地址
        address, district = venue_text, venue_district
    elif venue_text and not venue_branch and "集合" in venue_label:
        pass  # 走讀類只寫集合地點，不能當成主辦館的位置
    elif branch:
        address = "高雄市" + BRANCHES[branch]
        district = district_of(address)
        if not venue_branch:
            venue = f"{LIBRARY}{branch} {venue_text}".strip()

    fee_lines = [l for l in body if _FEE_LINE_RE.search(l)]
    intro = [l for l in body if not l.startswith(("公布日期", "公布單位"))]
    return Event(
        id=f"{NAME}:{item['id']}",
        title=title,
        start=start,
        end=end,
        venue=venue,
        address=address,
        district=district,
        category=category_by_keywords(title),
        fee=fee_of(*fee_lines),
        organizer=f"{LIBRARY}{unit}" if unit else LIBRARY,
        organizer_type="政府",
        description="\n".join(intro[:3]),
        links=[Link(source=NAME, url=DETAIL_URL.format(id=item["id"]))],
    )
