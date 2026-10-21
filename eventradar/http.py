"""共用 HTTP 抓取，含重試。

使用 curl_cffi 模擬瀏覽器的 TLS 指紋：有些網站前面的 Cloudflare 會擋 requests
的指紋；另外 Python 3.13 起的嚴格憑證檢查會拒絕 cloud.culture.tw 的憑證
（缺 Subject Key Identifier），curl_cffi 不受影響。
"""

from __future__ import annotations

import time

from curl_cffi import requests

IMPERSONATE = "chrome"


def get(url: str, *, params: dict | None = None, timeout: int = 60, retries: int = 2):
    last_error: Exception | None = None
    for attempt in range(retries + 1):
        try:
            resp = requests.get(
                url,
                params=params,
                timeout=timeout,
                impersonate=IMPERSONATE,
                headers={"Accept-Language": "zh-TW,zh;q=0.9"},
            )
            resp.raise_for_status()
            return resp
        except Exception as e:
            last_error = e
            if attempt < retries:
                time.sleep(3 * (attempt + 1))
    assert last_error is not None
    raise last_error


def post_json(url: str, body: dict, *, timeout: int = 60, retries: int = 2) -> dict:
    last_error: Exception | None = None
    for attempt in range(retries + 1):
        try:
            resp = requests.post(
                url,
                json=body,
                timeout=timeout,
                impersonate=IMPERSONATE,
                headers={"Accept-Language": "zh-TW,zh;q=0.9"},
            )
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            last_error = e
            if attempt < retries:
                time.sleep(3 * (attempt + 1))
    assert last_error is not None
    raise last_error
