"""規則式分類：活動分類、主辦類型、費用。"""

from __future__ import annotations

import re

# 關鍵字規則，依序比對，先中先贏
_KEYWORD_RULES: list[tuple[str, re.Pattern]] = [
    ("市集", re.compile(r"市集|跳蚤|二手市|農夫市")),
    ("運動", re.compile(r"馬拉松|路跑|鐵人|單車|自行車|球賽|運動會|錦標賽|健走|登山|瑜珈|瑜伽")),
    ("親子", re.compile(r"親子|兒童|童趣|小朋友|繪本|故事屋|說故事")),
    ("講座／課程", re.compile(r"講座|課程|工作坊|研習|培訓|講堂|論壇|讀書會|分享會|班\b|班」|班\)|班）|實務班|學堂|導覽|手作|DIY|體驗課|共讀|共學|大師班|訓練營")),
    ("展覽", re.compile(r"展覽|特展|常設展|個展|聯展|邀請展|作品展|藝術展|攝影展|書法展|畫展|展出|展$|EXHIBITION|Exhibition|博覽會")),
    ("表演／音樂", re.compile(r"演唱會|音樂會|音樂節|音樂祭|演奏|演出|巡演|巡迴|live|劇場|劇團|戲劇|舞蹈|舞團|歌劇|音樂劇|偶戲|脫口秀|單口|喜劇|樂團|合唱|管弦|交響|國樂|爵士|電影", re.IGNORECASE)),
    ("節慶／觀光", re.compile(r"節$|節 |季$|祭|嘉年華|燈會|燈節|煙火|跨年|觀光|旅展|遶境|巡安|廟會|生活節|藝術節|國際節")),
]


def category_by_keywords(text: str, default: str = "其他") -> str:
    for category, pattern in _KEYWORD_RULES:
        if pattern.search(text):
            return category
    return default


# --- 主辦類型 ---

# 政府或公部門（含行政法人、公立場館）
_GOV_RE = re.compile(
    r"政府|市府|公所|市立|國立|縣立|市議會|立法院|"
    r"[^\s、，,]{1,8}((?<![書藥])局|署|委員會)$|區公所|戶政|衛生所|"
    r"行政法人|高雄流行音樂中心|衛武營|國家表演藝術中心|文化中心|"
    r"高雄市電影館|皮影戲館|內惟藝術中心|"
    r"駁二|捷運公司|國軍|警察|消防|"
    r"國家|教育部|文化部|經濟部|交通部|數位發展部"
)
# 明確的民間單位
_PRIVATE_RE = re.compile(
    r"(?i)"
    r"公司|股份|有限|企業|工作室|協會|學會|公會|基金會|社團法人|促進會|樂團|劇團|舞團|合唱團|"
    r"娛樂|唱片|經紀|製作|創藝|Records|Entertainment|Live|Club|"
    r"書店|書局|咖啡|酒館|酒吧|餐廳|文化館|天后宮|宮$|廟$|教會|商圈|飯店|旅行社|7-ELEVEN|全聯|百貨"
)


def _split_units(organizer: str) -> list[str]:
    return [u.strip() for u in re.split(r"[、，,;；/]", organizer) if u.strip()]


def organizer_type_of(organizer: str) -> str:
    """任一主辦單位為政府即為「政府」；全部可判為民間才算「民間」；其餘「不確定」。"""
    units = _split_units(organizer)
    if not units:
        return "不確定"
    if any(_GOV_RE.search(u) for u in units):
        return "政府"
    if all(_PRIVATE_RE.search(u) for u in units):
        return "民間"
    return "不確定"


# --- 費用 ---

_FREE_RE = re.compile(r"免費|免票|免報名費|不收費|自由入場|自由參加|免門票")
_PRICE_RE = re.compile(
    r"(\d[\d,]{1,7})\s*元|NT\$?\s*(\d[\d,]{1,7})|NTD\s*(\d[\d,]{1,7})|[$＄]\s*(\d[\d,]{1,7})|\+\s*(\d{2,6})",
    re.IGNORECASE,
)


def mentions_free(text: str) -> bool:
    return bool(_FREE_RE.search(text or ""))


def fee_of(*texts: str) -> str:
    """有明確免費字樣為「免費」，有大於 0 的金額為「付費」，否則「未知」。"""
    joined = " ".join(t for t in texts if t)
    if not joined.strip():
        return "未知"
    for m in _PRICE_RE.finditer(joined):
        amount = next(g for g in m.groups() if g)
        if int(amount.replace(",", "")) > 0:
            return "付費"
    if _FREE_RE.search(joined):
        return "免費"
    return "未知"
