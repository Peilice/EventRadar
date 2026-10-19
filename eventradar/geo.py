"""高雄地點判定與行政區解析。"""

from __future__ import annotations

import re

DISTRICTS = [
    "楠梓", "左營", "鼓山", "三民", "鹽埕", "前金", "新興", "苓雅", "前鎮", "旗津",
    "小港", "鳳山", "林園", "大寮", "大樹", "大社", "仁武", "鳥松", "岡山", "橋頭",
    "燕巢", "田寮", "阿蓮", "路竹", "湖內", "茄萣", "永安", "彌陀", "梓官", "旗山",
    "美濃", "六龜", "甲仙", "杉林", "內門", "茂林", "桃源", "那瑪夏",
]

_DISTRICT_RE = re.compile("(" + "|".join(DISTRICTS) + ")區")
_ONLINE_RE = re.compile(r"線上|online|zoom|google meet|視訊|直播", re.IGNORECASE)


def is_kaohsiung(*texts: str) -> bool:
    """地址或場地名稱含「高雄」或「<高雄行政區>區」即視為高雄。"""
    joined = " ".join(t for t in texts if t)
    return "高雄" in joined or bool(_DISTRICT_RE.search(joined))


def is_online(*texts: str) -> bool:
    joined = " ".join(t for t in texts if t)
    return bool(_ONLINE_RE.search(joined))


def district_of(*texts: str) -> str:
    """回傳第一個找到的行政區（含「區」字），找不到回傳空字串。"""
    for text in texts:
        if not text:
            continue
        m = _DISTRICT_RE.search(text)
        if m:
            return m.group(0)
    return ""
