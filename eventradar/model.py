"""活動資料模型與時間工具。"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone

TAIPEI = timezone(timedelta(hours=8))

# 統一分類
CATEGORIES = ["展覽", "表演／音樂", "講座／課程", "節慶／觀光", "市集", "親子", "運動", "其他"]
FEES = ["免費", "付費", "未知"]
ORGANIZER_TYPES = ["政府", "民間", "不確定"]


@dataclass
class Link:
    source: str  # 來源代號，如 khh_travel
    url: str


@dataclass
class Event:
    id: str  # "<來源>:<來源內 ID>"
    title: str
    start: datetime
    end: datetime
    venue: str = ""
    address: str = ""
    district: str = ""
    category: str = "其他"
    fee: str = "未知"
    organizer: str = ""
    organizer_type: str = "不確定"
    description: str = ""
    links: list[Link] = field(default_factory=list)
    lat: float | None = None
    lng: float | None = None
    aliases: list[str] = field(default_factory=list)  # 去重時併入的其他活動 ID，讓網頁上的標記不因主 ID 改變而遺失

    @property
    def sources(self) -> list[str]:
        return sorted({link.source for link in self.links})

    def to_dict(self) -> dict:
        d = asdict(self)
        d["start"] = self.start.isoformat()
        d["end"] = self.end.isoformat()
        d["sources"] = self.sources
        return d

    @classmethod
    def from_dict(cls, d: dict) -> Event:
        d = dict(d)
        d.pop("sources", None)
        d["start"] = datetime.fromisoformat(d["start"])
        d["end"] = datetime.fromisoformat(d["end"])
        d["links"] = [Link(**link) for link in d.get("links", [])]
        return cls(**d)


def parse_local(text: str, fmt: str = "%Y/%m/%d %H:%M:%S") -> datetime:
    """解析台灣時間字串，回傳帶時區的 datetime。"""
    return datetime.strptime(text.strip(), fmt).replace(tzinfo=TAIPEI)


def now_taipei() -> datetime:
    return datetime.now(TAIPEI)
