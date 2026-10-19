# 高雄活動雷達 EventRadar

每天自動蒐集高雄的政府與民間活動，整理成可篩選的網頁。

## 資料來源

| 代號 | 來源 | 內容 | 備註 |
| --- | --- | --- | --- |
| `iculture` | 文化部 iCulture 藝文活動 API | 全國藝文活動，只保留高雄場次 | 很多活動沒填主辦單位 |
| `khh_travel` | 高雄旅遊網活動 XML（觀光局） | 觀光等級的大型活動 | 沒有費用與簡介 |
| `kktix` | KKTIX（API + 公開 feed） | 售票、報名活動 | 沒有票價欄位，用票種名稱推斷 |

更多背景請見 [高雄市政府活動資料來源參考.md](高雄市政府活動資料來源參考.md)。

## 流程

1. `python -m eventradar` 逐一抓各來源 → 篩出高雄、尚未結束的活動 → 分類 → 跨來源去重
2. 各來源解析結果存在 `data/sources/<來源>.json`；某來源失敗時沿用上次成功的資料
3. 輸出 `docs/data/events.json` 與 `docs/data/status.json`，由 `docs/index.html` 讀取顯示

規則重點：

- **高雄判定**：地址或場地含「高雄」或「<高雄行政區>區」；線上活動排除
- **分類**：先對應來源原有分類，沒有就用關鍵字（`eventradar/classify.py`）
- **費用／主辦類型**：只依明確的字樣判斷，判斷不出來就標「未知」或「不確定」
- **去重**：名稱相似、日期重疊、同行政區三者都成立才合併；同一來源內不合併

## 本機使用

```sh
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements.txt   # Windows
.venv/Scripts/python -m eventradar                         # 抓資料
.venv/Scripts/python -m pytest -q                          # 測試
.venv/Scripts/python -m http.server 8799 --directory docs  # 開 http://127.0.0.1:8799/
```

其他選項：`--only kktix` 只重抓指定來源；`--save-raw <目錄>` 保存原始回應，用來更新 `tests/fixtures/`。

## 部署（GitHub）

1. 建立 GitHub repo 並推上去（Pages 免費方案需為公開 repo）
2. Settings → Pages → Source 選 `Deploy from a branch`，分支 `main`、資料夾 `/docs`
3. Settings → Actions → General → Workflow permissions 選 `Read and write permissions`
4. 到 Actions 頁手動執行一次「每日更新活動」確認可以跑

之後每天台灣時間 00:00 自動更新（GitHub 尖峰時段可能延遲）。有任何來源失敗時 workflow 會標紅並寄信給你，網頁底部的來源狀態也會標紅。

## 已知限制

- 抓取使用 `curl_cffi` 模擬瀏覽器 TLS 指紋：KKTIX 的 Cloudflare 會擋一般的 Python requests。GitHub Actions 的機房在國外，若某來源擋海外 IP，需改在本機排程執行。
- iCulture 約七成的活動沒有填主辦單位，所以主辦類型多為「不確定」。
- 講座、研習、社區活動等小型活動多數不在這些來源中。
