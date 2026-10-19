"""各來源解析器：以存下來的真實回應測試。網站改版時這裡會先壞。"""

from eventradar.model import CATEGORIES, FEES, ORGANIZER_TYPES
from eventradar.sources import iculture, khh_travel, kktix


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
