from datetime import datetime

from eventradar.dedupe import dedupe, is_same_event, normalize_title, titles_match
from eventradar.model import TAIPEI, Event, Link

PRIORITY = ["iculture", "khh_travel", "kktix"]


def ev(id_, title, start, end=None, district="鹽埕區", **kw):
    source = id_.split(":")[0]
    s = datetime.fromisoformat(start).replace(tzinfo=TAIPEI)
    e = datetime.fromisoformat(end or start).replace(tzinfo=TAIPEI)
    return Event(id=id_, title=title, start=s, end=e, district=district,
                 links=[Link(source=source, url=f"https://example.com/{id_}")], **kw)


def test_normalize_title_strips_noise():
    assert normalize_title("【11/6 高雄場】Ellery 呈獻 THE CUT") == normalize_title("Ellery 呈獻 THE CUT")
    assert normalize_title("2026 Takao Rock 打狗祭") == "takaorock打狗祭"


def test_titles_match():
    assert titles_match("Fujii Kaze Prema World Tour - Kaohsiung", "Fujii Kaze Prema World Tour - Kaohsiung")
    assert titles_match("POP! POP! POP! 流行音樂互動展", "POP! POP! POP!流行音樂互動展 ＠ 高雄流行音樂中心")
    assert not titles_match("2026高雄電影節", "2026高雄國際偶戲節")
    assert not titles_match("高雄", "高雄場")  # 去雜訊後為空


def test_merges_across_sources():
    a = ev("iculture:1", "Fujii Kaze Prema World Tour", "2026-10-31T19:00", organizer="KKLIVE Taiwan", organizer_type="民間")
    b = ev("khh_travel:2", "Fujii Kaze Prema World Tour", "2026-10-31T00:00", "2026-11-01T23:59",
           organizer="高雄市政府", organizer_type="政府")
    c = ev("kktix:3", "Fujii Kaze Prema World Tour", "2026-10-31T19:00", fee="付費")
    merged = dedupe([a, b, c], PRIORITY)
    assert len(merged) == 1
    m = merged[0]
    assert m.id == "iculture:1"
    assert m.aliases == ["khh_travel:2", "kktix:3"]
    assert m.sources == ["iculture", "khh_travel", "kktix"]
    assert m.fee == "付費"
    # 主辦單位與類型出自同一來源
    assert (m.organizer, m.organizer_type) == ("KKLIVE Taiwan", "民間")


def test_does_not_merge_same_source_sessions():
    a = ev("kktix:a", "【13:00】Disney in Concert", "2026-10-25T13:00")
    b = ev("kktix:b", "【16:30】Disney in Concert", "2026-10-25T16:30")
    assert len(dedupe([a, b], PRIORITY)) == 2


def test_does_not_merge_without_date_overlap():
    a = ev("iculture:1", "羊文学 TOUR 2026", "2026-10-24T18:30")
    b = ev("kktix:1", "羊文学 TOUR 2026", "2026-10-25T18:30")
    assert not is_same_event(a, b)


def test_does_not_merge_different_or_unknown_district():
    a = ev("iculture:1", "聖誕音樂會", "2026-12-24T19:00", district="鹽埕區")
    b = ev("kktix:1", "聖誕音樂會", "2026-12-24T19:00", district="左營區")
    c = ev("kktix:2", "聖誕音樂會", "2026-12-24T19:00", district="")
    assert not is_same_event(a, b)
    assert not is_same_event(a, c)
