"""共用 HTTP 抓取，含重試與詳情頁的時間上限。

使用 curl_cffi 模擬瀏覽器的 TLS 指紋：有些網站前面的 Cloudflare 會擋 requests
的指紋；另外 Python 3.13 起的嚴格憑證檢查會拒絕 cloud.culture.tw 的憑證
（缺 Subject Key Identifier），curl_cffi 不受影響。
"""

from __future__ import annotations

import logging
import time

from curl_cffi import requests

log = logging.getLogger("eventradar")

IMPERSONATE = "chrome"
DEFAULT_HEADERS = {"Accept-Language": "zh-TW,zh;q=0.9"}
# 只有這些狀態碼值得重試；403、404 這類重試幾次結果都一樣，只會白等
RETRY_STATUS = {408, 425, 429, 500, 502, 503, 504}
# 每個來源抓詳情頁的時間上限（秒）。網站開始擋詳情頁時，逐頁失敗會拖過 workflow 的時間限制，
# 讓所有來源當天都沒更新；超過上限就停止抓新的詳情頁，只用列表資料，沒抓到的下次再抓
DETAIL_BUDGET = 300


def _retryable(error: Exception) -> bool:
    resp = getattr(error, "response", None)
    # 沒有回應（逾時、連線中斷、DNS）才可能下次就好；有回應時看狀態碼
    return resp is None or resp.status_code in RETRY_STATUS


def request(
    method: str,
    url: str,
    *,
    params: dict | None = None,
    json: dict | None = None,
    headers: dict | None = None,
    timeout: int = 60,
    retries: int = 2,
):
    for attempt in range(retries + 1):
        try:
            resp = requests.request(
                method,
                url,
                params=params,
                json=json,
                timeout=timeout,
                impersonate=IMPERSONATE,
                headers={**DEFAULT_HEADERS, **(headers or {})},
            )
            resp.raise_for_status()
            return resp
        except Exception as e:
            if attempt >= retries or not _retryable(e):
                raise
            time.sleep(3 * (attempt + 1))
    raise AssertionError("unreachable")


def get(url: str, *, params: dict | None = None, headers: dict | None = None, timeout: int = 60, retries: int = 2):
    return request("GET", url, params=params, headers=headers, timeout=timeout, retries=retries)


def post_json(url: str, body: dict, *, headers: dict | None = None, timeout: int = 60, retries: int = 2) -> dict:
    return request("POST", url, json=body, headers=headers, timeout=timeout, retries=retries).json()


class Deadline:
    """抓詳情頁的時間上限。迴圈每抓一頁前問 expired()，超過時記一次警告。"""

    def __init__(self, source: str, seconds: float | None = None):
        self.source = source
        self.seconds = DETAIL_BUDGET if seconds is None else seconds
        self.end = time.monotonic() + self.seconds
        self.hit = False

    def expired(self) -> bool:
        if time.monotonic() < self.end:
            return False
        if not self.hit:
            self.hit = True
            log.warning("%s：抓詳情頁超過 %d 秒，其餘只用列表資料，下次執行再補抓", self.source, self.seconds)
        return True
