"""單一來源失敗時，沿用上次成功的資料並記錄錯誤，不影響其他來源。"""

import json
from datetime import timedelta
from types import SimpleNamespace

import pytest

from eventradar import pipeline
from eventradar.model import Event, Link


def make_source(name, events=None, error=None):
    def fetch(previous=None):
        if error:
            raise error
        return b""

    return SimpleNamespace(NAME=name, LABEL=name.upper(), fetch=fetch, parse=lambda content, now: list(events or []))


@pytest.fixture(autouse=True)
def isolated_first_seen(tmp_path, monkeypatch):
    monkeypatch.setattr(pipeline, "FIRST_SEEN_PATH", tmp_path / "first_seen.json")


def test_failed_source_falls_back_to_cache(tmp_path, monkeypatch, now):
    monkeypatch.setattr(pipeline, "CACHE_DIR", tmp_path / "cache")
    monkeypatch.setattr(pipeline, "OUTPUT_DIR", tmp_path / "out")

    good = Event(id="a:1", title="好來源活動", start=now, end=now + timedelta(hours=2), district="鹽埕區",
                 links=[Link("a", "https://a.example/1")])
    old = Event(id="b:1", title="上次抓到的活動", start=now, end=now + timedelta(days=1), district="左營區",
                links=[Link("b", "https://b.example/1")])

    # 第一次：兩個來源都成功
    monkeypatch.setattr(pipeline, "SOURCES", [make_source("a", [good]), make_source("b", [old])])
    pipeline.build(now=now)

    # 第二次：b 失敗
    later = now + timedelta(hours=1)
    monkeypatch.setattr(pipeline, "SOURCES", [make_source("a", [good]), make_source("b", error=RuntimeError("403"))])
    status = pipeline.build(now=later)

    b = status["sources"]["b"]
    assert b["ok"] is False and "403" in b["error"]
    assert b["last_success"] == now.isoformat()  # 保留上次成功時間
    assert b["cached_count"] == 1
    assert status["sources"]["a"]["ok"] is True

    events = json.loads((tmp_path / "out" / "events.json").read_text(encoding="utf-8"))["events"]
    assert {e["title"] for e in events} == {"好來源活動", "上次抓到的活動"}


def test_sudden_drop_treated_as_failure(tmp_path, monkeypatch, now):
    monkeypatch.setattr(pipeline, "CACHE_DIR", tmp_path / "cache")
    monkeypatch.setattr(pipeline, "OUTPUT_DIR", tmp_path / "out")

    def make_events(n):
        return [Event(id=f"a:{i}", title=f"活動{i}", start=now, end=now + timedelta(days=1), district="鹽埕區",
                      links=[Link("a", f"https://a.example/{i}")]) for i in range(n)]

    monkeypatch.setattr(pipeline, "SOURCES", [make_source("a", make_events(100))])
    pipeline.build(now=now)

    # 網站回傳不完整：100 筆掉到 5 筆
    monkeypatch.setattr(pipeline, "SOURCES", [make_source("a", make_events(5))])
    status = pipeline.build(now=now + timedelta(hours=1))
    a = status["sources"]["a"]
    assert a["ok"] is False and "筆數異常" in a["error"]
    assert a["cached_count"] == 100
    cache = json.loads((tmp_path / "cache" / "a.json").read_text(encoding="utf-8"))
    assert len(cache["events"]) == 100  # 快取不被不完整的結果覆蓋

    # 正常減少（例如活動陸續結束）不受影響
    monkeypatch.setattr(pipeline, "SOURCES", [make_source("a", make_events(40))])
    assert pipeline.build(now=now + timedelta(hours=2))["sources"]["a"]["ok"] is True


def test_first_seen_marks_new_events(tmp_path, monkeypatch, now):
    monkeypatch.setattr(pipeline, "CACHE_DIR", tmp_path / "cache")
    monkeypatch.setattr(pipeline, "OUTPUT_DIR", tmp_path / "out")

    def make_event(source, i, title):
        return Event(id=f"{source}:{i}", title=title, start=now, end=now + timedelta(days=30), district="鹽埕區",
                     links=[Link(source, f"https://{source}.example/{i}")])

    def build_titles(day, a_events, b_events=()):
        monkeypatch.setattr(pipeline, "SOURCES", [make_source("a", a_events), make_source("b", list(b_events))])
        pipeline.build(now=now + timedelta(days=day))
        events = json.loads((tmp_path / "out" / "events.json").read_text(encoding="utf-8"))["events"]
        return {e["title"]: e["first_seen"] for e in events}

    old = make_event("a", 1, "老活動")
    assert build_titles(0, [old]) == {"老活動": "2026-10-19"}

    # 隔天新增一筆；老活動同時出現在 b 來源，合併後仍沿用最早的日期
    seen = build_titles(1, [old, make_event("a", 2, "新活動")], [make_event("b", 9, "老活動")])
    assert seen == {"老活動": "2026-10-19", "新活動": "2026-10-20"}

    # 來源漏抓一天後又出現，不算新活動
    build_titles(2, [old])
    assert build_titles(3, [old, make_event("a", 2, "新活動")])["新活動"] == "2026-10-20"


def test_skipped_source_uses_cache_until_stale(tmp_path, monkeypatch, now):
    monkeypatch.setattr(pipeline, "CACHE_DIR", tmp_path / "cache")
    monkeypatch.setattr(pipeline, "OUTPUT_DIR", tmp_path / "out")

    ev = Event(id="b:1", title="本機抓的活動", start=now, end=now + timedelta(days=30), district="鳳山區",
               links=[Link("b", "https://b.example/1")])
    # 本機只抓 b，寫入快取
    monkeypatch.setattr(pipeline, "SOURCES", [make_source("a", []), make_source("b", [ev])])
    pipeline.build(now=now, only=["b"])

    # 雲端跳過 b：b 一抓就會失敗，但不該被呼叫
    monkeypatch.setattr(pipeline, "SOURCES", [make_source("a", []), make_source("b", error=RuntimeError("403"))])
    b = pipeline.build(now=now + timedelta(days=1), skip=["b"])["sources"]["b"]
    assert b["ok"] is True and b["count"] == 1 and b["last_success"] == now.isoformat()

    # 本機太久沒更新：標為失敗，活動仍沿用
    b = pipeline.build(now=now + timedelta(days=3), skip=["b"])["sources"]["b"]
    assert b["ok"] is False and b["cached_count"] == 1 and "本機" in b["error"]
