# 地震預警與國家級警報LLM Wiki

把中央氣象署和美國USGS公開的地震預警資料整理成一份LLM Wiki，再只用Wiki的內容做一份給新手的教學簡報。讀者設定是沒有地震學背景、收過國家級警報的高中生和大學生。

<!--STATS-->

## 網站

| 頁面 | 內容 |
|---|---|
| [教學簡報](https://weichen1209.github.io/quake-alert-wiki/slides/index.html) | 每頁下方列出用到的Wiki頁；最後一頁列出這些頁引用的來源 |
| [Wiki目錄](https://weichen1209.github.io/quake-alert-wiki/wiki/index.html) | 每頁一行摘要；[總覽](https://weichen1209.github.io/quake-alert-wiki/wiki/overview.html)用幾段話串起整個主題 |
| [簡報對應表](https://weichen1209.github.io/quake-alert-wiki/map.html) | 每頁簡報用到哪些Wiki頁、這些頁引用哪些來源 |
| [頁面關係圖](https://weichen1209.github.io/quake-alert-wiki/graph.html) | Wiki頁面之間的連結 |
| [流程圖](https://weichen1209.github.io/quake-alert-wiki/flow.html) | loop／graph設計、從v1改成v2的原因、兩次執行的比較 |
| [執行紀錄](https://weichen1209.github.io/quake-alert-wiki/runs/index.html) | 照流程圖執行的每一步和檢查輸出（run-01用v1，run-02用v2） |
| [規則AGENTS.md](https://weichen1209.github.io/quake-alert-wiki/AGENTS.html) | AI維護Wiki、做簡報要照的規則和檢查代碼 |

## 做法

- 三層：`raw/`放原始來源（取得後不改，記SHA-256），`wiki/`由AI照規則維護，`AGENTS.md`是規則。
- 先討論、後生成：每篇來源先由AI寫討論單（重點、和現有Wiki的關係、想問的問題），學生回覆之後AI才生成或修改頁面。討論單在`wiki/discussions/`。
- 每個AI步驟後面都有檢查，不通過就回去重做，最多3次。檢查程式在`tools/`。
- 簡報只用Wiki的內容，每頁標出用到的Wiki頁；檢查程式比對數字和引文，另一個AI審查意思對不對、新手看不看得懂。
- 這次執行時，學生角色的工作（討論單的學生回覆、版型和規則的修改）由能執行程式的AI代做。

## 來源

| 編號 | 來源 | 發布者 | 日期 |
|---|---|---|---|
| S01 | [國家級警報來了--地震測報過程](https://edu.cwa.gov.tw/PopularScience/ec/ec_3.html) | 交通部中央氣象署 數位科普網 | 未標示 |
| S02 | [地震百問（選錄）：震源與震央、地震波、規模、震度](https://scweb.cwa.gov.tw/zh-TW/Guidance/FAQdetail/13) | 交通部中央氣象署 地震測報中心 | 未標示 |
| S03 | [地震百問（選錄）：地震預報、地震速報與強震即時警報](https://scweb.cwa.gov.tw/zh-TW/Guidance/FAQdetail/96) | 交通部中央氣象署 地震測報中心 | 未標示 |
| S04 | [地震速報－軟體專區（強震即時警報之原理等）](https://scweb.cwa.gov.tw/zh-tw/guidance/eew) | 交通部中央氣象署 地震測報中心 | 未標示 |
| S05 | [新聞稿：交通部中央氣象署地震災防告警細胞廣播訊息（PWS）新增發布條件](https://orgws.kcg.gov.tw/001/KcgOrgUploadFiles/212/relfile/76456/429674/8c71d86a-21a9-4594-9efe-d6a3d0eb00bd.pdf) | 交通部中央氣象署（高雄市政府網站轉載） | 113年8月30日 |
| S06 | [Earthquake Early Warning – Overview](https://www.usgs.gov/programs/earthquake-hazards/science/earthquake-early-warning-overview) | U.S. Geological Survey | 未標示 |
| S07 | [有關「災防告警服務」（PWS）與氣象署地震相關資訊之說明](https://scweb.cwa.gov.tw/zh-tw/pws/info_d/2) | 交通部中央氣象署 地震測報中心 | 頁面標示110年9月2日 |
| S08 | [有關近期PWS推播「地震速報」發布條件及範圍調整之媒體報導，中央氣象局回應](https://www.cwa.gov.tw/Data/service/hottopic/20201008_SC_PWSv2.pdf) | 交通部中央氣象局 | 原文未寫日期 |
| S09 | [地震來時保命三步驟](https://edu.cwa.gov.tw/PopularScience/ec/ec_4.html) | 交通部中央氣象署 數位科普網 | 未標示 |

中央氣象署的網頁依「政府網站資料開放宣告」使用並註明出處；S01、S09所在的數位科普網頁尾寫「非經授權禁止轉載」，同一頁尾的「網站資訊使用聲明」連到這份宣告，本repo依這份宣告使用。S05是新聞稿，S06是美國聯邦政府著作（公有領域）。

## 重建網站

```
python3 tools/build.py
```
