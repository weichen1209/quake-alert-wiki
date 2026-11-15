# Wiki紀錄

## [2026-11-15] plan | D00 整體規劃
- 討論單：discussions/D00-規劃.md
- 簡報比例原理約6、制度約4，最重視「為什麼有時候先搖才響」。
- 第一批取得5篇：cwa-edu-pws-story、cwa-faq-basics、cwa-faq-eew、cwa-eew-principle、cwa-press-2024-pws；第二批取得 cwa-pws-info、cwa-pws-2020-response，做發布門檻時間線。
- 簡報要有預警時間試算和測驗；先不放美國對照，收到警報怎麼做之後再補。

## [2026-11-15] ingest | S01 國家級警報來了--地震測報過程
- 討論單：discussions/D01-S01-國家級警報故事.md
- 新增：sources/S01-cwa-edu-pws-story.md、topics/國家級警報.md
- 修改：index.md（加來源、主題兩節和D01）；overview.md 內容不足，先不建
- 檢查：第1次 E8 W1 → 第2次 E1 W1 → 第3次 E0 W1（保留的警告：W03，D00是規劃討論單，沒有頁面需要連到它）

## [2026-11-15] ingest | S02 地震百問（選錄）：震源與震央、地震波、規模、震度
- 討論單：discussions/D02-S02-地震基本概念.md
- 新增：sources/S02-cwa-faq-basics.md、concepts/規模.md、concepts/震度.md、concepts/震源與震央.md、concepts/P波與S波.md
- 修改：topics/國家級警報.md（加震度5級的分級說明和概念頁連結）；index.md（加概念一節、S02和D02）；overview.md 內容仍不足，先不建
- 檢查：第1次 E15 W1 → 第2次 E0 W1（保留的警告：W03，同S01）

## [2026-11-15] ingest | S03 地震百問（選錄）：地震預報、地震速報與強震即時警報
- 討論單：discussions/D03-S03-速報與強震即時警報.md
- 新增：sources/S03-cwa-faq-eew.md、concepts/強震即時警報.md、topics/警報名稱比較.md
- 修改：topics/國家級警報.md（加不同來源的說法：S01和S03的發布條件，都日期未標示）；concepts/P波與S波.md（加連結）；index.md（加討論單、概念、來源、主題）；overview.md 內容仍不足，先不建；預警時間與盲區等S04再建
- 檢查：第1次 E14 W1 → 第2次 E0 W1（保留的警告：W03，同S01）

## [2026-11-15] ingest | S04 地震速報－軟體專區（強震即時警報之原理等）
- 討論單：discussions/D04-S04-強震即時警報原理.md
- 新增：sources/S04-cwa-eew-principle.md、topics/預警時間與盲區.md
- 修改：concepts/強震即時警報.md（加S04的定義、和預測的差別、三種極限）；topics/警報名稱比較.md（加預測對照和「速報」用法）；index.md（加討論單、來源、主題）；topics/國家級警報.md 學生決定先不改；overview.md 仍不足，先不建；試算用的S波速度和發布秒數仍缺，等做簡報時補來源
- 檢查：第1次 E6 W1 → 第2次 E0 W1（保留的警告：W03，同S01）

## [2026-11-15] ingest | S05 新聞稿：交通部中央氣象署地震災防告警細胞廣播訊息（PWS）新增發布條件
- 討論單：discussions/D05-S05-PWS新增發布條件.md
- 新增：sources/S05-cwa-press-2024-pws.md、topics/收到警報怎麼做.md、overview.md
- 修改：topics/國家級警報.md（加S05的發布條件、三來源並列的表和S03與S05的規模6.5衝突、時間線加113年9月1日）；topics/警報名稱比較.md（加「地震速報」在S01、S03、S05的用法）；index.md（加總覽、討論單、來源、主題）；concepts/強震即時警報.md 不改；concepts/災防告警細胞廣播.md 不建
- 檢查：第1次 E21 W1 → 第2次 E0 W1（保留的警告：W03，同S01）

## [2026-11-15] query | Q01 新手學習順序、Q02 簡報大綱
- 新增：queries/Q01-新手學習順序.md、queries/Q02-簡報大綱.md
- 修改：index.md（加查詢）
- 缺資料：S波速度（試算 data-vs）、單一的發布警報秒數（data-alert，暫定20待確認）、113年9月1日之前的發布條件年份、完整防護動作；回N1補來源

## [2026-11-15] slides | 簡報第1版
- 新增：slides/deck.html，20頁（依queries/Q02-簡報大綱.md）
- 用到的Wiki頁：overview.md、concepts/規模.md、震度.md、震源與震央.md、P波與S波.md、強震即時警報.md、topics/預警時間與盲區.md、警報名稱比較.md、國家級警報.md、收到警報怎麼做.md
- 學生的決定：試算的發布警報秒數用20（對應PWS約20多秒內，簡化成20秒），頁面上說明這是簡化
- 缺資料：S波速度（第10頁 data-vs 要用，Wiki沒有數字，第10頁暫不放calc-eew元件，補來源後再放，位置已留註解）；113年9月1日之前的發布條件年份（第14頁）；完整防護動作（第15頁）；缺資料回N1補來源
- 檢查：C2a第1次 E0（程式看不出第10頁沒有試算）；C2b第1次 E6 W11（另一個AI審查，見runs/run-01/checks/47-C2b-deck.txt）；Wiki缺S波速度 → 回N1取得S06

## [2026-11-15] ingest | S06 Earthquake Early Warning – Overview
- 討論單：discussions/D06-S06-美國地震預警.md
- 新增：sources/S06-usgs-eew-overview.md
- 修改：concepts/P波與S波.md（加S06速度和換算、不同來源的說法）；topics/預警時間與盲區.md（加速度來源和試算說明）；concepts/強震即時警報.md（加預警不是預測）；overview.md；index.md；不建美國ShakeAlert頁，門檻和感測器數量不收
- 檢查：第1次 E54 → 第2次 E18 → 第3次 E16（S06的部分已通過；剩下16個都在queries/Q02-簡報大綱.md，是N5的大綱第一次被檢查到，交給重做大綱時修）
