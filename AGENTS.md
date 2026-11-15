# AGENTS.md：地震預警LLM Wiki的規則

這份文件寫給維護這個Wiki、用Wiki做簡報的AI。改Wiki或簡報之前先讀完；規則和檢查程式的結果不一致時，先回報，不要自己改掉其中一邊。

目前版本：v1（2026-11-15）

## 1. 專案目的

把「地震預警與國家級警報」的公開資料整理成一份LLM Wiki，再只用Wiki的內容做一份給新手的教學HTML簡報。

- 讀者：沒有地震學背景、收過國家級警報的一般人（高中生、大學生）。
- 簡報要讓讀者看完能說明：規模和震度的差別、P波和S波、強震即時警報怎麼算、國家級警報的發布條件、為什麼震央附近會先搖才響、收到警報怎麼做。

## 2. 三層結構

| 層 | 位置 | 誰寫 | 規則 |
|---|---|---|---|
| 原始來源 | `raw/` | `tools/fetch.py` | 寫入後不能修改，`raw/_sources.json` 記SHA-256 |
| Wiki | `wiki/` | AI | 照第4、5節的格式寫，每次修改記在 `wiki/log.md` |
| 規則 | `AGENTS.md` | 學生和AI討論後修改 | 修改要在第10節記版本 |

## 3. 目錄

```
raw/_sources.json      來源清單（候選和已取得）
raw/Sxx-*.md           已取得的原始來源（文字）
wiki/index.md          目錄：每頁一行摘要
wiki/log.md            時序紀錄（只往後加）
wiki/overview.md       主題總覽
wiki/concepts/         單一概念，例如 規模.md、震度.md
wiki/topics/           制度、流程、比較，例如 國家級警報.md
wiki/sources/          每篇來源一頁摘要 Sxx-*.md
wiki/discussions/      討論單 Dxx-*.md（先討論、後生成）
wiki/queries/          查詢結果歸檔 Qxx-*.md（例如簡報大綱）
slides/deck.html       簡報內容（只有各頁的section）
templates/             簡報和網站的版型（AI不改）
tools/                 程式
runs/run-xx/           每次執行的紀錄
docs/                  GitHub Pages輸出（build.py產生，不手改）
```

## 4. 頁面格式

### 4.1 前置資料

每個 `wiki/` 頁面（index.md、log.md 除外）開頭都要有：

```
---
title: 震度
type: concept
summary: 地面上各地搖晃的程度，臺灣分0到7級共10級
sources: [S02, S05]
updated: 2026-11-15
---
```

- `type` 只能是 overview、concept、topic、source、discussion、query。
- `summary` 一句話，會放進 index.md。
- `sources` 列這頁用到的來源編號。

### 4.2 出處

- 每一段和每個清單項目都要有出處標記，寫在句號前：`規模是描述地震大小的絕對尺度〔S02〕。`
- 一句用到兩篇來源就寫兩個：`〔S02〕〔S05〕`。
- 只放連結的清單項目（例如「相關頁面」一節）不用出處。

### 4.3 引文

- 「」裡接著出處標記的是引文：`「預估規模5.0以上」〔S05〕`，引文要和raw原文逐字相同（空白不算）。原文裡的「」在引文裡改成『』。
- 沒有出處標記的「」只能放名稱或用語，12個字以內，例如「趴下、掩護、穩住」。
- 文章、網頁的標題用〈〉，例如〈地震防護〉，不用「」。

### 4.4 數字

- 有出處的句子裡，阿拉伯數字要能在那篇來源的原文找到（例如來源寫「規模5.0」，Wiki就寫5.0，不寫成5）。
- 單位換算寫成 `（換算：3.7英里約6.0公里）`，括號裡的數字不檢查，但要在討論單或頁面寫出算法。
- 年份照來源寫法（民國或西元），需要時在括號補另一種：`113年（2024年）`。

### 4.5 日期和不同說法

- 規則、門檻、系統效能這類會改的說法，要寫出是哪一份文件、哪一天的說法。
- 不同來源說法不一樣時，兩種都留，在該頁加一節 `## 不同來源的說法`，列出各自的來源、日期和差在哪；不要自己判斷哪個對，除非有來源說明哪個是現行。

### 4.6 連結

- 頁面之間用相對路徑：`[震度](../concepts/震度.md)`。
- 每頁至少要被一個其他頁面連到（index.md 不算）。
- 檔名用頁面標題，例如 `wiki/concepts/震度.md`；來源摘要用 `Sxx-簡稱.md`。

### 4.7 Markdown範圍

只用：標題（#到###）、段落、清單（可兩層）、表格、粗體、連結、引用區塊（>）。不用HTML、圖片、註腳。

## 5. 各類頁面寫什麼

- **source（來源摘要）**：這篇是誰、何時發布、講什麼；5到10個重點（每點附出處，重要的用引文）；這篇讓哪些頁面新增或修改；最後連到它的討論單。
- **concept**：一句定義、白話說明、和相近概念的差別、常見誤解（有來源才寫）、相關頁面。
- **topic**：制度或流程的步驟、條件、時間；不同年份的變化；不同來源的說法。
- **overview**：用5到8段串起整個主題，每段連到細節頁。
- **discussion（討論單）**：格式見第6.2節。
- **query**：問題、讀了哪些頁、回答（每點附Wiki頁和出處）。

## 6. 流程（graph v1）

```
N0 規劃討論（一次）
  ↓
┌─ 每篇來源重複 ───────────────────────────┐
│ N1 取得資料 → N2 討論 → 學生回覆 → N3 生成/更新頁面 → C1 Wiki檢查 │
│                                  ↑          不通過（最多3次） ↓     │
│                                  └────────── 修改 ─────────────┘     │
└───────────────────────────────────────────┘
  ↓
N4 查詢Wiki → N5 整理重點（大綱）→ N6 產生簡報 → C2 簡報檢查（程式＋AI審查）
                                       ↑      不通過：重生出錯的頁（最多3次）
                                       └────────────┘
                                       Wiki缺資料：回到N1補來源
  ↓
N7 建置與發佈 → 記錄log
```

### 6.1 N1 取得資料

`python3 tools/fetch.py <key>` 從 `raw/_sources.json` 取一篇，自動編號Sxx，存成 `raw/Sxx-key.md`。

### 6.2 N2 討論（先討論、後生成）

AI讀新來源、`wiki/index.md` 和相關頁面後，寫 `wiki/discussions/Dxx-Sxx-簡稱.md`，這時還不能改其他Wiki頁：

```
---
title: 討論單 D01：S01 ……
type: discussion
summary: ……
sources: [S01]
updated: 2026-11-15
---
## AI：這篇的重點
1. ……「引文」〔S01〕
## AI：和現有Wiki的關係
- 新增：……
- 修改：……
- 和其他來源不一致：……
## AI：想問的問題
1. ……
## 學生回覆
（學生寫）
## 決定
（AI依回覆整理：要新增、修改哪些頁）
```

學生回覆後，AI才把「決定」寫完並進入N3。

### 6.3 N3 生成

照討論單的「決定」新增或修改頁面，更新 `wiki/index.md`、`wiki/overview.md`（需要時），最後在 `wiki/log.md` 加一筆。

### 6.4 C1 Wiki檢查

`python3 tools/lint_wiki.py`。有錯誤（E）就回N3修改，最多3次；警告（W）要在log註明為什麼保留。

### 6.5 N4 查詢、N5 大綱

- N4：讀 `wiki/index.md`，選頁，回答「新手要依序懂哪些事才能理解國家級警報」，存成 `wiki/queries/Qxx-*.md`。
- N5：把回答排成簡報大綱，存成 `wiki/queries/Qxx-簡報大綱.md`：每頁寫目的、重點、用到的Wiki頁。

### 6.6 N6 產生簡報

照大綱寫 `slides/deck.html`，格式見第7節。只能用Wiki頁裡的內容；Wiki沒有的事不能寫，需要的話回報「Wiki缺資料」。

### 6.7 C2 簡報檢查

- 程式：`python3 tools/check_slides.py`。
- AI審查：另一個AI只讀簡報和它引用的Wiki頁，逐頁檢查「內容有沒有Wiki依據」「新手看不看得懂」，寫成 `runs/run-xx/review.md`。
- 有錯誤就回N6重寫出錯的頁，最多3次。

### 6.8 N7 建置與發佈

`python3 tools/build.py` 產生 `docs/`，push後GitHub Pages更新。

### 6.9 log.md

每筆一個標題，格式固定，只往後加，不改舊紀錄：

```
## [2026-11-15] ingest | S01 國家級警報來了--地震測報過程
- 討論單：discussions/D01-S01-……
- 新增：……
- 修改：……
- 檢查：第1次 E3 W1 → 第2次 E0 W1（保留的警告：……）
```

類別只能是 plan、ingest、query、slides、lint、graph。「檢查」那行在C1之後補上（同一筆紀錄，可以改）。

## 7. 簡報格式

`slides/deck.html` 只放 `<section>`，版型、換頁和互動元件在 `templates/deck.html`，由 `tools/build.py` 合併。

```html
<section class="slide" data-kind="concept" data-wiki="concepts/震度.md concepts/規模.md">
  <h2>規模和震度不一樣</h2>
  <div class="compare">
    <div class="card"><h3>規模</h3><p>……</p></div>
    <div class="card"><h3>震度</h3><p>……</p></div>
  </div>
  <aside class="notes">講者備註：……</aside>
</section>
```

- `data-kind`：title、objectives、hook、concept、process、practice、misconception、quiz、summary、sources。順序：title、objectives 開頭；quiz（可以多頁）、summary、sources 結尾；中間至少一頁 practice（放互動試算）。
- `data-wiki`：這頁用到的Wiki頁（相對 `wiki/` 的路徑，空白分隔）。title、sources 以外每頁都要有。頁尾的「出處」由build自動產生。
- 可用標籤：section、h1、h2、h3、p、ul、ol、li、strong、em、small、span、div、table、thead、tbody、tr、th、td、aside、figure、figcaption、button、a（只能連到Wiki頁）。不能用script、style、img、iframe、行內style屬性。
- 可用的class：slide、lead、compare、card、steps、timeline、callout、warn、cols、big、muted、notes、scale、quiz、calc-eew、src。
- 互動元件：
  - 預警時間試算：`<div class="calc-eew" data-vs="S波速度(公里/秒)" data-alert="發布警報的秒數" data-wiki="……"></div>`，數值要出現在data-wiki的頁面裡。
  - 測驗：`<div class="quiz" data-answer="b"><p>題目</p><button data-opt="a">…</button>…<p class="why" data-wiki="……">解析</p></div>`，每題4個選項。
- 每頁正文（不含notes）160字以內；全部10到22頁。
- 數字、引文的規則和Wiki一樣：要能在 `data-wiki` 的頁面裡找到。

## 8. 檢查代碼

### 8.1 Wiki（tools/lint_wiki.py）

| 代碼 | 等級 | 檢查 |
|---|---|---|
| W01 | E | 前置資料缺欄位、type不合法 |
| W02 | E | 連結指到不存在的檔案 |
| W03 | W | 孤兒頁（沒有其他頁連到） |
| W04 | E | index.md 沒列到的頁面，或列了不存在的頁面 |
| W05 | E | 段落或清單項目沒有出處標記 |
| W06 | E | 引文和raw原文不一致；沒有出處的「」超過12字 |
| W07 | E | 有出處的句子裡，數字在該來源原文找不到 |
| W08 | E | log.md 標題格式不對或日期倒退 |
| W09 | E | 已取得的來源沒有來源摘要頁，或摘要頁的id不對 |
| W10 | E | raw/ 檔案的SHA-256和 _sources.json 不同 |
| W11 | E | 來源摘要頁沒有對應的討論單，或討論單沒有學生回覆 |
| W12 | E | 出處標記指到不存在或還沒取得的來源 |

### 8.2 簡報（tools/check_slides.py）

| 代碼 | 等級 | 檢查 |
|---|---|---|
| P01 | E | 頁面種類或順序不合第7節 |
| P02 | E | 缺data-wiki，或指到不存在的Wiki頁 |
| P03 | E | 數字在data-wiki的頁面裡找不到 |
| P04 | E | 引文（12字以上的「」）在data-wiki的頁面裡找不到 |
| P05 | E | 互動元件的數值在它的data-wiki頁面裡找不到 |
| P06 | E | 用了不允許的標籤、class、屬性或外部連結 |
| P07 | W | 單頁正文超過160字；總頁數不在10到22頁 |
| P08 | E | 測驗不是4個選項、缺答案或解析 |

## 9. 不要做的事

- 不改 `raw/` 的檔案；來源有錯就在Wiki寫明，不改原文。
- 不刪 `wiki/log.md` 的舊紀錄；寫錯就在新紀錄更正。
- 不把自己的推論寫成來源的說法；推論要寫「（推論）」並說明根據。
- 簡報不寫Wiki沒有的內容，不從網路或自己的知識補。
- 不改 `templates/`、`tools/`；需要改時先回報。

## 10. 版本紀錄

- v1（2026-11-15）：第一版流程。檢查放在生成之後：C1在每篇來源生成後，C2在整份簡報產生後。
