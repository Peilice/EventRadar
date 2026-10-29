---
name: 高雄活動雷達
description: 自動彙整高雄的政府與民間活動，像一份翻開就能找到週末去處的口袋地圖
colors:
  seaside-blue: "#1e4fc7"
  seaside-blue-deep: "#15379a"
  on-sea: "#fff8ea"
  pineapple-yellow: "#ffc93c"
  cijin-sunset: "#ff6b35"
  time-orange: "#c2410c"
  harbor-ink: "#15213f"
  newsprint: "#fff5e3"
  surface: "#ffffff"
  surface-warm: "#fffaf0"
  muted-ink: "#4b5675"
  line-soft: "#e9dcc2"
  row-line: "#f1e7d3"
  gov-blue: "#1d4ed8"
  private-green: "#047857"
  danger: "#b91c1c"
  danger-soft: "#fde4e4"
  footer-muted: "#c3cbe4"
  footer-line: "#2f3d66"
  cat-exhibit: "#1d4ed8"
  cat-show: "#c2185b"
  cat-talk: "#6d28d9"
  cat-fest: "#c2410c"
  cat-market: "#92580a"
  cat-kids: "#047857"
  cat-sport: "#0e7490"
  cat-other: "#4b5563"
typography:
  brand:
    fontFamily: "Chiron GoRound TC, Noto Sans TC, PingFang TC, Microsoft JhengHei, system-ui, sans-serif"
    fontSize: "1.3rem"
    fontWeight: 900
    letterSpacing: "0.04em"
  headline:
    fontFamily: "Chiron GoRound TC, Noto Sans TC, PingFang TC, Microsoft JhengHei, system-ui, sans-serif"
    fontSize: "1.4rem"
    fontWeight: 900
    lineHeight: 1.35
  title:
    fontFamily: "Chiron GoRound TC, Noto Sans TC, PingFang TC, Microsoft JhengHei, system-ui, sans-serif"
    fontSize: "1rem"
    fontWeight: 700
    lineHeight: 1.35
  body:
    fontFamily: "Noto Sans TC, PingFang TC, Microsoft JhengHei, system-ui, -apple-system, Segoe UI, sans-serif"
    fontSize: "16px"
    fontWeight: 400
    lineHeight: 1.6
  body-small:
    fontFamily: "Noto Sans TC, PingFang TC, Microsoft JhengHei, system-ui, -apple-system, Segoe UI, sans-serif"
    fontSize: "0.85rem"
    fontWeight: 400
    lineHeight: 1.5
  label:
    fontFamily: "Chiron GoRound TC, Noto Sans TC, PingFang TC, Microsoft JhengHei, system-ui, sans-serif"
    fontSize: "0.85rem"
    fontWeight: 800
  numeral:
    fontFamily: "Fredoka, Chiron GoRound TC, sans-serif"
    fontSize: "1.9rem"
    fontWeight: 700
    lineHeight: 1
    fontFeature: "tnum"
rounded:
  bar: "8px"
  sm: "12px"
  toggle: "14px"
  md: "20px"
  pill: "999px"
spacing:
  xs: "4px"
  sm: "8px"
  md: "16px"
  block: "18px"
  lg: "26px"
components:
  top-bar:
    backgroundColor: "{colors.seaside-blue}"
    textColor: "{colors.on-sea}"
    height: "64px"
  search:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.harbor-ink}"
    typography: "{typography.body}"
    rounded: "{rounded.pill}"
    padding: "0 14px"
    height: "44px"
  button-filter:
    backgroundColor: "{colors.pineapple-yellow}"
    textColor: "{colors.harbor-ink}"
    typography: "{typography.label}"
    rounded: "{rounded.pill}"
    padding: "0 16px"
    height: "44px"
  range:
    backgroundColor: "transparent"
    textColor: "{colors.on-sea}"
    typography: "{typography.label}"
    rounded: "{rounded.pill}"
    padding: "0 16px"
    height: "36px"
  range-selected:
    backgroundColor: "{colors.on-sea}"
    textColor: "{colors.harbor-ink}"
  strip-day:
    textColor: "{colors.on-sea}"
    rounded: "{rounded.sm}"
    width: "46px"
  strip-day-current:
    backgroundColor: "{colors.on-sea}"
    textColor: "{colors.harbor-ink}"
  segmented:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.muted-ink}"
    typography: "{typography.label}"
    rounded: "{rounded.pill}"
    height: "34px"
  segmented-selected:
    backgroundColor: "{colors.harbor-ink}"
    textColor: "{colors.newsprint}"
  active-filter:
    backgroundColor: "{colors.pineapple-yellow}"
    textColor: "{colors.harbor-ink}"
    typography: "{typography.label}"
    rounded: "{rounded.pill}"
    padding: "0 8px 0 12px"
    height: "32px"
  day-block:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.harbor-ink}"
    rounded: "{rounded.md}"
  day-head:
    backgroundColor: "{colors.surface-warm}"
    textColor: "{colors.seaside-blue}"
    typography: "{typography.numeral}"
    padding: "10px 16px"
  day-rel:
    backgroundColor: "{colors.cijin-sunset}"
    textColor: "{colors.harbor-ink}"
    typography: "{typography.label}"
    rounded: "{rounded.pill}"
    padding: "0 10px"
  event-row:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.harbor-ink}"
    typography: "{typography.title}"
    padding: "8px 10px 8px 16px"
  tag:
    backgroundColor: "{colors.surface-warm}"
    textColor: "{colors.muted-ink}"
    rounded: "{rounded.pill}"
    padding: "0 8px"
  tag-new:
    backgroundColor: "{colors.pineapple-yellow}"
    textColor: "{colors.harbor-ink}"
  chip:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.harbor-ink}"
    typography: "{typography.label}"
    rounded: "{rounded.pill}"
    padding: "4px 14px"
    height: "38px"
  chip-selected:
    backgroundColor: "{colors.harbor-ink}"
    textColor: "{colors.newsprint}"
  button-ghost:
    backgroundColor: "transparent"
    textColor: "{colors.harbor-ink}"
    typography: "{typography.label}"
    rounded: "{rounded.pill}"
    padding: "6px 16px"
    height: "40px"
  button-ghost-hover:
    backgroundColor: "{colors.cijin-sunset}"
    textColor: "{colors.harbor-ink}"
  button-primary:
    backgroundColor: "{colors.seaside-blue}"
    textColor: "{colors.on-sea}"
    typography: "{typography.label}"
    rounded: "{rounded.pill}"
    padding: "6px 18px"
    height: "44px"
  input:
    backgroundColor: "{colors.surface-warm}"
    textColor: "{colors.harbor-ink}"
    typography: "{typography.body}"
    rounded: "{rounded.sm}"
    padding: "8px 12px"
    height: "44px"
  panel:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.harbor-ink}"
    rounded: "{rounded.md}"
    width: "460px"
  footer:
    backgroundColor: "{colors.harbor-ink}"
    textColor: "{colors.newsprint}"
---

# Design System: 高雄活動雷達

## Overview

**Creative North Star: "高雄週末口袋地圖"**

這是一份讓人週末前翻開、隨手就能找到去處的在地小冊。它的語言借自港邊的布告欄與手作海報：西子灣海藍的大色塊、鳳梨黃與旗津夕陽橘的強調，全部用夜港墨的粗線描邊，再壓上一層硬陰影，像一張張貼上去、摸得到邊緣的紙片。氣質是熱鬧、親切、有手感，但使用者是來找活動的，不是來欣賞版面的。

活動變多之後，版面的任務是「先選時段、再掃清單、點開看細節」：
1. **選時段**：黏在頂端的海藍頂列放搜尋、月曆、篩選，桌機下面一排時段按鈕（今天、明天、本週末、下週末、7 天內、30 天內），再下面是顯示每天場次與熱度的日期條。
2. **掃清單**：一天一個區塊，一列一筆活動，時間、標題、地點、標籤、愛心排成一行，同一天同名同場地的多個時段合併。
3. **看細節**：點一列就從右側滑出詳情抽屜（手機是底部面板），列出全部場次與來源連結。

表現力集中在頂列（雷達標誌、會漂的浪花邊、日期條）、日期標頭的大數字與「今天／明天」徽章、按得下去的按鈕，以及頁尾的雙層夜浪。其他地方保持米黃報紙底與墨色文字，讓資訊說話。

深色模式不是反白，而是「夜裡的港口」：底色換成深海藍（#0e1630），墨線改成較亮的藍灰，強調色略提亮，分類色往白混合以維持對比。

**Key Characteristics:**
- 墨線描邊（2px）加零模糊的硬陰影，是整套系統的深度語言
- 圓潤字體（Chiron GoRound TC）負責所有標題、標籤與按鈕；內文用系統黑體
- 每個活動分類有一個主色，左側色條、淺底與文字色都由它以 `color-mix` 推出
- 數字用 Fredoka 與等寬數字：日期標頭、日期條、時間、計數
- 海浪是唯一的裝飾母題：頂列下緣的浪花、收合處的細浪、頁尾的雙層浪

## Colors

港都海報的套色：一個海藍、兩個暖色強調、一個墨色，其餘都是紙。

### Primary
- **西子灣海藍** (seaside-blue)：頂列底色、月曆星期列、今日日期圓點、日期標頭的大數字、「還有 N 場」的文字，以及篩選面板唯一的主要按鈕「顯示活動」。
- **西子灣深海** (seaside-blue-deep)：雷達標誌的圓盤、站名的錯位字影。
- **海報米白** (on-sea)：海藍上的文字、時段按鈕選取底、日期條目前那天的底。

### Secondary
- **鳳梨黃** (pineapple-yellow)：篩選按鈕、已套用條件的膠囊、「新增」標籤、日期條的熱度柱、選取中的計數、「已報名」票券的填色、文字選取底色、輸入框焦點光圈。
- **旗津夕陽橘** (cijin-sunset)：「今天／明天」徽章、日期條目前那天的熱度柱、「想去」愛心、焦點外框、游標與表單 accent、次要按鈕的 hover 底、標題 hover 底線。

### Tertiary
- **時間橘** (time-orange)：清單每列的時間，以及週末日期標頭的數字與星期，讓「什麼時候」第一眼就跳出來。它是夕陽橘的深色版，確保白底上的文字對比。

### Neutral
- **夜港墨** (harbor-ink)：內文、描邊、硬陰影、頁尾底色。黃、橘色塊上的文字一律用它，不用白。
- **米黃報紙** (newsprint)：頁面底色，也是頁尾上的文字色。
- **白紙** (surface)：日期區塊、面板、按鈕、搜尋框底。
- **暖白** (surface-warm)：日期標頭、輸入框、標籤、場次膠囊、來源連結的底，比白紙稍暖一階。
- **淡墨** (muted-ink)：地點、場次副行、提示文字、未選取的分頁。
- **紙邊線** (line-soft)：月曆格線、面板內分隔、標籤描邊、計數膠囊底、細浪分隔線。
- **列線** (row-line)：清單每列之間的 1px 分隔，比紙邊線更淡。

### 分類色
展覽藍、表演桃紅、講座紫、節慶橘、市集褐、親子綠、運動青、其他灰。每個分類只宣告一個 `--hue`，清單左側 4px 色條與分類簡稱用文字色（深色模式 45% 混白），列 hover 底、詳情的分類膠囊、選取中的場次用淺底（16% 混白，深色模式 30% 混底色）。

### Named Rules
**The 墨字上色塊 Rule.** 鳳梨黃與夕陽橘上的文字永遠是夜港墨（#15213f），不論淺色或深色模式；暖色塊上不放白字。

**The 一色一分類 Rule.** 新增分類只能加一個 `--hue`，不得另外手寫淺底或文字色；深淺一律交給 `color-mix`。

**The 海藍是面 Rule.** 西子灣海藍用於大面積的品牌面（頂列、月曆星期列）與日期數字。按鈕只有一個例外：篩選面板底部的「顯示活動」。其他可點的東西靠墨線與硬陰影辨識，不做成海藍按鈕或海藍連結。

## Typography

**Display Font:** Chiron GoRound TC（備援 Noto Sans TC、PingFang TC、Microsoft JhengHei）
**Body Font:** Noto Sans TC（備援 PingFang TC、Microsoft JhengHei、system-ui）
**Numeral Font:** Fredoka（日期、時間、計數）

**Character:** 圓頭的 Chiron GoRound 帶來糖果般的親切感，粗到 800–900 時像手寫海報字；內文退回系統黑體，確保長地址與簡介讀得順。Fredoka 的圓潤數字和中文圓體同一個口氣。

### Hierarchy
- **Brand**（900，1.3rem，字距 0.04em）：頂列站名，配 2px 錯位的深海色字影；手機隱藏，只留標誌。
- **Headline**（900，1.4rem，行高 1.35）：詳情抽屜的活動標題、月曆年月；篩選面板標題 1.2rem。
- **Title**（700，1rem，行高 1.35）：清單列的活動標題，最多兩行（`-webkit-line-clamp: 2`）；手機 0.97rem。
- **Body**（400，16px，行高 1.6）：頁面基準；列的副行（分類・地點・行政區）0.85rem，簡介 0.93rem。
- **Label**（800，0.85rem）：欄位標籤、按鈕、chip、分頁、膠囊，全部用圓體；標籤 0.75rem、700。
- **Numeral**（Fredoka 700）：日期標頭 1.9rem（手機 1.6rem）、日期條 1.05rem、列的時間 1rem、計數 0.7–0.85rem。

### Named Rules
**The 圓體發聲 Rule.** 凡是介面在「說話」的地方（標題、標籤、按鈕、chip、狀態）都用 Chiron GoRound；凡是資料（地址、主辦、簡介、表格內容）都用內文黑體。

**The 數字對齊 Rule.** 任何會並排比較的數字（日期、時間、計數、筆數）都開 `tabular-nums`。

## Layout

單欄，頂列內容與主區都限寬 1080px，左右 16px 邊距（全螢幕 PWA 時改用 safe-area inset）；頁尾內容 1280px。篩選不再佔側欄，收進右側面板，已套用的條件以黃色膠囊列在清單上方，可逐一移除。

**頂列**（sticky，z-index 20）由上而下三層：64px 高的標誌＋搜尋＋月曆＋篩選；時段按鈕（桌機）；日期條。頂列實際高度由 `ResizeObserver` 寫進 `--stick`，日期標頭與月曆當日清單都黏在它下方。

**日期條**：每天一格 46px，顯示星期、日子、熱度柱（以當期最多場的一天為滿）與場次數。桌機點了捲到那天，捲動時目前那天跟著亮起；範圍只有一兩天、超過 62 天、在「長期展覽」分頁或「依活動」檢視時隱藏。手機一次只看一天，日期條從今天起列 60 天，兩側有前一天／後一天箭頭。

**主區**：更新時間 → 分頁（單日活動／長期展覽）與檢視切換（依日期／依活動，僅桌機）→ 已套用條件 → 清單。清單一天一個區塊，區塊間距 18px；每天先列 12 筆，超過 15 筆時其餘收進「還有 N 場，全部展開」。展期超過 14 天的活動移到「長期展覽」分頁。

**面板**：詳情抽屜 460px、篩選面板 420px，距視窗邊緣 12px，背後一層半透明遮罩，開啟時鎖住頁面捲動。

**月曆**（只顯示有標記的活動，不套用篩選）：1000px 以上月曆格與 340px 寬的當日清單並排，當日清單 sticky；以下改上下排，點日期後捲到當日清單。月曆模式下搜尋與篩選按鈕隱藏（保留位置）。

**640px 以下**：頂列縮成 58px、站名隱藏、篩選按鈕只剩圖示；時段按鈕與自訂日期隱藏，改用日期條選日子；清單列改成兩行（時間｜標題＋標籤｜愛心）；面板改成底部 88vh 的面板；月曆的活動橫條縮成 10px 色條。

節奏：元件內 4–8px，列內 12px，日期區塊之間 18px，月曆長期區塊前 36px，頁尾前 56px。

## Elevation & Depth

整套系統只用一種深度：**零模糊、往右下偏移的夜港墨硬陰影**，搭配 2px 墨線描邊，讓每個元件像一張貼在紙上的厚紙片。深度表達的是「可以按」與「浮在上面」，而不是光影。深色模式陰影色換成近黑（#050916），仍是硬邊。

### Shadow Vocabulary
- **紙片**（`box-shadow: 4px 4px 0 var(--shadow-c)`）：日期區塊、月曆格。
- **抽屜**（`box-shadow: -6px 6px 0 var(--shadow-c)`）：從右側滑出的詳情與篩選面板，陰影落在左下，像從右邊抽出來的紙。手機的底部面板不加陰影。
- **按鈕**（`box-shadow: 2px 2px 0 var(--shadow-c)`）：篩選按鈕、chip、月曆箭頭、「顯示活動」；hover 時 3px 並往左上 1px，按下時陰影歸零並往右下 2px。
- **切換鈕**（`box-shadow: 3px 3px 0 var(--shadow-c)`）：月曆／列表切換鈕；hover 4px，按下往右下 3px。

清單列、時段按鈕、日期條、分頁、愛心不加陰影：它們是同一張紙上的內容，不是另外貼上去的紙片。

### Named Rules
**The 按得下去 Rule.** 有硬陰影的東西就必須能互動或代表一張紙片；按下時陰影歸零、元件位移到陰影的位置，像真的被壓下去。不可點的裝飾不加硬陰影。

**The 無柔光 Rule.** 不使用模糊陰影、發光暈或毛玻璃。焦點用 3px 夕陽橘外框或鳳梨黃光圈表示，不用陰影模擬。唯一的半透明是面板背後的遮罩。

## Shapes

大圓角加粗墨線，像圓角裁切的貼紙。日期區塊與面板 20px（手機底部面板上緣 22px），輸入框、日期條格子、來源連結 12px，月曆切換鈕 14px，所有按鈕、chip、標籤、徽章、搜尋框、分頁都是完整膠囊（999px）。月曆跨日橫條 8px，延續到下一格的一側取消圓角與邊線，看起來接在一起。

**海浪**是全站唯一的裝飾形狀，三處都用同一個語彙：
- **頂列浪花邊**：頂列下緣 14px 高、週期 60px 的浪，海藍浪花疊在往下錯開 3px 的墨線浪上，14 秒一輪緩慢往右漂。以 CSS mask（`--wave-mask`）畫，顏色由 `background` 決定。
- **細浪分隔線**：「還有 N 場」上方一道 8px 高、週期 30px 的紙邊線色細浪（`--wave-line`）。
- **頁尾雙層浪**：頁尾上緣 46px 高的 SVG，前浪是米黃底色，後浪相位錯開、露出一道海藍與夜港墨混成的藍。

圖示是同一套自繪 SVG：24px 格線、2px 圓頭線條、無填色；被選取的標記（想去愛心、已報名票券）才填色，票券的撕線用 `--tear` 挖空。月曆切換鈕的圖示是唯一的彩色小插圖，hover 時傾斜 -6°。

## Components

### Top Bar（頂列）
西子灣海藍、米白字，捲動時黏住頂端。左邊是會掃描的雷達標誌（40px，5 秒一圈、兩個光點閃爍）與站名；中間是白底墨框的膠囊搜尋框（44px 高、最寬 480px，焦點時整顆套上鳳梨黃光圈）；右邊是月曆切換鈕與篩選按鈕。

### Filter Button（篩選）
鳳梨黃底、墨框、2px 硬陰影的膠囊，44px 高，滑桿圖示＋「篩選」。有套用條件時後面接一顆墨底米黃字的 Fredoka 計數徽章。

### Range Buttons（時段，桌機）
海藍上的線框膠囊，36px 高，邊線是 45% 的米白；hover 填上 14% 米白，選取時整顆填滿米白、文字轉墨色。預設選「本週末」。

### Date Strip（日期條）
海藍上一排 46px 的小格，每格由上而下：星期（圓體 0.72rem，週末鳳梨黃）、日子（Fredoka 1.05rem）、16px 高的熱度柱（鳳梨黃）、場次數。目前那天反白成米白底墨框，星期轉時間橘、熱度柱轉夕陽橘。沒有活動的日子半透明且不可點。手機兩側加 34×64px 的半透明箭頭。

### Tabs & Group Toggle（分頁與檢視切換）
白底墨框的膠囊分段控制，內含 34px 高的按鈕；選取的那顆反轉成墨底米黃字。分頁標籤後接 Fredoka 的筆數。

### Active Filters（已套用條件）
鳳梨黃底墨框的 32px 膠囊，條件名稱＋小叉叉，點一下移除；最後一個是底線文字「清除」。

### Day Block（日期區塊）
白紙、2px 墨框、20px 圓角、4px 紙片陰影；不能 `overflow: hidden`，否則標頭的 sticky 會失效。
- **Day Head**：暖白底、下緣墨線，sticky 在頂列下方。Fredoka 1.9rem 的海藍日子（週末時間橘，深色模式改政府藍），旁邊兩行「月份／星期」，可接一顆夕陽橘的「今天／明天」膠囊，右側是「N 場」。
- **收合**：超過 15 筆時先列 12 筆，底部是細浪分隔線＋海藍文字的「還有 N 場，全部展開」（深色模式鳳梨黃）。

### Event Row（清單列）
全站的主角。一列四欄：64px 時間｜標題與副行｜標籤｜40px 愛心。
- **左側色條**：4px 寬、上下各留 10px 的分類色條。
- **時間**：Fredoka 700 時間橘；第二行淡墨 0.74rem（結束時間或「整天」等）。
- **標題**：圓體 700，最多兩行；hover 時加 2px 夕陽橘底線。下面一行副行：分類簡稱（分類色）・地點・行政區，地點過長以省略號截斷。
- **標籤**：靠右排列，見 Tags。
- **愛心**：無框的 40px 圓鈕，平常是淡化的淡墨空心愛心；點一下變夕陽橘實心（想去），再點取消。已報名的列改顯示鳳梨黃實心票券。
- **Hover**：整列鋪上該分類淺底與白紙 55% 混合的底色。
- 列與列之間是 1px 列線，整列（除了愛心）點下去開詳情。

### Tags
1px 紙邊線的小膠囊，暖白底、淡墨字、圓體 700 0.75rem。
- **免費**：民間綠的淡底與綠字綠框。
- **新增**：鳳梨黃底、墨框墨字。
- **政府／民間**（詳情）：只描邊，用政府藍與民間綠。
- **N 天／另 N 天**：中性樣式，表示合併的多天場次。

### Panel（詳情抽屜與篩選面板）
白紙、2px 墨框、20px 圓角、往左下的 6px 硬陰影，從右側滑入（0.28s）；手機改為從底部滑上的面板。右上角是 40px 的圓形關閉鈕，hover 填夕陽橘。
- **詳情**：分類膠囊（分類淺底＋分類色字＋圖示）與「新增」標籤 → 1.4rem 標題 → 「想去」「已報名」兩顆 chip → 以圖示為標頭的資訊表（時間與全部場次、地點、主辦與政府／民間標籤、費用）→ 簡介 → 來源連結。場次是暖白小膠囊，目前這場用分類色框與淺底標出。來源連結是暖白底、墨框、12px 圓角的整列按鈕，hover 填鳳梨黃。
- **篩選**：標題列 → 分類、費用、我的標記與新增（含分享同步連結）、自訂日期（僅桌機）、行政區、來源 → 底部固定的「清除全部」（ghost）與「顯示活動」（海藍 primary）。

### Buttons
厚實、按得下去，像實體貼紙。
- **Shape:** 膠囊（999px），2px 墨線，最小高度 40px。
- **Ghost（清除全部、分享同步連結、今天）：** 透明底、墨字、圓體 800；hover 時整顆填滿夕陽橘、文字維持墨色。
- **Primary（顯示活動）：** 海藍底、米白字、2px 硬陰影，44px 高，撐滿剩餘寬度；按下時陰影歸零。
- **View toggle（月曆／列表）：** 44px 方形（手機 42px）、14px 圓角、3px 硬陰影，內放彩色小插圖（列表時是橘頂條月曆，月曆時是兩張疊起的橘頂條活動卡片，都帶一顆鳳梨黃標記點）；hover 圖示傾斜 -6°。深色模式下底色維持海報米白，讓墨線不會消失。
- **Disabled:** 透明度 0.35、移除陰影、游標 not-allowed。

### Chips
- **Style:** 白底、墨線、2px 硬陰影、圓體 700 0.9rem，最小高度 38px，可帶分類色圖示與計數膠囊（紙邊線底、Fredoka 數字）。
- **State:** 選取時反轉成墨底米黃字，計數膠囊變鳳梨黃；分類 chip 選取時改用該分類的淺底與分類色描邊。標記 chip 的圖示平常是夕陽橘愛心與時間橘票券，選取時填實。

### Inputs / Fields
- **Style:** 暖白底、2px 墨線、12px 圓角、最小高度 44px；標籤在上方，用圓體 800 0.85rem。
- **Focus:** 底色轉白，外加 3px 鳳梨黃光圈（無外框）。
- **Date:** iOS Safari 的日期欄另外重設外觀，文字靠左、空值不塌陷。

### Empty State
置中的 64px 雷達線稿（海藍，深色模式鳳梨黃）、一句說明，必要時附「改看 30 天內」之類的快捷按鈕。

### Calendar（我的標記月曆）
白紙墨框的月曆格，星期列是海藍底米白字（週末鳳梨黃）；今天的日期是海藍圓點，選取的日期鋪鳳梨黃淡底加 3px 內框。每週最多畫三條跨日橫條：想去是白底夕陽橘框加空心愛心，已報名是鳳梨黃底墨框加實心票券，超出的以「+N」表示。展期超過 14 天的活動不畫在格子上，列在下方「本月可去的長期活動」。

### Footer（夜港）
夜港墨底、米黃字、上緣雙層浪；來源狀態表格用淡藍灰線分隔，時間與筆數不換行，失敗列以淡紅底與粉紅字標示並附錯誤訊息。

## Motion

- **Ease:** `cubic-bezier(0.22, 1, 0.36, 1)`，所有位移與面板滑入都用它。
- **按壓：** 0.18s，按鈕與 chip 的浮起與壓下。
- **面板：** 桌機從右側 30px 滑入、手機從下方 40px 滑上（0.28s），遮罩淡入 0.2s。
- **雷達：** 標誌 5 秒一圈，兩個光點錯開閃爍。
- **浪花：** 頂列浪花 14 秒一輪往右漂。
- **捲動：** 桌機點日期條時平滑捲到那天，減少動態效果時直接跳。
- `prefers-reduced-motion: reduce` 時關閉所有動畫與轉場，浪花與雷達都靜止。

## Do's and Don'ts

### Do:
- **Do** 讓所有可點的紙片元件同時具備 2px 墨線與硬陰影，並在 `:active` 時位移到陰影的位置、陰影歸零。
- **Do** 新增分類時只宣告一個 `--hue`，色條、淺底與文字色交給既有的 `color-mix` 規則。
- **Do** 在鳳梨黃、夕陽橘底上一律使用夜港墨（#15213f）文字與描邊，深色模式也一樣。
- **Do** 主題化瀏覽器自帶的表面：選取底色用鳳梨黃、游標與 accent 用夕陽橘、捲軸用淡化的墨色。
- **Do** 數字一律等寬（`tabular-nums`），日期與時間用 Fredoka。
- **Do** 新的 sticky 元素以 `--stick` 為頂端，不要寫死頂列高度。
- **Do** 改了 `style.css` 或 `app.js` 就更新 `index.html` 裡的 `?v=`。

### Don't:
- **Don't** 使用模糊陰影、發光暈、毛玻璃或漸層文字；深度只有硬陰影一種。
- **Don't** 把西子灣海藍做成一般按鈕或連結色；它是頂列與月曆的品牌面，按鈕只有「顯示活動」一個例外。
- **Don't** 在暖色塊上放白字，或用灰色文字放在彩色底上。
- **Don't** 在標題、按鈕、標籤上改用內文黑體，或在長段資料上用圓體。
- **Don't** 用 emoji 或 Unicode 符號代替圖示；沿用 24px 格線、2px 圓頭線條的自繪 SVG。
- **Don't** 把清單列做回卡片或加上硬陰影；清單要好掃，一列一筆、靠色條與列線分隔。
- **Don't** 另外發明裝飾圖形；需要分隔或收尾時沿用 `--wave-mask`、`--wave-line` 的海浪。
