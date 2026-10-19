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


POSTAL_CODES = {
    "800": "新興", "801": "前金", "802": "苓雅", "803": "鹽埕", "804": "鼓山", "805": "旗津",
    "806": "前鎮", "807": "三民", "811": "楠梓", "812": "小港", "813": "左營", "814": "仁武",
    "815": "大社", "820": "岡山", "821": "路竹", "822": "阿蓮", "823": "田寮", "824": "燕巢",
    "825": "橋頭", "826": "梓官", "827": "彌陀", "828": "永安", "829": "湖內", "830": "鳳山",
    "831": "大寮", "832": "林園", "833": "鳥松", "840": "大樹", "842": "旗山", "843": "美濃",
    "844": "六龜", "845": "內門", "846": "杉林", "847": "甲仙", "848": "桃源", "849": "那瑪夏",
    "851": "茂林", "852": "茄萣",
}
# 郵遞區號須接在「高雄」前面，避免把門牌號碼誤認
_POSTAL_RE = re.compile(r"(?:^|[\s(（])(8[0-5]\d)(?:\d{2,3})?\s*(?:臺灣|台灣)?\s*高雄")

# 地址沒寫行政區時，用知名場館或地標推斷
LANDMARKS = {
    "駁二": "鹽埕", "大義倉庫": "鹽埕", "高雄流行音樂中心": "鹽埕", "高流": "鹽埕",
    "衛武營": "鳳山", "大東文化藝術中心": "鳳山",
    "高雄展覽館": "前鎮", "夢時代": "前鎮", "高雄軟體園區": "前鎮", "高雄市立圖書館總館": "前鎮",
    "高雄巨蛋": "左營", "K-ARENA": "左營", "蓮池潭": "左營", "高雄國家體育場": "左營", "世運主場館": "左營",
    "高雄車站": "三民", "高雄市文化中心": "苓雅", "至德堂": "苓雅", "中央公園": "前金",
    "高雄市立美術館": "鼓山", "高美館": "鼓山", "內惟藝術中心": "鼓山", "哈瑪星": "鼓山",
    "打狗英國領事館": "鼓山", "美麗島站": "新興", "旗津": "旗津",
    "五塊厝": "苓雅", "漢神巨蛋": "左營", "獅甲": "前鎮",
}


def district_of(*texts: str) -> str:
    """回傳行政區（含「區」字）：先找「○○區」，再看郵遞區號，最後比對地標；都找不到回傳空字串。"""
    texts = tuple(t for t in texts if t)
    for text in texts:
        m = _DISTRICT_RE.search(text)
        if m:
            return m.group(0)
    for text in texts:
        m = _POSTAL_RE.search(text)
        if m and m.group(1) in POSTAL_CODES:
            return POSTAL_CODES[m.group(1)] + "區"
    for text in texts:
        for landmark, district in LANDMARKS.items():
            if landmark in text:
                return district + "區"
    return ""
