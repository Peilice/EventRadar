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
  display:
    fontFamily: "Chiron GoRound TC, Noto Sans TC, PingFang TC, Microsoft JhengHei, system-ui, sans-serif"
    fontSize: "clamp(2rem, 6vw, 3.4rem)"
    fontWeight: 900
    lineHeight: 1.1
    letterSpacing: "0.04em"
  headline:
    fontFamily: "Chiron GoRound TC, Noto Sans TC, PingFang TC, Microsoft JhengHei, system-ui, sans-serif"
    fontSize: "1.4rem"
    fontWeight: 900
  title:
    fontFamily: "Chiron GoRound TC, Noto Sans TC, PingFang TC, Microsoft JhengHei, system-ui, sans-serif"
    fontSize: "1.12rem"
    fontWeight: 800
    lineHeight: 1.4
  body:
    fontFamily: "Noto Sans TC, PingFang TC, Microsoft JhengHei, system-ui, -apple-system, Segoe UI, sans-serif"
    fontSize: "16px"
    fontWeight: 400
    lineHeight: 1.6
  body-small:
    fontFamily: "Noto Sans TC, PingFang TC, Microsoft JhengHei, system-ui, -apple-system, Segoe UI, sans-serif"
    fontSize: "0.9rem"
    fontWeight: 400
    lineHeight: 1.5
  label:
    fontFamily: "Chiron GoRound TC, Noto Sans TC, PingFang TC, Microsoft JhengHei, system-ui, sans-serif"
    fontSize: "0.85rem"
    fontWeight: 800
  numeral:
    fontFamily: "Fredoka, Chiron GoRound TC, sans-serif"
    fontSize: "2.1rem"
    fontWeight: 700
    lineHeight: 1
    fontFeature: "tnum"
rounded:
  bar: "8px"
  sm: "12px"
  ticket: "14px"
  md: "20px"
  pill: "999px"
spacing:
  xs: "4px"
  sm: "8px"
  md: "16px"
  gutter: "18px"
  lg: "28px"
components:
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
  mark-want-pressed:
    backgroundColor: "{colors.cijin-sunset}"
    textColor: "{colors.harbor-ink}"
    rounded: "{rounded.pill}"
    padding: "2px 10px"
    height: "32px"
  mark-going-pressed:
    backgroundColor: "{colors.pineapple-yellow}"
    textColor: "{colors.harbor-ink}"
    rounded: "{rounded.pill}"
    padding: "2px 10px"
    height: "32px"
  input:
    backgroundColor: "{colors.surface-warm}"
    textColor: "{colors.harbor-ink}"
    typography: "{typography.body}"
    rounded: "{rounded.sm}"
    padding: "8px 12px"
    height: "44px"
  event-card:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.harbor-ink}"
    rounded: "{rounded.md}"
    padding: "0 16px 14px"
  day-ticket:
    backgroundColor: "{colors.pineapple-yellow}"
    textColor: "{colors.harbor-ink}"
    typography: "{typography.numeral}"
    rounded: "{rounded.ticket}"
    padding: "4px 18px 4px 14px"
  day-ticket-weekend:
    backgroundColor: "{colors.cijin-sunset}"
  hero:
    backgroundColor: "{colors.seaside-blue}"
    textColor: "{colors.on-sea}"
    typography: "{typography.display}"
  footer:
    backgroundColor: "{colors.harbor-ink}"
    textColor: "{colors.newsprint}"
---

# Design System: 高雄活動雷達

## Overview

**Creative North Star: "高雄週末口袋地圖"**

這是一份讓人週末前翻開、隨手就能找到去處的在地小冊。它的語言借自港邊的布告欄與手作海報：西子灣海藍的大色塊、鳳梨黃的太陽、旗津夕陽橘的強調，全部用夜港墨的粗線描邊，再壓上一層硬陰影，像一張張貼上去、摸得到邊緣的紙片。氣質是熱鬧、親切、有手感：色塊大膽，但每張卡片的時間、地點、主辦都排得清楚好掃，因為使用者是來找活動的，不是來欣賞版面的。

密度屬於「工具」等級：桌機是左側篩選欄加卡片看板，手機收成單欄。所有表現力集中在幾個固定位置：頁首海報（雷達標誌、太陽、網點、波浪）、日期票根、分類色頂條、按得下去的按鈕。其他地方保持米黃報紙底與墨色文字，讓資訊說話。

深色模式不是反白，而是「夜裡的港口」：底色換成深海藍（#0e1630），墨線改成較亮的藍灰，強調色略提亮，分類色往白混合以維持對比。

**Key Characteristics:**
- 墨線描邊（2px）加零模糊的硬陰影，是整套系統的深度語言
- 圓潤字體（Chiron GoRound TC）負責所有標題、標籤與按鈕；內文用系統黑體
- 每個活動分類有一個主色，淺底與文字色都由它以 `color-mix` 推出
- 數字用 Fredoka 與等寬數字，日期像票根一樣被撕下來
- 頁首與頁尾用波浪邊界接到米黃底，上方是白天的港、下方是夜港

## Colors

港都海報的套色：一個海藍、兩個暖色強調、一個墨色，其餘都是紙。

### Primary
- **西子灣海藍** (seaside-blue)：頁首大色塊、月曆星期列、「今天」徽章、今日日期圓點。是品牌的面，不拿來當按鈕底色。
- **西子灣深海** (seaside-blue-deep)：雷達標誌的圓盤、標題的錯位陰影、頁首資訊膠囊的底。

### Secondary
- **鳳梨黃** (pineapple-yellow)：平日的日期票根、「免費」標籤、選取中的計數、「已報名」按下狀態、文字選取底色、輸入框焦點光圈。
- **旗津夕陽橘** (cijin-sunset)：週末的日期票根、「新」標籤、「想去」按下狀態、焦點外框、游標與表單 accent、次要按鈕的 hover 底。

### Tertiary
- **時間橘** (time-orange)：只用在活動時間那一行，讓「什麼時候」在卡片裡第一眼就跳出來。它是夕陽橘的深色版，用來確保白底上的文字對比。

### Neutral
- **夜港墨** (harbor-ink)：內文、描邊、硬陰影、頁尾底色。黃、橘色塊上的文字一律用它，不用白。
- **米黃報紙** (newsprint)：頁面底色，也是頁尾上的文字色。
- **白紙** (surface)：卡片、篩選面板、按鈕底。
- **暖白** (surface-warm)：輸入框與「進行中」區塊的底，比卡片稍暖一階。
- **淡墨** (muted-ink)：地點、主辦、提示文字。
- **紙邊線** (line-soft)：月曆格線、日期標頭的點線、計數膠囊底。

### 分類色
展覽藍、表演桃紅、講座紫、節慶橘、市集褐、親子綠、運動青、其他灰。每個分類只宣告一個 `--hue`，卡片頂條的淺底（16% 混白，深色模式 30% 混底色）與文字色（深色模式 45% 混白）都由它推算。

### Named Rules
**The 墨字上色塊 Rule.** 鳳梨黃與夕陽橘上的文字永遠是夜港墨（#15213f），不論淺色或深色模式；暖色塊上不放白字。

**The 一色一分類 Rule.** 新增分類只能加一個 `--hue`，不得另外手寫淺底或文字色；深淺一律交給 `color-mix`。

**The 海藍是面 Rule.** 西子灣海藍用於大面積的品牌面（頁首、月曆頭），不做成按鈕或連結色；可點的東西靠墨線與硬陰影辨識。

## Typography

**Display Font:** Chiron GoRound TC（備援 Noto Sans TC、PingFang TC、Microsoft JhengHei）
**Body Font:** Noto Sans TC（備援 PingFang TC、Microsoft JhengHei、system-ui）
**Numeral Font:** Fredoka（只用於日期大數字、計數與月曆日期）

**Character:** 圓頭的 Chiron GoRound 帶來糖果般的親切感，粗到 800–900 時像手寫海報字；內文退回系統黑體，確保長地址與主辦單位讀得順。Fredoka 的圓潤數字和中文圓體同一個口氣。

### Hierarchy
- **Display**（900，clamp(2rem, 6vw, 3.4rem)，行高 1.1，字距 0.04em）：只有頁首站名，配 3px 錯位的深海色字影（手機 2px）。
- **Headline**（900，1.4rem）：月曆的年月標題。
- **Title**（800，1.12rem，行高 1.4）：活動標題，`text-wrap: balance`，長字串可任意斷行。
- **Body**（400，16px，行高 1.6）：頁面基準；卡片內的時間、地點、主辦用 0.9rem、行高 1.5。
- **Label**（800，0.85rem）：欄位標籤、分類頂條、按鈕、chip、膠囊，全部用圓體。
- **Numeral**（Fredoka 700，2.1rem，行高 1，等寬數字）：日期票根上的日子；計數用 0.78rem。

### Named Rules
**The 圓體發聲 Rule.** 凡是介面在「說話」的地方（標題、標籤、按鈕、chip、狀態）都用 Chiron GoRound；凡是資料（地址、主辦、簡介、表格內容）都用內文黑體。

**The 數字對齊 Rule.** 任何會並排比較的數字（日期、計數、筆數、時間）都開 `tabular-nums`。

## Layout

最大寬度 1280px，左右 16px 邊距（全螢幕 PWA 時改用 safe-area inset）。1000px 以上切成兩欄：左側 320px 篩選欄 sticky 黏在頂端 16px、可獨立捲動，右側卡片看板，欄距 28px。月曆模式下側欄隱藏，月曆格與 340px 寬的當日清單並排。

卡片看板用 `auto-fill` 網格，每張最小 300px，間距 18px（手機 14px），同列卡片等高，來源連結推到卡片底部。日期標頭橫跨整列並 sticky，底緣以 10px 漸層淡出，讓卡片滑進去時不被切齊。

頁首下緣與頁尾上緣都是 34px 高的正弦波浪，把海藍與夜港墨接到米黃底。640px 以下：頁首縮小、太陽移到右上角、月曆的活動橫條縮成 10px 色條。

節奏：元件內 4–8px，欄位之間 16px，區塊之間 36px，頁尾前 56px。

## Elevation & Depth

整套系統只用一種深度：**零模糊、往右下偏移的夜港墨硬陰影**，搭配 2px 墨線描邊，讓每個元件像一張貼在紙上的厚紙片。深度表達的是「可以按」與「浮在上面」，而不是光影。深色模式陰影色換成近黑（#050916），仍是硬邊。

### Shadow Vocabulary
- **紙片**（`box-shadow: 4px 4px 0 var(--shadow-c)`）：活動卡片、篩選面板、月曆格、「進行中」區塊。
- **浮起的紙片**（`box-shadow: 7px 7px 0 var(--shadow-c)`，同時 `translate(-3px, -3px)`）：卡片 hover 與內部取得焦點時。
- **按鈕**（`box-shadow: 2px 2px 0 var(--shadow-c)`）：chip、想去／已報名、月曆箭頭；hover 時 3px 並往左上 1px，按下時陰影歸零並往右下 2px。
- **票根與切換鈕**（`box-shadow: 3px 3px 0 var(--shadow-c)`）：日期票根、月曆／首頁切換鈕。

### Named Rules
**The 按得下去 Rule.** 有硬陰影的東西就必須能互動或代表一張紙片；按下時陰影歸零、元件位移到陰影的位置，像真的被壓下去。不可點的裝飾不加硬陰影。

**The 無柔光 Rule.** 不使用模糊陰影、發光暈或毛玻璃。焦點用 3px 夕陽橘外框或鳳梨黃光圈表示，不用陰影模擬。

## Shapes

大圓角加粗墨線，像圓角裁切的貼紙。卡片與面板 20px，輸入框 12px，日期票根 14px 且左右各挖一個 7px 半圓缺口（CSS mask），所有按鈕、chip、標籤、徽章都是完整膠囊（999px）。月曆跨日橫條 8px，延續到下一格的一側取消圓角與邊線，看起來接在一起。

圖示是同一套自繪 SVG：24px 格線、2px 圓頭線條、無填色；被選取的標記（想去愛心、已報名票券）才填色。頁首的「今天」徽章刻意旋轉 -4°，是全站唯一的歪斜。

## Components

### Buttons
厚實、按得下去，像實體貼紙。
- **Shape:** 膠囊（999px），2px 墨線，最小高度 40px。
- **Ghost（清除篩選、分享同步連結、今天）：** 透明底、墨字、圓體 800；hover 時整顆填滿夕陽橘、文字維持墨色。
- **View toggle（月曆／首頁）：** 46px 方形、14px 圓角、3px 硬陰影，內放彩色小插圖（橘頂條月曆、橘屋頂小屋）；hover 圖示傾斜 -6°。
- **Disabled:** 透明度 0.35、移除陰影、游標 not-allowed。

### Chips
- **Style:** 白底、墨線、2px 硬陰影、圓體 700 0.9rem，可帶分類色圖示與計數膠囊（紙邊線底、Fredoka 數字）。
- **State:** 選取時反轉成墨底米黃字，計數膠囊變鳳梨黃；分類 chip 選取時改用該分類的淺底與分類色描邊。

### Mark buttons（想去／已報名）
疊在卡片頂條右側，32px 高的小膠囊，平常是白底淡墨字加空心圖示。按下後「想去」變夕陽橘底、「已報名」變鳳梨黃底，文字與描邊固定夜港墨，圖示填實（票券的撕線用按鈕底色挖空）。

### Cards / Containers
- **Corner Style:** 20px。
- **Background:** 白紙；頂部是分類色淺底的頂條，以 2px 墨線與內文分隔，頂條放分類圖示、分類名（分類色）與標記按鈕。
- **Shadow Strategy:** 紙片 4px，hover 浮起到 7px（見 Elevation & Depth）。
- **Border:** 2px 夜港墨。
- **Internal Padding:** 左右 16px、底 14px。
- **內容順序：** 標題 → 時間（時間橘、粗體）→ 地點 → 主辦 → 標籤 → 簡介（可展開，附旋轉箭頭）→ 來源連結（推到底部）。整張卡片透過標題連結的偽元素可點，標記、簡介、來源連結疊在其上。

### Inputs / Fields
- **Style:** 暖白底、2px 墨線、12px 圓角、最小高度 44px；標籤在上方，用圓體 800 0.85rem。
- **Focus:** 底色轉白，外加 3px 鳳梨黃光圈（無外框）。
- **Disabled:** 透明度 0.45。

### Tags
1.5px 墨線小膠囊，圓體 800 0.78rem。「免費」鳳梨黃底、「新」夕陽橘底（皆墨字墨框）；「政府」「民間」只描邊，用政府藍與民間綠。

### Day Ticket（日期票根）
全站的招牌元件。鳳梨黃底（週末改夕陽橘）、墨框、3px 硬陰影、左右半圓缺口，大字 Fredoka 日子加上兩行「月／週幾」。旁邊可接一顆歪斜 -4° 的海藍「今天／明天」徽章，再由一條紙邊線點線延伸到右側的「N 場」計數。sticky 在捲動時黏住頂端。

### Hero（頁首海報）
西子灣海藍色塊，右上角一顆鳳梨黃太陽套夕陽橘光環，右側鋪一層往左淡出的網點；左邊是會掃描的雷達標誌（5 秒一圈、光點閃爍），站名 Display 字配深海錯位字影，底下是資訊膠囊。下緣波浪接米黃底。

### Footer（夜港）
夜港墨底、米黃字、上緣波浪；來源狀態表格用淡藍灰線分隔，時間與筆數不換行，失敗列以淡紅底與粉紅字標示並附錯誤訊息。

## Do's and Don'ts

### Do:
- **Do** 讓所有可點的元件同時具備 2px 墨線與硬陰影，並在 `:active` 時位移到陰影的位置、陰影歸零。
- **Do** 新增分類時只宣告一個 `--hue`，淺底與文字色交給既有的 `color-mix` 規則。
- **Do** 在鳳梨黃、夕陽橘底上一律使用夜港墨（#15213f）文字與描邊，深色模式也一樣。
- **Do** 主題化瀏覽器自帶的表面：選取底色用鳳梨黃、游標與 accent 用夕陽橘、捲軸用淡化的墨色。
- **Do** 數字一律等寬（`tabular-nums`），日期大字用 Fredoka。
- **Do** 改了 `style.css` 或 `app.js` 就更新 `index.html` 裡的 `?v=`。

### Don't:
- **Don't** 使用模糊陰影、發光暈、毛玻璃或漸層文字；深度只有硬陰影一種。
- **Don't** 把西子灣海藍做成按鈕或連結色；它是頁首與月曆頭的品牌面。
- **Don't** 在暖色塊上放白字，或用灰色文字放在彩色底上。
- **Don't** 在標題、按鈕、標籤上改用內文黑體，或在長段資料上用圓體。
- **Don't** 用 emoji 或 Unicode 符號代替圖示；沿用 24px 格線、2px 圓頭線條的自繪 SVG。
- **Don't** 增加第二個歪斜元素；-4° 的「今天」徽章是唯一的俏皮傾斜。
