"""各來源解析器：以存下來的真實回應測試。網站改版時這裡會先壞。"""

import json
from datetime import datetime

from eventradar.model import CATEGORIES, FEES, ORGANIZER_TYPES, TAIPEI, Event, Link
from eventradar.sources import accupass, iculture, khcc, khh_travel, kmfa, kpmc, ksml, opentix, twmarket, weiwuying

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


class TestKsml:
    def test_parses(self, fixture_bytes, now):
        events = ksml.parse(fixture_bytes("ksml.json"), now)
        _check_common(events, now)
        assert all(e.organizer_type == "政府" for e in events)
        assert sum(1 for e in events if e.district) >= len(events) * 0.9
        for e in events:
            assert e.links[0].url.startswith("https://www.ksml.edu.tw/LibNews/Details.aspx")

    def test_skips_items_without_dates(self, fixture_bytes, now):
        ids = {e.id for e in ksml.parse(fixture_bytes("ksml.json"), now)}
        assert "ksml:129" not in ids  # FB 粉絲團連結
        assert "ksml:15776" not in ids  # 循環袋交流箱，沒有活動日期

    def test_sessions_from_body(self, fixture_bytes, now):
        events = {e.id: e for e in ksml.parse(fixture_bytes("ksml.json"), now)}
        e = events["ksml:16424"]  # 兩場：11/1、11/13 14:00-16:00
        assert (e.start.isoformat(), e.end.isoformat()) == ("2026-11-01T14:00:00+08:00", "2026-11-13T16:00:00+08:00")
        assert e.district == "三民區"
        e = events["ksml:16413"]  # 列表沒有活動日期，從標題與內文讀
        assert e.start.isoformat() == "2026-12-19T09:30:00+08:00"
        assert e.fee == "付費"

    def test_venue_outside_library(self, fixture_bytes, now):
        events = {e.id: e for e in ksml.parse(fixture_bytes("ksml.json"), now)}
        assert events["ksml:16334"].district == "三民區"  # 橋頭分館辦的走讀，地點在三民區
        assert events["ksml:16400"].district == ""  # 只寫集合地點
        assert events["ksml:16422"].address == "高雄市前鎮區新光路61號"  # 多元文化部 → 總館

    def test_dates_in(self):
        from datetime import date

        ref = date(2026, 10, 21)
        assert ksml.dates_in("活動時間：115/11/01 (日) 上午10:00", ref) == [date(2026, 11, 1)]
        assert ksml.dates_in("115年 11月 7 日（六）", ref) == [date(2026, 11, 7)]
        assert ksml.dates_in("時間：2026/10/11（二）-2027/1/10（日）", ref) == [date(2026, 10, 11), date(2027, 1, 10)]
        assert ksml.dates_in("課程日期：10月7日至11月25日", ref) == [date(2026, 10, 7), date(2026, 11, 25)]
        assert ksml.dates_in("時間：1/9(六)", ref) == [date(2027, 1, 9)]  # 沒寫年份且早於參考日太多 → 明年
        assert ksml.dates_in("時間：14:00 - 16:00", ref) == []

    def test_clock_times(self):
        from datetime import time

        assert ksml.clock_times("時間：3/21 周六下午 2:30~5:00") == [time(14, 30), time(17, 0)]
        assert ksml.clock_times("下午14:00－16:00") == [time(14, 0), time(16, 0)]
        assert ksml.clock_times("上午10：00-12：00") == [time(10, 0), time(12, 0)]

    def test_branch_names(self):
        assert ksml._branch_of("岡山文化中心分館3樓") == "岡山文化中心分館"
        assert ksml._branch_of("文化中心分館4樓團欣室") == "高雄市文化中心分館"
        assert ksml._branch_of("南鼓山分館") == "南鼓山分館"
        assert ksml._branch_of("李科永圖書館 戶外草坪") == "李科永紀念圖書館"


class TestKhcc:
    def test_parses(self, fixture_bytes, now):
        events = khcc.parse(fixture_bytes("khcc.json"), now)
        _check_common(events, now)
        assert all(e.district for e in events)
        assert {e.category for e in events} >= {"展覽", "表演／音樂"}

    def test_exhibition(self, fixture_bytes, now):
        events = {e.id: e for e in khcc.parse(fixture_bytes("khcc.json"), now)}
        e = events["khcc:4324"]
        assert e.title == "2026清流畫會會員聯展" and e.category == "展覽"
        assert (e.start.isoformat(), e.end.isoformat()) == ("2026-10-23T00:00:00+08:00", "2026-11-03T23:59:59+08:00")
        assert (e.venue, e.address, e.district) == ("高雄市文化中心 至真堂三館", "高雄市苓雅區五福一路67號", "苓雅區")
        assert e.description.startswith("清流畫會秉持推廣水墨藝術")
        assert e.links[0].url.endswith("EXEC=D&DATA=4324")

    def test_performance_one_event_per_day(self, fixture_bytes, now):
        events = {e.id: e for e in khcc.parse(fixture_bytes("khcc.json"), now)}
        # 11/1 有 15:00 與 19:30 兩場，合併成最早開始到最晚結束
        e = events["khcc:-40200:20261101"]
        assert (e.start.strftime("%H:%M"), e.end.strftime("%H:%M")) == ("15:00", "22:00")
        assert "khcc:-40200:20261102" in events and "khcc:-40200:20261103" in events
        assert e.fee == "付費" and e.organizer == "凡事策劃藝文整合有限公司"
        assert e.description == "演出單位：凡事策劃藝文整合有限公司"

    def test_skips_private_and_ended(self, fixture_bytes, now):
        events = khcc.parse(fixture_bytes("khcc.json"), now)
        titles = {e.title for e in events}
        assert "2026奧斯卡音樂大賽" not in titles  # 入場方式：特定對象
        assert not any(e.venue.startswith("岡山") for e in events)  # 岡山這段期間都是特定對象
        later = khcc.parse(fixture_bytes("khcc.json"), datetime(2026, 11, 4, tzinfo=TAIPEI))
        assert "khcc:4324" not in {e.id for e in later}  # 11/3 結束

    def test_venue_names(self, fixture_bytes, now):
        venues = {e.venue for e in khcc.parse(fixture_bytes("khcc.json"), now)}
        assert "大東演藝廳" in venues and "高雄市音樂館" in venues
        assert "大東文化藝術中心展覽館303" in venues  # 去掉「每日10-17時,周一無休」
        assert "高雄市音樂館 音樂館" not in venues and not any("每日" in v for v in venues)

    def test_fee(self):
        assert khcc._fee("免票") == "免費"
        assert khcc._fee("售票") == "付費"
        assert khcc._fee("索票 (於服務台索取，每人2張)") == "免費"
        assert khcc._fee("") == "未知"

    def test_parse_list(self):
        page = (
            '<div class="row m101_box" onclick="x"><div class="col-md-9">'
            '<div style="m">活動名稱:<a href="rwd_home03.aspx?ID=$M102&IDK=2&EXEC=D&DATA=-40130&AP=$M102_DATE-115/10/31">'
            '<span style="color:#863408"><午茶絲竹吧></span></a>\n</div>'
            '<div style="m">演出時間:<span>115/10/31 17:00~18:00</span></a>\n</div>'
            '<div style="m">演出地點：大東戶外舞台</span></a>\n</div>'
            '<div style="m">演出單位：高雄市國樂團C</span></a>\n</div></div></div>'
            '<table><tr><td><a href="#" onClick="GoPage5700(2)">2</a></td></tr></table>'
        )
        [item] = khcc.parse_list(page, "04")
        assert item["title"] == "<午茶絲竹吧>"
        assert (item["kind"], item["data"], item["when"]) == ("performance", "-40130", "115/10/31 17:00~18:00")
        assert (item["place"], item["performer"]) == ("大東戶外舞台", "高雄市國樂團C")
        assert khcc._last_page(page) == 2

    def test_parse_detail(self):
        page = (
            '<div  id="toplink"><div class="m1">活動訊息</div></div>'
            '<div style="m">主辦單位：高雄市政府文化局 財團法人高雄市愛樂文化藝術基金會</div>'
            '<div style="m">演出時間：115/10/31 (六) | 17:00~18:00</div>'
            '<div style="m">入場方式：免票</div><div>BACK</div>'
        )
        assert khcc.parse_detail(page) == {
            "organizer": "高雄市政府文化局 財團法人高雄市愛樂文化藝術基金會",
            "admission": "免票",
            "description": "",
        }


class TestOpentix:
    def test_parses(self, fixture_bytes, now):
        events = opentix.parse(fixture_bytes("opentix.json"), now)
        _check_common(events, now)
        assert sum(1 for e in events if e.district) >= len(events) * 0.9

    def test_sessions_merged_per_day(self, fixture_bytes, now):
        events = {e.id: e for e in opentix.parse(fixture_bytes("opentix.json"), now)}
        prefix = "opentix:2075422956057141248:"
        days = sorted(k[len(prefix):] for k in events if k.startswith(prefix))
        assert days == ["20261106", "20261107", "20261108"]
        e = events[prefix + "20261107"]  # 14:30 與 19:30 兩場
        assert (e.start.strftime("%H:%M"), e.end.strftime("%H:%M")) == ("14:30", "21:10")
        assert (e.venue, e.district, e.fee) == ("駁二正港小劇場", "鹽埕區", "付費")
        assert e.links[0].url == "https://www.opentix.life/event/2075422956057141248"

    def test_only_kaohsiung_venue(self, fixture_bytes, now):
        events = [e for e in opentix.parse(fixture_bytes("opentix.json"), now) if e.id.startswith("opentix:2010907685806804993:")]
        # 臺中、高雄、臺北巡演，只留高雄場
        assert [(e.venue, e.start.date().isoformat()) for e in events] == [("衛武營國家藝術文化中心表演廳", "2026-12-06")]

    def test_skips_test_programs_and_zones(self, fixture_bytes, now):
        titles = {e.title for e in opentix.parse(fixture_bytes("opentix.json"), now)}
        assert "新手村 節目" not in titles  # 工程師測試用
        assert "衛武營主辦節目免費身障票專區" not in titles

    def test_fee(self):
        assert opentix._fee([{"minPrice": 0, "maxPrice": 0}]) == "免費"
        assert opentix._fee([{"minPrice": 500, "maxPrice": 1200}]) == "付費"
        assert opentix._fee([]) == "未知"


class TestKmfa:
    def test_parses(self, fixture_bytes, now):
        events = kmfa.parse(fixture_bytes("kmfa.json"), now)
        _check_common(events, now)
        assert all(e.district == "鼓山區" and e.organizer_type == "政府" for e in events)

    def test_time_from_title(self, fixture_bytes, now):
        events = {e.id: e for e in kmfa.parse(fixture_bytes("kmfa.json"), now)}
        e = events["kmfa:750753d7-e525-406c-838d-ad5ad731e7d3"]
        assert e.start.isoformat() == e.end.isoformat() == "2026-11-01T14:00:00+08:00"
        assert (e.venue, e.address, e.fee) == ("高雄市立美術館 地下樓演講廳", "高雄市鼓山區美術館路80號", "付費")
        assert e.links[0].url == "https://www.kmfa.gov.tw/OnlineApplyDetailC001200.aspx?Cond=750753d7-e525-406c-838d-ad5ad731e7d3"
        tour = events["kmfa:90fd7d19-0c4a-4385-b5db-d1a92b0a6849"]  # 標題沒寫時間：整段期間
        assert (tour.start.isoformat(), tour.end.isoformat()) == ("2026-09-08T00:00:00+08:00", "2026-11-29T23:59:59+08:00")
        assert tour.fee == "免費"  # 「子機租借費用$50」不算票價

    def test_sites(self, fixture_bytes, now):
        events = {e.id: e for e in kmfa.parse(fixture_bytes("kmfa.json"), now)}
        kids = events["kmfa:31439cc0-5d1d-4720-90e3-2f8c46955fbc"]
        assert (kids.venue, kids.address) == ("高雄兒童美術館", "高雄市鼓山區馬卡道路330號")
        assert events["kmfa:d76631d1-a917-4a01-861c-99fcaa9facd8"].venue == "高雄市立美術館園區 地下樓演講廳"

    def test_skips_non_events(self, fixture_bytes, now):
        ids = {e.id for e in kmfa.parse(fixture_bytes("kmfa.json"), now)}
        assert "kmfa:611e7186-f90b-4481-a92b-67883e02616c" not in ids  # 徵件
        assert "kmfa:6c1c6773-96a5-412f-b099-5fffd6fd6e84" not in ids  # 訂閱優惠
        assert "kmfa:b885f858-d065-4fb3-8338-35048c03a30b" not in ids  # 歡迎來信洽詢合作
