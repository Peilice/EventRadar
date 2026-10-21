"""蒐集流程：逐一抓各來源 → 去重 → 輸出網頁用的 JSON。

各來源獨立執行：某來源失敗時沿用它上次成功的資料（存在 data/sources/），
並在 status.json 記錄錯誤，網頁會標紅顯示。
"""

from __future__ import annotations

import argparse
import json
import logging
import traceback
from datetime import datetime
from pathlib import Path

from .dedupe import dedupe
from .model import Event, now_taipei
from .sources import SOURCES

ROOT = Path(__file__).resolve().parent.parent
CACHE_DIR = ROOT / "data" / "sources"
OUTPUT_DIR = ROOT / "docs" / "data"
# 筆數比上次（仍未結束的）少了九成以上，多半是網站回傳不完整，視同失敗
MIN_RATIO = 0.1
MIN_BASELINE = 20  # 上次筆數太少時不檢查，避免小來源正常波動被誤判

log = logging.getLogger("eventradar")


def _write_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")


def _read_json(path: Path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def run_source(source, now: datetime, save_raw: Path | None = None) -> tuple[list[Event], dict]:
    """抓一個來源。回傳 (活動, 狀態)；失敗時回傳上次成功的活動。"""
    cache_path = CACHE_DIR / f"{source.NAME}.json"
    status = {"label": source.LABEL, "last_attempt": now.isoformat()}
    cached = _read_json(cache_path, {"events": []})
    previous = [Event.from_dict(d) for d in cached["events"]]
    try:
        content = source.fetch(previous=previous)
        if save_raw:
            save_raw.mkdir(parents=True, exist_ok=True)
            (save_raw / f"{source.NAME}.raw").write_bytes(content)
        events = source.parse(content, now)
        baseline = sum(1 for ev in previous if ev.end >= now)
        if baseline >= MIN_BASELINE and len(events) < baseline * MIN_RATIO:
            raise ValueError(f"筆數異常：只有 {len(events)} 筆，上次仍有效的有 {baseline} 筆")
        _write_json(cache_path, {"fetched_at": now.isoformat(), "events": [e.to_dict() for e in events]})
        status.update(ok=True, count=len(events), last_success=now.isoformat(), error="")
        log.info("%s：%d 筆", source.NAME, len(events))
        return events, status
    except Exception as e:  # 單一來源失敗不影響其他來源
        log.error("%s 失敗：%s", source.NAME, e)
        log.debug(traceback.format_exc())
        events = [ev for ev in previous if ev.end >= now]
        status.update(ok=False, count=0, cached_count=len(events), error=f"{type(e).__name__}: {e}"[:300])
        return events, status


def build(now: datetime | None = None, only: list[str] | None = None, save_raw: Path | None = None) -> dict:
    now = now or now_taipei()
    old_status = _read_json(OUTPUT_DIR / "status.json", {}).get("sources", {})

    all_events: list[Event] = []
    statuses = {}
    for source in SOURCES:
        if only and source.NAME not in only:
            cached = _read_json(CACHE_DIR / f"{source.NAME}.json", {"events": []})
            all_events += [ev for ev in map(Event.from_dict, cached["events"]) if ev.end >= now]
            if source.NAME in old_status:
                statuses[source.NAME] = old_status[source.NAME]
            continue
        events, status = run_source(source, now, save_raw)
        if not status["ok"] and source.NAME in old_status:
            status["last_success"] = old_status[source.NAME].get("last_success")
        statuses[source.NAME] = status
        all_events += events

    merged = dedupe(all_events, [s.NAME for s in SOURCES])
    merged.sort(key=lambda e: (e.start, e.end, e.title))
    log.info("合併前 %d 筆，合併後 %d 筆", len(all_events), len(merged))

    _write_json(
        OUTPUT_DIR / "events.json",
        {"generated_at": now.isoformat(), "events": [e.to_dict() for e in merged]},
    )
    status_doc = {"generated_at": now.isoformat(), "sources": statuses}
    _write_json(OUTPUT_DIR / "status.json", status_doc)
    return status_doc


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="eventradar", description="蒐集高雄活動資訊")
    parser.add_argument("--only", nargs="+", help="只重新抓指定來源，其他沿用快取")
    parser.add_argument("--save-raw", type=Path, help="把各來源原始回應存到此目錄（製作測試資料用）")
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO, format="%(message)s")

    status = build(only=args.only, save_raw=args.save_raw)
    failed = [name for name, s in status["sources"].items() if not s.get("ok")]
    # 任一來源失敗就回傳非 0；資料仍已寫出，由 GitHub Actions 先提交再標記失敗並寄通知
    if failed:
        log.error("失敗的來源：%s", "、".join(failed))
    return 1 if failed else 0
