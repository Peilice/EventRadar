"""HTTP 重試：只重試可能下次就好的錯誤；詳情頁有時間上限。"""

from types import SimpleNamespace

import pytest

from eventradar import http


class FakeHTTPError(Exception):
    def __init__(self, status):
        super().__init__(f"HTTP {status}")
        self.response = SimpleNamespace(status_code=status)


@pytest.fixture
def calls(monkeypatch):
    """依序回傳 outcomes 裡的結果（例外就丟出），記錄呼叫次數。"""
    record = SimpleNamespace(count=0, outcomes=[], kwargs=None)

    def fake_request(method, url, **kwargs):
        record.count += 1
        record.kwargs = kwargs
        outcome = record.outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return SimpleNamespace(raise_for_status=lambda: None, json=lambda: outcome, text="")

    monkeypatch.setattr(http.requests, "request", fake_request)
    monkeypatch.setattr(http.time, "sleep", lambda _s: None)
    return record


def test_does_not_retry_client_errors(calls):
    calls.outcomes = [FakeHTTPError(403)]
    with pytest.raises(FakeHTTPError):
        http.get("https://example.com/")
    assert calls.count == 1


@pytest.mark.parametrize("error", [FakeHTTPError(503), FakeHTTPError(429), TimeoutError("timed out")])
def test_retries_transient_errors(calls, error):
    calls.outcomes = [error, {"ok": True}]
    assert http.post_json("https://example.com/", {}) == {"ok": True}
    assert calls.count == 2


def test_gives_up_after_retries(calls):
    calls.outcomes = [FakeHTTPError(502)] * 3
    with pytest.raises(FakeHTTPError):
        http.get("https://example.com/", retries=2)
    assert calls.count == 3


def test_extra_headers_merge_with_defaults(calls):
    calls.outcomes = [{}]
    http.post_json("https://example.com/", {}, headers={"Origin": "https://a.example"})
    assert calls.kwargs["headers"]["Origin"] == "https://a.example"
    assert "Accept-Language" in calls.kwargs["headers"]


def test_deadline(caplog):
    assert http.Deadline("x", seconds=60).expired() is False
    budget = http.Deadline("x", seconds=0)
    assert budget.expired() and budget.expired()
    assert sum("抓詳情頁超過" in r.getMessage() for r in caplog.records) == 1  # 只警告一次
