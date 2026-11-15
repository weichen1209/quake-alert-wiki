"""執行紀錄：每個節點跑完記一筆到 runs/<run>/trace.jsonl，report 產生 runs/<run>/README.md。

  python3 tools/runlog.py add <run> <節點> <對象> <結果> [說明]
  python3 tools/runlog.py report <run>
結果用 pass、fail、done、reply、gap 其中一種。檢查程式加 --run 時會自動記錄。
"""
import datetime
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NODES = {
    "N0": "規劃討論", "N1": "取得資料", "N2": "討論", "R": "學生回覆", "N3": "生成頁面",
    "C1": "Wiki檢查", "N4": "查詢Wiki", "N5": "整理大綱", "C0": "大綱檢查", "N6": "產生簡報",
    "C2a": "簡報檢查（程式）", "C2b": "簡報審查（AI）", "N7": "建置發佈", "L": "Wiki全體檢查",
}


def events(run):
    f = ROOT / "runs" / run / "trace.jsonl"
    if not f.exists():
        return []
    return [json.loads(l) for l in f.read_text(encoding="utf-8").splitlines() if l.strip()]


def add(run, node, target, status, note="", codes=None, check_file=None, owners=None):
    d = ROOT / "runs" / run
    d.mkdir(parents=True, exist_ok=True)
    ev = events(run)
    attempt = 1 + sum(1 for e in ev if e["node"] == node and e["target"] == target)
    rec = {"seq": len(ev) + 1, "time": datetime.datetime.now().isoformat(timespec="seconds"),
           "node": node, "target": target, "attempt": attempt, "status": status,
           "codes": codes or {}, "note": note}
    if check_file:
        rec["check_file"] = check_file
    if owners:
        rec["owners"] = owners  # 錯誤是哪個節點產生的：{節點: {代碼: 個數}}
    with (d / "trace.jsonl").open("a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    return rec


def report(run):
    ev = events(run)
    lines = [f"# 執行紀錄 {run}", "",
             "由 `tools/runlog.py report` 依 `trace.jsonl` 產生。檢查節點的完整輸出在 `checks/`。", "",
             "## 逐步紀錄", "",
             "| # | 時間 | 節點 | 對象 | 第幾次 | 結果 | 錯誤代碼 | 說明 |", "|---|---|---|---|---|---|---|---|"]
    for e in ev:
        codes = "、".join(f"{k}×{v}" for k, v in sorted(e["codes"].items())) or "－"
        name = f"{e['node']} {NODES.get(e['node'], '')}".strip()
        note = e["note"].replace("|", "／")
        if e.get("check_file"):
            note = (note + " " if note else "") + f"[輸出](checks/{e['check_file']})"
        lines.append(f"| {e['seq']} | {e['time'][11:16]} | {name} | {e['target']} | {e['attempt']} | {e['status']} | {codes} | {note} |")
    # 依「產生錯誤的節點」統計：檢查程式有標就照標的（例如討論單裡AI寫的部分算N2），
    # 沒標就算在檢查節點前面那個生成節點
    owner = {"C1": "N3", "C0": "N5", "C2a": "N6", "C2b": "N6"}
    per_node = defaultdict(Counter)
    fails = Counter()
    for e in ev:
        if e["node"] in owner and e["status"] == "fail":
            for src, codes in (e.get("owners") or {owner[e["node"]]: e["codes"]}).items():
                fails[src] += 1
                for k, v in codes.items():
                    per_node[src][k] += v
    lines += ["", "## 各生成節點被檢查抓到錯的次數", "",
              "檢查沒通過時，錯誤依所在的檔案和小節算到產生它的節點：討論單裡AI寫的部分算N2（D00算N0），「學生回覆」算R，「決定」和其他Wiki頁算N3。", "",
              "| 節點 | 有錯的檢查次數 | 錯誤代碼合計 |", "|---|---|---|"]
    for node in [n for n in ["N0", "N2", "R", "N3", "N5", "N6"] if n in ("N2", "N3", "N5", "N6") or fails.get(n)]:
        c = per_node.get(node, Counter())
        codes = "、".join(f"{k}×{v}" for k, v in sorted(c.items())) or "－"
        lines.append(f"| {node} {NODES[node]} | {fails.get(node, 0)} | {codes} |")
    out = ROOT / "runs" / run / "README.md"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"寫入 {out.relative_to(ROOT)}（{len(ev)} 筆）")


def main():
    if len(sys.argv) >= 3 and sys.argv[1] == "report":
        report(sys.argv[2])
    elif len(sys.argv) >= 6 and sys.argv[1] == "add":
        rec = add(sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5], " ".join(sys.argv[6:]))
        print(f"#{rec['seq']} {rec['node']} {rec['target']} 第{rec['attempt']}次 {rec['status']}")
    else:
        print(__doc__)


if __name__ == "__main__":
    main()
