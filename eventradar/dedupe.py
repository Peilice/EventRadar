"""跨來源去重：名稱相似 + 日期重疊 + 同行政區，三者都成立才合併。

判斷不確定時寧可不合併；同一來源內的活動不互相合併（例如同一場演出的不同場次）。
"""

from __future__ import annotations

import re
from difflib import SequenceMatcher

from .model import Event

SIMILARITY_THRESHOLD = 0.85
MIN_CONTAINED_LEN = 6
MIN_CONTAINED_RATIO = 0.6

_BRACKETED_NOISE_RE = re.compile(r"【[^】]*】|\[[^\]]*\]|［[^］]*］")
_NOISE_RE = re.compile(r"20\d\d|高雄場|高雄站|高雄")
_NON_WORD_RE = re.compile(r"[\W_]+")


def normalize_title(title: str) -> str:
    t = _BRACKETED_NOISE_RE.sub("", title)
    t = _NOISE_RE.sub("", t.lower())
    return _NON_WORD_RE.sub("", t)


def titles_match(a: str, b: str) -> bool:
    na, nb = normalize_title(a), normalize_title(b)
    if not na or not nb:
        return False
    if na == nb:
        return True
    short, long_ = sorted((na, nb), key=len)
    if len(short) >= MIN_CONTAINED_LEN and short in long_ and len(short) / len(long_) >= MIN_CONTAINED_RATIO:
        return True
    return SequenceMatcher(None, na, nb).ratio() >= SIMILARITY_THRESHOLD


def _dates_overlap(a: Event, b: Event) -> bool:
    return a.start.date() <= b.end.date() and b.start.date() <= a.end.date()


def is_same_event(a: Event, b: Event) -> bool:
    if set(a.sources) & set(b.sources):
        return False
    if not (a.district and a.district == b.district):
        return False
    return _dates_overlap(a, b) and titles_match(a.title, b.title)


def dedupe(events: list[Event], source_priority: list[str]) -> list[Event]:
    """合併重複活動。source_priority 決定合併後優先採用哪個來源的欄位。"""
    parent = list(range(len(events)))

    def find(i: int) -> int:
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    for i in range(len(events)):
        for j in range(i + 1, len(events)):
            if is_same_event(events[i], events[j]):
                parent[find(j)] = find(i)

    groups: dict[int, list[Event]] = {}
    for i, event in enumerate(events):
        groups.setdefault(find(i), []).append(event)

    rank = {name: i for i, name in enumerate(source_priority)}
    merged = []
    for group in groups.values():
        group.sort(key=lambda e: min(rank.get(s, len(rank)) for s in e.sources))
        merged.append(group[0] if len(group) == 1 else _merge(group))
    return merged


def _first(values, empty=("", None)):
    return next((v for v in values if v not in empty), next(iter(values), None))


def _merge(group: list[Event]) -> Event:
    base = group[0]
    # 主辦單位與主辦類型取自同一個來源，避免張冠李戴
    org_source = next((e for e in group if e.organizer_type != "不確定"), None) or next(
        (e for e in group if e.organizer), base
    )
    links, seen_urls = [], set()
    for e in group:
        for link in e.links:
            if link.url not in seen_urls:
                seen_urls.add(link.url)
                links.append(link)
    return Event(
        id=base.id,
        title=base.title,
        start=min(e.start for e in group),
        end=max(e.end for e in group),
        venue=_first([e.venue for e in group]),
        address=_first([e.address for e in group]),
        district=base.district,
        category=_first([e.category for e in group], empty=("其他",)),
        fee=_first([e.fee for e in group], empty=("未知",)),
        organizer=org_source.organizer,
        organizer_type=org_source.organizer_type,
        description=_first([e.description for e in group]),
        links=links,
        lat=_first([e.lat for e in group]),
        lng=_first([e.lng for e in group]),
    )
