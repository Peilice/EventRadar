"""單一來源失敗時，沿用上次成功的資料並記錄錯誤，不影響其他來源。"""

import json
from datetime import timedelta
from types import SimpleNamespace

from eventradar import pipeline
from eventradar.model import Event, Link


def make_source(name, events=None, error=None):
    def fetch(previous=None):
        if error:
            raise error
        return b""

    return SimpleNamespace(NAME=name, LABEL=name.upper(), fetch=fetch, parse=lambda content, now: list(events or []))


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
