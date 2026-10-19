"""地點、分類、費用、主辦類型規則。"""

import pytest

from eventradar.classify import category_by_keywords, fee_of, organizer_type_of
from eventradar.geo import district_of, is_kaohsiung, is_online


@pytest.mark.parametrize(
    "texts, expected",
    [
        (("高雄市鹽埕區真愛路1號",), True),
        (("", "高雄流行音樂中心 海音館"), True),
        (("鳳山區光遠路161號",), True),  # 沒寫高雄但有高雄行政區
        (("臺北市信義區信義路五段5號", "世貿展覽館一館"), False),
        (("桃園市桃園區三民路一段1號",), False),  # 三民路不是三民區
        (("Le Phare 共享空間 | 新左營館",), False),  # 寧可漏也不誤收
        (("", ""), False),
    ],
)
def test_is_kaohsiung(texts, expected):
    assert is_kaohsiung(*texts) is expected


def test_is_online():
    assert is_online("線上直播")
    assert is_online("Zoom 會議室")
    assert not is_online("高雄市立圖書館總館")


@pytest.mark.parametrize(
    "texts, expected",
    [
        (("高雄市806前鎮區夢時代",), "前鎮區"),
        (("高雄市鼓山區4鄰鼓山三路19-3號",), "鼓山區"),
        (("", "那瑪夏區民權里"), "那瑪夏區"),
        (("高雄",), ""),
    ],
)
def test_district_of(texts, expected):
    assert district_of(*texts) == expected


@pytest.mark.parametrize(
    "title, expected",
    [
        ("2026城市嶼浪市集嘉年華", "市集"),  # 市集優先於嘉年華
        ("高雄港馬拉松", "運動"),
        ("親子手作工作坊", "親子"),
        ("AI 應用講座", "講座／課程"),
        ("生命鬥士藍約翰-陶藝創作特展", "展覽"),
        ("空中補給巡迴演唱會", "表演／音樂"),
        ("2026高雄左營萬年季", "節慶／觀光"),
        ("微醺大飯店", "其他"),
    ],
)
def test_category_by_keywords(title, expected):
    assert category_by_keywords(title) == expected


@pytest.mark.parametrize(
    "texts, expected",
    [
        (("優惠票+49;團體優待票+79;全票+99",), "付費"),
        (("標準價 NTD 6600元/人",), "付費"),
        (("免費入場",), "免費"),
        (("免費入場，貴賓席 500 元",), "付費"),
        (("0 元",), "未知"),
        (("",), "未知"),
        (("一般票",), "未知"),
    ],
)
def test_fee_of(texts, expected):
    assert fee_of(*texts) == expected


@pytest.mark.parametrize(
    "organizer, expected",
    [
        ("高雄市政府文化局", "政府"),
        ("高雄市立圖書館總館", "政府"),
        ("高雄流行音樂中心、德國經濟辦事處", "政府"),
        ("台灣電力公司、高雄市政府文化局", "政府"),  # 任一為政府即政府
        ("海洋委員會海洋保育署", "政府"),
        ("全球音樂經紀有限公司", "民間"),
        ("鹿港天后宮、旗山天后宮", "民間"),
        ("三民書局", "民間"),  # 書局不是政府機關
        ("長興美術館", "不確定"),  # 美術館不一定公立
        ("MOPCON 主辦小組", "不確定"),
        ("", "不確定"),
    ],
)
def test_organizer_type_of(organizer, expected):
    assert organizer_type_of(organizer) == expected
