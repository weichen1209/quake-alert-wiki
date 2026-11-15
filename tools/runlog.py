"""執行紀錄：每個節點跑完記一筆到 runs/<run>/trace.jsonl，report 產生 runs/<run>/README.md。

  python3 tools/runlog.py add <run> <節點> <對象> <結果> [說明] [--codes R1=2,R3=1] [--file 檔名]
  python3 tools/runlog.py report <run>
結果用 pass、fail、done、reply、gap、note、fix 其中一種：note是補充說明（學生讀頁面發現的問題、版型修正、改決定），
fix是學生手動修改；統計只算pass和fail。檢查程式加 --run 時會自動記錄。
"""
import datetime
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NODES = {
    "N0": "規劃討論", "N1": "取得資料", "N2": "討論", "R": "學生回覆", "N3": "生成頁面",
    "C1": "Wiki檢查", "N4": "查詢Wiki", "N5": "整理大綱", "C0": "大綱檢查", "N6": "產生簡報",
    "C2a": "簡報檢查（程式）", "C2b": "簡報審查（AI）", "N7": "建置發佈", "L": "Wiki全體檢查",
    "T": "版型修正（學生）", "C1a": "討論單檢查", "F": "規則和程式修正（學生）",
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


ELINE = re.compile(r"^E (\w+) (\S+?)(?::\d+)? (?:\[(\w+)\] )?(.*)$")


def check_errors(run, e, default_owner):
    """一次檢查抓到的錯：[(產生它的節點, 代碼, 比對用的key)]。有輸出檔就逐行讀，沒有就用codes。"""
    f = ROOT / "runs" / run / "checks" / e.get("check_file", "")
    if e.get("check_file") and f.exists():
        out = []
        for line in f.read_text(encoding="utf-8").splitlines():
            m = ELINE.match(line)
            if m:
                code, where, who, msg = m.groups()
                out.append((who or default_owner, code, (code, where, msg.strip())))
        return out
    return [(default_owner, k, (k, e["target"], e["seq"], i))
            for k, v in e["codes"].items() for i in range(v)]


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
    # 學生回覆時（R）發現的錯算在寫討論單的N2
    owner = {"C1": "N3", "C1a": "N2", "C0": "N5", "C2a": "N6", "C2b": "N6", "R": "N2"}
    per_node = defaultdict(Counter)   # 不重複的錯：{節點: {代碼: 個數}}
    fails = Counter()
    checks = defaultdict(lambda: {"runs": 0, "fails": 0, "new": 0})
    prev_keys = {}                    # 每種檢查上一次的錯誤集合
    for e in ev:
        node = e["node"]
        if node not in owner or e["status"] not in ("pass", "fail"):
            continue
        errs = check_errors(run, e, owner[node])
        keys = {k for _, _, k in errs}
        new = [(src, code) for src, code, k in errs if k not in prev_keys.get(node, set())]
        prev_keys[node] = keys
        checks[node]["runs"] += 1
        if e["status"] == "fail":
            checks[node]["fails"] += 1
            for src in {s for s, _, _ in errs}:
                fails[src] += 1
        checks[node]["new"] += len(new)
        for src, code in new:
            per_node[src][code] += 1
    lines += ["", "## 各檢查節點", "",
              "「抓到的錯」同一個錯只算第一次：和上一次同類檢查比，代碼、檔案、訊息都一樣的錯不再算。", "",
              "| 檢查 | 執行次數 | 不通過 | 抓到的錯 |", "|---|---|---|---|"]
    for node in ["R", "C1a", "C1", "C0", "C2a", "C2b"]:
        c = checks.get(node)
        if c:
            lines.append(f"| {node} {NODES.get(node, '')} | {c['runs']} | {c['fails']} | {c['new']} |")
    lines += ["", "## 各生成節點被檢查抓到的錯", "",
              "錯誤依所在的檔案和小節算到產生它的節點：討論單裡AI寫的部分算N2（D00算N0），「學生回覆」算R，「決定」和其他Wiki頁算N3，queries/的查詢頁算N4、大綱算N5，大綱列出的Wiki缺資料（O03）算N1（要回N1補來源），簡報算N6。學生回覆時發現的錯算N2。", "",
              "| 節點 | 有錯的檢查次數 | 抓到的錯 | 代碼 |", "|---|---|---|---|"]
    for node in [n for n in ["N0", "N1", "N2", "R", "N3", "N4", "N5", "N6"] if n in ("N2", "N3", "N5", "N6") or fails.get(n)]:
        c = per_node.get(node, Counter())
        codes = "、".join(f"{k}×{v}" for k, v in sorted(c.items())) or "－"
        lines.append(f"| {node} {NODES[node]} | {fails.get(node, 0)} | {sum(c.values())} | {codes} |")
    out = ROOT / "runs" / run / "README.md"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"寫入 {out.relative_to(ROOT)}（{len(ev)} 筆）")


def main():
    if len(sys.argv) >= 3 and sys.argv[1] == "report":
        report(sys.argv[2])
    elif len(sys.argv) >= 6 and sys.argv[1] == "add":
        # 選用：--codes R1=2,R3=1（錯誤代碼）、--file 檔名（checks/ 裡的輸出）
        rest, codes, cfile = sys.argv[6:], {}, None
        for flag in ("--codes", "--file"):
            if flag in rest:
                i = rest.index(flag)
                val = rest[i + 1]
                rest = rest[:i] + rest[i + 2:]
                if flag == "--codes":
                    codes = {k: int(v) for k, v in (p.split("=") for p in val.split(",") if p)}
                else:
                    cfile = val
        rec = add(sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5], " ".join(rest), codes, cfile)
        print(f"#{rec['seq']} {rec['node']} {rec['target']} 第{rec['attempt']}次 {rec['status']}")
    else:
        print(__doc__)


if __name__ == "__main__":
    main()
