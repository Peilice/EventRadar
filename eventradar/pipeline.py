"""蒐集流程：逐一抓各來源 → 去重 → 輸出網頁用的 JSON。

各來源獨立執行：某來源失敗時沿用它上次成功的資料（存在 data/sources/），
並在 status.json 記錄錯誤，網頁會標紅顯示。
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import traceback
from datetime import datetime, timedelta
from pathlib import Path

from .dedupe import dedupe
from .model import Event, now_taipei
from .sources import SOURCES

ROOT = Path(__file__).resolve().parent.parent
CACHE_DIR = ROOT / "data" / "sources"
OUTPUT_DIR = ROOT / "docs" / "data"
# 每個活動 ID 第一次與最後一次被抓到的日期，用來判斷哪些是新增的活動
FIRST_SEEN_PATH = ROOT / "data" / "first_seen.json"
# 超過這麼多天沒再出現才從紀錄移除，避免來源偶爾漏抓、之後又出現時被當成新活動
FIRST_SEEN_KEEP_DAYS = 60
# 筆數比上次（仍未結束的）少了九成以上，多半是網站回傳不完整，視同失敗
MIN_RATIO = 0.1
MIN_BASELINE = 20  # 上次筆數太少時不檢查，避免小來源正常波動被誤判
# 少了五成以上不擋資料，但標黃提醒（例如 iCulture 在部分時段缺售票系統匯入的活動）
WARN_RATIO = 0.5
# --skip 的來源由別處（本機 runner）更新快取，超過這麼久沒更新視同失敗
SKIP_MAX_AGE = timedelta(days=2)

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
        # 下滑後快取就只剩較少的筆數，隔天拿它比會以為正常；所以下滑時記下下滑前仍有效活動的結束時間，
        # 之後一直拿它比（活動陸續結束時自然遞減），直到筆數回升才清掉
        ref_ends = [e for e in cached.get("ref_ends", []) if datetime.fromisoformat(e) >= now]
        if len(ref_ends) < baseline:
            ref_ends = [ev.end.isoformat() for ev in previous if ev.end >= now]
        warning = ""
        if len(ref_ends) >= MIN_BASELINE and len(events) < len(ref_ends) * WARN_RATIO:
            warning = f"筆數少了一半以上：{len(events)} 筆，下滑前仍有效的有 {len(ref_ends)} 筆"
            log.warning("%s %s", source.NAME, warning)
        # 警告也寫進快取：本機 runner 的 status.json 不提交，每日更新要從快取讀回
        cache = {"fetched_at": now.isoformat(), "warning": warning, "events": [e.to_dict() for e in events]}
        if warning:
            cache["ref_ends"] = ref_ends
        _write_json(cache_path, cache)
        status.update(ok=True, count=len(events), last_success=now.isoformat(), error="", warning=warning)
        log.info("%s：%d 筆", source.NAME, len(events))
        return events, status
    except Exception as e:  # 單一來源失敗不影響其他來源
        log.error("%s 失敗：%s", source.NAME, e)
        resp = getattr(e, "response", None)
        if resp is not None:  # HTTP 錯誤時附上回應內容，方便判斷被擋的原因
            log.error("  %s %s\n  %s", resp.status_code, resp.url, resp.text[:500])
        log.debug(traceback.format_exc())
        events = [ev for ev in previous if ev.end >= now]
        status.update(ok=False, count=0, cached_count=len(events), error=f"{type(e).__name__}: {e}"[:300])
        return events, status


def use_cache(source, now: datetime) -> tuple[list[Event], dict]:
    """不抓取，直接用別處更新的快取；狀態依快取的抓取時間判斷。"""
    cached = _read_json(CACHE_DIR / f"{source.NAME}.json", {"events": []})
    events = [ev for ev in map(Event.from_dict, cached["events"]) if ev.end >= now]
    fetched_at = cached.get("fetched_at")
    status = {"label": source.LABEL, "last_attempt": fetched_at, "last_success": fetched_at}
    if fetched_at and now - datetime.fromisoformat(fetched_at) <= SKIP_MAX_AGE:
        status.update(ok=True, count=len(events), error="", warning=cached.get("warning", ""))
    else:
        days = SKIP_MAX_AGE.days
        status.update(ok=False, count=0, cached_count=len(events), error=f"超過 {days} 天沒有更新（由本機 runner 抓取）")
    return events, status


def mark_first_seen(events: list[Event], now: datetime) -> None:
    """幫每筆活動填上第一次被抓到的日期，並更新紀錄檔。"""
    today = now.date().isoformat()
    seen = _read_json(FIRST_SEEN_PATH, {})
    for ev in events:
        record = seen.setdefault(ev.id, {"first": today})
        record["last"] = today
        ev.first_seen = record["first"]
    cutoff = (now - timedelta(days=FIRST_SEEN_KEEP_DAYS)).date().isoformat()
    _write_json(FIRST_SEEN_PATH, {k: v for k, v in sorted(seen.items()) if v["last"] >= cutoff})


def build(
    now: datetime | None = None,
    only: list[str] | None = None,
    save_raw: Path | None = None,
    skip: list[str] | None = None,
) -> dict:
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
        if skip and source.NAME in skip:
            events, status = use_cache(source, now)
            statuses[source.NAME] = status
            all_events += events
            continue
        events, status = run_source(source, now, save_raw)
        if not status["ok"] and source.NAME in old_status:
            status["last_success"] = old_status[source.NAME].get("last_success")
        statuses[source.NAME] = status
        all_events += events

    mark_first_seen(all_events, now)
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


class _GitHubAnnotations(logging.Handler):
    """在 GitHub Actions 上把警告與錯誤另外輸出成 annotation，執行摘要頁就看得到，不必翻紀錄。"""

    def __init__(self):
        super().__init__(level=logging.WARNING)

    def emit(self, record: logging.LogRecord) -> None:
        kind = "error" if record.levelno >= logging.ERROR else "warning"
        msg = record.getMessage().replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")
        print(f"::{kind}::{msg}", flush=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="eventradar", description="蒐集高雄活動資訊")
    parser.add_argument("--only", nargs="+", help="只重新抓指定來源，其他沿用快取")
    parser.add_argument("--skip", nargs="+", help="不抓指定來源，沿用別處更新的快取（太久沒更新視同失敗）")
    parser.add_argument("--save-raw", type=Path, help="把各來源原始回應存到此目錄（製作測試資料用）")
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO, format="%(message)s")
    if os.environ.get("GITHUB_ACTIONS"):
        logging.getLogger().addHandler(_GitHubAnnotations())

    status = build(only=args.only, save_raw=args.save_raw, skip=args.skip)
    sources = status["sources"]
    # --only 時只看這次有抓的來源，其他來源沿用的舊狀態不算
    failed = [name for name in args.only or sources if not sources.get(name, {}).get("ok")]
    # 任一來源失敗就回傳非 0；資料仍已寫出，由 GitHub Actions 先提交再標記失敗並寄通知
    if failed:
        log.error("失敗的來源：%s", "、".join(failed))
    return 1 if failed else 0
