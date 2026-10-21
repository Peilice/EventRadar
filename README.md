# 高雄活動雷達 EventRadar

每天自動蒐集高雄的政府與民間活動，整理成可篩選的網頁。

## 資料來源

| 代號 | 來源 | 內容 | 備註 |
| --- | --- | --- | --- |
| `iculture` | 文化部 iCulture 藝文活動 API | 全國藝文活動，只保留高雄場次 | 很多活動沒填主辦單位 |
| `khh_travel` | 高雄旅遊網活動 XML（觀光局） | 觀光等級的大型活動 | 沒有費用與簡介 |
| `kktix` | KKTIX（API + 公開 feed） | 售票、報名活動 | 沒有票價欄位，用票種名稱推斷 |
| `accupass` | Accupass 活動通（網站前端 API + 活動頁 JSON-LD） | 講座、課程、手作、聚會等 | 地址要逐頁抓；已抓過的活動沿用上次資料 |
| `weiwuying` | 衛武營官網（網站前端 API） | 節目與學習推廣活動 | 費用、主辦（衛武營主辦與否）都有 |
| `kpmc` | 高雄流行音樂中心官網（節目頁內嵌資料 + 詳情頁） | 演出、課程 | 只有開始時間；已開始的展覽不收 |
| `ksml` | 高雄市立圖書館官網「最新活動」（列表 + 詳情頁 HTML） | 各分館的講座、親子、走讀、讀書會 | 時間、地點、費用從內文推斷；地址用內建的分館名錄 |
| `twmarket` | 台灣市集整合資訊網（WordPress API，「高雄市集」分類） | 百貨、商圈、公園、校園的假日市集 | 內容是攤商招募文，場次與時間從內文推斷 |

駁二藝術特區的官網活動列表由前端動態載入且內容停在 2020 年，未納入；駁二的展演多由文化局發布到文化部 iCulture。

政府來源的調查背景記在本機的「高雄市政府活動資料來源參考.md」（不納入版控）。

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
- KKTIX `api/v2`、Accupass 搜尋 API、衛武營 `/api/programs/list` 都不是公開文件化的 API，網站改版時可能失效（測試與網頁上的來源狀態會先反映）。
- 高流官網沒有結束時間：結束時間視同開始時間；開始時間已過的節目（多為進行中的展覽）不收。
- Accupass 與高流要逐頁讀詳情：Accupass 首次執行約 300 頁（約 5 分鐘）、高流約 50 頁，之後每天只抓新活動。
- 部分 Accupass 活動刻意只寫「捷運○○站附近」或「報名後通知」，這些活動沒有行政區。
- 市集資料來自攤商招募文：能讀出場次就拆成每天一筆（含「每週六日」「限假日」），讀不出來就以標題的日期範圍當一筆；招募文沒寫的市集（例如只在臉書公告的）不會出現。費用一律標「未知」，除非寫明免費入場（內文的金額多是攤位費）。
- 高市圖的活動時間寫在內文裡，各館格式不一：一篇含多個場次時合併成一筆（第一場到最後一場）；只寫在表格或圖片裡的場次讀不到，只用列表的活動日期。走讀活動只寫集合地點時沒有行政區。費用多數沒寫，標「未知」。每天重抓全部約 100 頁詳情。
- 區公所、社區、各局處自辦的小型活動多數不在這些來源中。
