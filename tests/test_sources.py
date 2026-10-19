"""各來源解析器：以存下來的真實回應測試。網站改版時這裡會先壞。"""

import json

from eventradar.model import CATEGORIES, FEES, ORGANIZER_TYPES, Event, Link
from eventradar.sources import accupass, iculture, khh_travel, kktix, kpmc, twmarket, weiwuying

from .conftest import NOW


def _check_common(events, now):
    assert events, "解析結果不應為空"
    ids = [e.id for e in events]
    assert len(ids) == len(set(ids))
    for e in events:
        assert e.title
        assert e.end >= now, f"已結束的活動不應保留：{e.title}"
        assert e.start <= e.end
        assert e.category in CATEGORIES
        assert e.fee in FEES
        assert e.organizer_type in ORGANIZER_TYPES
        assert e.links and all(link.url.startswith("http") for link in e.links)


class TestKhhTravel:
    def test_parses_and_drops_ended(self, fixture_bytes, now):
        events = khh_travel.parse(fixture_bytes("khh_travel.xml"), now)
        _check_common(events, now)
        titles = {e.title for e in events}
        assert "2026高雄 Wild Wild 野生活" in titles
        assert "高雄跨年晚會 ✦ 2026雄嗨趴" not in titles  # 2026/01/01 已結束

    def test_fields(self, fixture_bytes, now):
        events = {e.id: e for e in khh_travel.parse(fixture_bytes("khh_travel.xml"), now)}
        e = events["khh_travel:C2_397000000A_008107"]
        assert e.district == "鳳山區"
        assert e.organizer_type == "政府"
        assert e.links[0].url == "https://khh.travel/zh-tw/event/calendardetail/8107/"
        assert e.lat and e.lng
        assert e.description == ""  # 來源填「無」


class TestICulture:
    def test_only_kaohsiung(self, fixture_bytes, now):
        events = iculture.parse(fixture_bytes("iculture.json"), now)
        _check_common(events, now)
        for e in events:
            assert "高雄" in e.address + e.venue or e.district

    def test_multi_city_tour_keeps_only_kaohsiung_shows(self, fixture_bytes, now):
        events = {e.id: e for e in iculture.parse(fixture_bytes("iculture.json"), now)}
        e = events["iculture:68b5d60226b32440a896424b"]  # 高雄 10/24 + 臺中 12/19
        assert e.start.date().isoformat() == "2026-10-24"
        assert e.end.date().isoformat() == "2026-10-24"
        assert e.venue == "高雄市文化中心至德堂"
        assert e.district == "苓雅區"

    def test_domain_only_url_falls_back_to_detail_page(self, fixture_bytes, now):
        events = iculture.parse(fixture_bytes("iculture.json"), now)
        for e in events:
            assert e.links[0].url.rstrip("/") not in ("https://kktix.com", "https://tixcraft.com")


class TestKktix:
    def test_parses(self, fixture_bytes, now):
        events = kktix.parse(fixture_bytes("kktix.json"), now)
        _check_common(events, now)

    def test_filters_non_kaohsiung_and_ads(self, fixture_bytes, now):
        events = kktix.parse(fixture_bytes("kktix.json"), now)
        for e in events:
            assert "台北" not in e.address and "臺北" not in e.address
            assert "辦公室" not in e.title and "租借" not in e.title

    def test_collection_parent_skipped_when_children_present(self, fixture_bytes, now):
        events = kktix.parse(fixture_bytes("kktix.json"), now)
        # 山下智久高雄場：系列活動 slug 為 aikorf，兩個子場次都在結果中
        assert "kktix:aikorf" not in {e.id for e in events}
        assert sum(1 for e in events if "山下智久" in e.title) == 2

    def test_organizer_from_feed(self, fixture_bytes, now):
        events = kktix.parse(fixture_bytes("kktix.json"), now)
        assert sum(1 for e in events if e.organizer) >= len(events) * 0.8

    def test_ticket_names_imply_paid(self, fixture_bytes, now):
        events = kktix.parse(fixture_bytes("kktix.json"), now)
        assert sum(1 for e in events if e.fee == "付費") >= len(events) * 0.5


class TestAccupass:
    def test_parses(self, fixture_bytes, now):
        events = accupass.parse(fixture_bytes("accupass.json"), now)
        _check_common(events, now)
        assert {e.fee for e in events} <= {"免費", "付費"}  # 費用直接來自 Accupass 的篩選
        assert sum(1 for e in events if e.address) >= len(events) * 0.9
        for e in events:
            assert e.links[0].url.startswith("https://www.accupass.com/event/")

    def test_times_converted_from_utc(self, now):
        item = {"eventIdNumber": "1", "name": "測試", "startDateTime": "2026-10-23T11:30:00Z",
                "endDateTime": "2026-10-23T12:30:00Z", "eventPlaceType": "Offline", "location": "Kaohsiung City"}
        e = accupass._parse_item(item, {}, [], "免費", now)
        assert e.start.isoformat() == "2026-10-23T19:30:00+08:00"

    def test_skips_online_and_other_cities(self, now):
        base = {"eventIdNumber": "1", "name": "測試", "startDateTime": "2026-10-23T11:30:00Z"}
        assert accupass._parse_item({**base, "eventPlaceType": "Online", "location": "Kaohsiung City"}, {}, [], "免費", now) is None
        assert accupass._parse_item({**base, "eventPlaceType": "Offline", "location": "Taipei City"}, {}, [], "免費", now) is None

    def test_category_keyword_first_then_accupass(self):
        assert accupass._category("萬聖精靈多肉森林組盆(親子班)", "", ["20"]) == "親子"
        assert accupass._category("THE FACT MUSIC AWARDS", "", ["22", "1"]) == "表演／音樂"
        assert accupass._category("某某聚會", "", []) == "其他"

    def test_fetch_reuses_previous_details(self, monkeypatch):
        item = {"eventIdNumber": "42", "name": "舊活動", "startDateTime": "2026-12-01T01:00:00Z",
                "eventPlaceType": "Offline", "location": "Kaohsiung City"}
        monkeypatch.setattr(accupass, "_search_all", lambda price, category=None: [item] if price == "1" else [])
        monkeypatch.setattr(accupass, "_fetch_detail", lambda _id: (_ for _ in ()).throw(AssertionError("不應重抓")))
        prev = Event(id="accupass:42", title="舊活動", start=NOW, end=NOW, venue="駁二", address="高雄市鹽埕區大勇路1號",
                     organizer="某單位", links=[Link("accupass", "https://www.accupass.com/event/42")])
        raw = json.loads(accupass.fetch(previous=[prev]))
        assert raw["details"]["42"]["location"]["address"] == "高雄市鹽埕區大勇路1號"


class TestWeiwuying:
    def test_parses(self, fixture_bytes, now):
        events = weiwuying.parse(fixture_bytes("weiwuying.json"), now)
        _check_common(events, now)
        for e in events:
            assert e.district == "鳳山區"
            assert e.venue.startswith("衛武營") and "衛武營 衛武營" not in e.venue
            assert e.links[0].url.startswith("https://www.npac-weiwuying.org/programs/")
        assert any(e.category == "講座／課程" for e in events)  # 學習推廣類

    def test_time_ranges(self):
        discrete = {"type": "discrete", "discrete": [{"time": 1792584000}, {"time": 1792670400}]}
        start, end = weiwuying._time_range(discrete)
        assert (end - start).days == 1
        continuous = {"type": "continuous", "continuous": {"start": 1791561600, "end": 1800720000}}
        start, end = weiwuying._time_range(continuous)
        assert (end.hour, end.minute) == (23, 59)  # 結束日整天有效

    def test_fee(self):
        assert weiwuying._fee({"type": "free"}) == "免費"
        assert weiwuying._fee({"type": "ticket", "ticket": {"price": [300, 600]}}) == "付費"
        assert weiwuying._fee({"type": "ticket", "ticket": {"price": [0]}}) == "免費"
        assert weiwuying._fee({"type": "signup"}) == "未知"

    def test_organizer_only_when_host(self, now):
        row = {"_id": "x", "chinese": {"title": "測試", "site": {}}, "catalogs": [],
               "dateTime": {"type": "discrete", "discrete": [{"time": int(now.timestamp()) + 3600}]}}
        assert weiwuying._parse_row({**row, "host": True}, "program", {}, {}, now).organizer_type == "政府"
        assert weiwuying._parse_row({**row, "host": False}, "program", {}, {}, now).organizer_type == "不確定"


class TestKpmc:
    def test_parses(self, fixture_bytes, now):
        events = kpmc.parse(fixture_bytes("kpmc.json"), now)
        _check_common(events, now)
        assert not any("總表" in e.title or "公告" in e.title for e in events)
        assert all(e.start >= now for e in events)  # 沒有結束時間，已開始的不收
        assert sum(1 for e in events if e.fee != "未知") >= len(events) * 0.8

    def test_whale_pier_is_lingya(self, fixture_bytes, now):
        events = kpmc.parse(fixture_bytes("kpmc.json"), now)
        for e in events:
            if "鯨魚堤岸" in e.venue:
                assert e.district == "苓雅區"
            else:
                assert e.district == "鹽埕區"

    def test_parse_detail(self):
        page = """<div><p>主辦單位</p><p>邱淑蟬 x 高雄流行音樂中心</p><p>票價資訊</p>
        <p>雙人套票 1200</p><p>單人預售 700</p><a>將此活動加入 Google 日曆</a><p>其他展演</p></div>"""
        assert kpmc.parse_detail(page) == {"organizer": "邱淑蟬 x 高雄流行音樂中心", "price": "雙人套票 1200 單人預售 700"}

    def test_price_roundtrip_through_description(self):
        desc = kpmc._description("某樂團", "預售 $800")
        assert kpmc._price_from_description(desc) == "預售 $800"


class TestTwmarket:
    def test_parses(self, fixture_bytes, now):
        events = twmarket.parse(fixture_bytes("twmarket.json"), now)
        _check_common(events, now)
        assert sum(1 for e in events if e.category == "市集") >= len(events) * 0.7
        assert sum(1 for e in events if e.district) >= len(events) * 0.9

    def test_weekend_sessions_split_per_day(self, fixture_bytes, now):
        events = [e for e in twmarket.parse(fixture_bytes("twmarket.json"), now) if e.id.startswith("twmarket:61285:")]
        days = [e.start.date().isoformat() for e in events]  # 10/31~11/29 每個週六日
        assert days[:3] == ["2026-10-31", "2026-11-01", "2026-11-07"] and len(days) == 10
        assert all(e.start.hour == 9 and e.end.hour == 17 for e in events)
        assert all(e.district == "鼓山區" for e in events)

    def test_hours_per_day(self, fixture_bytes, now):
        events = {e.id: e for e in twmarket.parse(fixture_bytes("twmarket.json"), now)}
        sat, sun = events["twmarket:61125:20261107"], events["twmarket:61125:20261108"]
        assert (sat.start.hour, sat.end.strftime("%H:%M")) == (12, "16:30")
        assert (sun.start.hour, sun.end.strftime("%H:%M")) == (9, "15:30")
        assert sat.address == "高雄市永安區新興路27-2號"

    def test_duplicate_posts_kept_once_per_day(self, fixture_bytes, now):
        events = twmarket.parse(fixture_bytes("twmarket.json"), now)
        # 61328 與 61159 是同一篇的重貼；機廠親子遊樂園區 11 月有兩篇不同標題的貼文
        assert not any(e.id.startswith("twmarket:61159:") for e in events)
        assert sum(1 for e in events if e.start.date().isoformat() == "2026-11-07" and "機廠" in e.venue) == 1

    def test_skips_non_kaohsiung_and_ended(self, fixture_bytes, now):
        ids = {e.id.split(":")[1] for e in twmarket.parse(fixture_bytes("twmarket.json"), now)}
        assert "61216" not in ids  # 多縣市
        assert "60741" not in ids  # 10/4 已結束

    def test_parse_title(self):
        info = twmarket.parse_title("2026.10.09~2026.02.08 高雄-大立百貨-漫光星光微型演唱會市集")
        assert info["end"].isoformat() == "2027-02-08"  # 跨年筆誤
        assert (info["region"], info["venue"], info["name"]) == ("高雄", "大立百貨", "漫光星光微型演唱會市集")
        assert twmarket.parse_title("2026.10.17~10.18 高雄市-岡山 樂購廣場") is None

    def test_session_dates(self):
        from datetime import date

        text = "市集時間 ▹10/24 ( 六）15:00-20:00\n11月場次 | 11/21-22(六、日)\n整體檔期 2026.10.17~12.20"
        days = twmarket.session_dates(text, date(2026, 10, 17), date(2026, 12, 20))
        assert days == [date(2026, 10, 24), date(2026, 11, 21), date(2026, 11, 22)]
        weekend = twmarket.session_dates("11月全月（限假日）", date(2026, 11, 1), date(2026, 11, 8))
        assert weekend == [date(2026, 11, 1), date(2026, 11, 7), date(2026, 11, 8)]
