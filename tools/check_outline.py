"""C0 大綱檢查（graph v2 新增）：N5整理完大綱、N6產生簡報之前執行。

  python3 tools/check_outline.py                     只檢查
  python3 tools/check_outline.py --run run-02 --target Q02   檢查並記錄到執行紀錄

檢查（AGENTS.md 第8.4節）：
  查詢頁（wiki/queries/）用 lint_wiki.py 的單頁檢查（引文、數字、出處、連結），錯了回N5（Q01的錯記在N4，由N5一起改）
  O02 大綱要有「## 試算數字」：data-vs、data-alert 各一行，數字要在寫的那一頁找得到，錯了回N5
  O03 大綱要有「## Wiki缺資料」：寫「無」，或每一項都標「（學生決定不補）」；還有缺的就回N1補來源
有錯誤（E）時結束碼為1。
"""
import argparse
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lint_wiki as L  # noqa: E402
import runlog  # noqa: E402
import wikilib as W  # noqa: E402

CALC = re.compile(r"data-(vs|alert)\s*[：:]\s*([\d.]+)\s*[｜|]\s*(\S+?\.md)")


def section(body, title):
    m = re.search(rf"^## {re.escape(title)}\s*$(.*?)(?=^## |\Z)", body, re.M | re.S)
    return m.group(1).strip() if m else None


def check():
    queries = [p for p in W.wiki_pages() if p.startswith("queries/")]
    issues = [(lv, code, f, ln, msg) for lv, code, f, ln, msg in L.lint(queries)]
    outline = [p for p in queries if "大綱" in p]
    if not outline:
        return issues + [("E", "O02", "wiki/queries/", 0, "沒有簡報大綱 Qxx-簡報大綱.md")]
    rel = outline[-1]
    f = f"wiki/{rel}"
    _, body, start = W.split_front((W.WIKI / rel).read_text(encoding="utf-8"))
    line_of = lambda s: start + body[:body.find(s)].count("\n") if s in body else 1  # noqa: E731

    # O02 試算數字
    calc = section(body, "試算數字")
    if calc is None:
        issues.append(("E", "O02", f, 1, "大綱沒有「## 試算數字」一節"))
    else:
        found = {m.group(1): m for m in CALC.finditer(calc)}
        for key in ("vs", "alert"):
            m = found.get(key)
            if not m:
                issues.append(("E", "O02", f, line_of("## 試算數字"), f"「試算數字」沒有 data-{key}：數字｜Wiki頁"))
                continue
            num, page = m.group(2), m.group(3)
            p = W.WIKI / page
            if not p.exists():
                issues.append(("E", "O02", f, line_of(m.group(0)), f"data-{key} 寫的頁面不存在：{page}"))
                continue
            _, pbody, _ = W.split_front(p.read_text(encoding="utf-8"))
            if not W.has_number(num, W.CITE.sub("", pbody)):
                issues.append(("E", "O02", f, line_of(m.group(0)), f"data-{key}={num} 在 {page} 找不到"))

    # O03 缺資料
    gap = section(body, "Wiki缺資料")
    if gap is None:
        issues.append(("E", "O03", f, 1, "大綱沒有「## Wiki缺資料」一節（沒有缺就寫「無」）"))
    elif re.sub(r"^[-*]\s*", "", gap).strip() not in ("無", "無。"):
        for item in re.findall(r"^\s*[-*]\s+(.+)$", gap, re.M) or [gap]:
            if "（學生決定不補）" not in item:
                issues.append(("E", "O03", f, line_of(item[:20]), f"Wiki缺資料：{item[:40]}"))
    return issues


def owner(code, f, ln, msg):
    if code == "O03":
        return "N1"
    if code == "O02":
        return "N5"
    return L.owner_of(f, ln, code, msg)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run")
    ap.add_argument("--target", default="Q02")
    args = ap.parse_args()
    issues = sorted(check(), key=lambda x: (x[2], x[3], x[1]))
    errs = Counter(c for lv, c, *_ in issues if lv == "E")
    owners, lines = {}, []
    for lv, code, f, ln, msg in issues:
        who = owner(code, f, ln, msg)
        if lv == "E":
            owners.setdefault(who, Counter())[code] += 1
        lines.append(f"{lv} {code} {f}:{ln} [{who}] {msg}")
    lines.append(f"錯誤 {sum(errs.values())} 個" + (f"（{'、'.join(f'{k}×{v}' for k, v in sorted(errs.items()))}）" if errs else ""))
    out = "\n".join(lines)
    print(out)
    if args.run:
        seq = len(runlog.events(args.run)) + 1
        d = W.ROOT / "runs" / args.run / "checks"
        d.mkdir(parents=True, exist_ok=True)
        name = f"{seq:02d}-C0-{args.target}.txt"
        (d / name).write_text(out + "\n", encoding="utf-8")
        runlog.add(args.run, "C0", args.target, "fail" if errs else "pass", "", dict(errs), name,
                   {k: dict(v) for k, v in owners.items()})
    sys.exit(1 if errs else 0)


if __name__ == "__main__":
    main()
