"""C1 Wiki檢查：照 AGENTS.md 第8.1節檢查 wiki/，輸出等級、代碼、檔案和行號。

  python3 tools/lint_wiki.py                      只檢查
  python3 tools/lint_wiki.py --run run-01 --target S01   檢查並記錄到執行紀錄
有錯誤（E）時結束碼為1。
"""
import argparse
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import runlog  # noqa: E402
import wikilib as W  # noqa: E402

REQUIRED = ["title", "type", "summary", "sources", "updated"]
QUOTE = re.compile(r"「([^「」]*)」")
SEP_ROW = re.compile(r"^\s*\|?\s*:?-{3,}")
LOG_HEAD = re.compile(r"^## \[(\d{4}-\d{2}-\d{2})\] (plan|ingest|query|slides|lint|graph) \| \S.*$")


def units(body, start):
    """把正文切成段落、清單項目、表格列：(種類, 文字, 行號, 小節標題)。"""
    lines = body.split("\n")
    out, para, para_line, section = [], [], None, ""

    def flush():
        nonlocal para, para_line
        if para:
            out.append(("para", " ".join(para), para_line, section))
        para, para_line = [], None

    for i, line in enumerate(lines):
        ln = start + i
        s = line.rstrip()
        if not s.strip():
            flush()
            continue
        if s.startswith("#"):
            flush()
            section = s.lstrip("#").strip()
            out.append(("heading", s, ln, section))
            continue
        if s.lstrip().startswith("|"):
            flush()
            if SEP_ROW.match(s):
                continue
            nxt = lines[i + 1] if i + 1 < len(lines) else ""
            out.append(("thead" if SEP_ROW.match(nxt) else "row", s, ln, section))
            continue
        if re.match(r"^\s*([-*]|\d+\.)\s+", s):
            flush()
            out.append(("item", s, ln, section))
            continue
        if s.startswith(">"):
            flush()
            out.append(("quote", s, ln, section))
            continue
        if out and out[-1][0] == "item" and line.startswith("  ") and not para:
            k, t, l0, sec = out[-1]
            out[-1] = (k, t + " " + s.strip(), l0, sec)
            continue
        if not para:
            para_line = ln
        para.append(s.strip())
    flush()
    return out


def link_only(text):
    t = re.sub(r"^\s*([-*]|\d+\.)\s+", "", text)
    t = W.LINK.sub("", t)
    return re.sub(r"[\s、，,；;。．.:：/／|]", "", t) == ""


def strip_marker(text):
    return re.sub(r"^\s*([-*]|\d+\.)\s+", "", text)


def section_text(body, title):
    m = re.search(rf"^## {re.escape(title)}\s*$(.*?)(?=^## |\Z)", body, re.M | re.S)
    return m.group(1).strip() if m else None


def owner_of(f, ln, code, msg):
    """這個錯是哪個節點產生的：討論單依小節分（AI的部分算N2，D00算N0；學生回覆算R；決定算N3），其他檔案算N3。"""
    if not f.startswith("wiki/discussions/"):
        return "N3"
    if code == "W11":
        return "R" if "學生回覆" in msg else "N3"
    first = "N0" if f.rsplit("/", 1)[-1].startswith("D00") else "N2"
    sec, path = "", W.ROOT / f
    if path.exists() and ln:
        for line in path.read_text(encoding="utf-8").split("\n")[:ln]:
            if line.startswith("## "):
                sec = line[3:].strip()
    if sec == "學生回覆":
        return "R"
    if sec == "決定" and first == "N2":
        return "N3"
    return first


def lint():
    issues = []  # (等級, 代碼, 檔案, 行號, 訊息)
    def add(level, code, f, ln, msg):
        issues.append((level, code, f, ln, msg))

    got = W.fetched()

    # W10 raw 沒被改過
    for sid, e in got.items():
        p = W.RAW / e["file"]
        if not p.exists():
            add("E", "W10", f"raw/{e['file']}", 0, "檔案不見了")
        elif W.sha256(p) != e["sha256"]:
            add("E", "W10", f"raw/{e['file']}", 0, "SHA-256和 _sources.json 不同，raw 檔案被改過")

    pages = W.wiki_pages()
    metas, inbound = {}, {p: set() for p in pages}

    for rel in pages:
        path = W.WIKI / rel
        text = path.read_text(encoding="utf-8")
        meta, body, start = W.split_front(text)
        metas[rel] = meta
        f = f"wiki/{rel}"

        # W01 前置資料
        # 規劃用的討論單還沒有來源，sources 可以是空的 []
        missing = [k for k in REQUIRED if not meta.get(k)
                   and not (k == "sources" and k in meta and meta.get("type") == "discussion")]
        if missing:
            add("E", "W01", f, 1, f"前置資料缺：{'、'.join(missing)}")
        if meta.get("type") and meta["type"] not in W.TYPES:
            add("E", "W01", f, 1, f"type「{meta['type']}」不合法")
        if meta.get("updated") and not re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(meta["updated"])):
            add("E", "W01", f, 1, "updated 要寫成 YYYY-MM-DD")
        ptype = meta.get("type", "")

        # W02 連結
        for ln_off, line in enumerate(body.split("\n")):
            for m in W.LINK.finditer(line):
                href = m.group(2)
                if re.match(r"^[a-z]+://", href):
                    continue
                target = (path.parent / href.split("#", 1)[0]).resolve()
                if not target.exists():
                    add("E", "W02", f, start + ln_off, f"連結找不到檔案：{href}")
                    continue
                try:
                    trel = target.relative_to(W.WIKI.resolve()).as_posix()
                except ValueError:
                    continue
                if trel in inbound and trel != rel:
                    inbound[trel].add(rel)

        for kind, t, ln, section in units(body, start):
            if kind == "heading":
                continue
            # W12 出處指到的來源
            for sid in W.CITE.findall(t):
                if sid not in got:
                    add("E", "W12", f, ln, f"出處 {sid} 不存在或還沒取得")
            # W05 每段要有出處
            if ptype != "discussion" and kind in ("para", "item", "row", "quote"):
                if "相關頁面" not in section and not link_only(t) and not W.CITE.search(t):
                    add("E", "W05", f, ln, f"沒有出處標記：{strip_marker(t)[:40]}")
            # W06 引文
            for m in QUOTE.finditer(t):
                q = m.group(1)
                cites = re.match(r"((?:〔S\d{2}〕)+)", t[m.end():])
                ids = re.findall(r"S\d{2}", cites.group(1)) if cites else []
                if ids:
                    bodies = [W.raw_body(s) for s in ids if s in got]
                    if bodies and not any(W.norm(q) in W.norm(b) for b in bodies):
                        add("E", "W06", f, ln, f"引文和{'、'.join(ids)}原文不一致：「{q[:30]}」")
                elif len(q) > 12:
                    add("E", "W06", f, ln, f"沒有出處的「」超過12字：「{q[:30]}」")
            # W07 數字
            if kind in ("para", "item", "row", "quote"):
                unit_ids = W.CITE.findall(t)
                for sent in re.split(r"(?<=[。！？])", strip_marker(t)):
                    ids = W.CITE.findall(sent) or unit_ids
                    ids = [s for s in ids if s in got]
                    if not ids:
                        continue
                    for num in W.numbers_in(sent):
                        if not any(W.has_number(num, W.raw_body(s)) for s in ids):
                            add("E", "W07", f, ln, f"數字 {num} 在{'、'.join(ids)}原文找不到：{sent.strip()[:40]}")

    # W03 孤兒頁
    for rel, src in inbound.items():
        if not src:
            add("W", "W03", f"wiki/{rel}", 1, "沒有其他頁面連到這頁")

    # W04 index.md
    idx = W.WIKI / "index.md"
    if not idx.exists():
        add("E", "W04", "wiki/index.md", 0, "沒有 index.md")
    else:
        listed = set()
        for m in W.LINK.finditer(idx.read_text(encoding="utf-8")):
            r = W.resolve("index.md", m.group(2))
            if r:
                listed.add(r)
        for rel in pages:
            if rel not in listed:
                add("E", "W04", "wiki/index.md", 0, f"沒有列到 {rel}")
        for rel in sorted(listed - set(pages)):
            add("E", "W04", "wiki/index.md", 0, f"列了不存在的頁面 {rel}")

    # W08 log.md
    log = W.WIKI / "log.md"
    if not log.exists():
        add("E", "W08", "wiki/log.md", 0, "沒有 log.md")
    else:
        prev = ""
        for i, line in enumerate(log.read_text(encoding="utf-8").split("\n"), 1):
            if line.startswith("## "):
                m = LOG_HEAD.match(line)
                if not m:
                    add("E", "W08", "wiki/log.md", i, f"標題格式不對：{line[:50]}")
                    continue
                if m.group(1) < prev:
                    add("E", "W08", "wiki/log.md", i, "日期比上一筆早")
                prev = m.group(1)

    # W09 每篇來源都有摘要頁；W11 摘要頁有討論單且學生回覆過
    for sid in sorted(got):
        cands = [r for r in pages if r.startswith(f"sources/{sid}-")]
        if not cands:
            add("E", "W09", "wiki/sources/", 0, f"{sid} 沒有來源摘要頁")
            continue
        meta = metas[cands[0]]
        if meta.get("type") != "source" or sid not in (meta.get("sources") or []):
            add("E", "W09", f"wiki/{cands[0]}", 1, f"type 要是 source，sources 要有 {sid}")
        ds = [r for r in pages if re.match(rf"discussions/D\d{{2}}-{sid}-", r)]
        if not ds:
            add("E", "W11", f"wiki/{cands[0]}", 1, f"{sid} 沒有討論單 discussions/Dxx-{sid}-*.md")
            continue
        _, dbody, _ = W.split_front((W.WIKI / ds[0]).read_text(encoding="utf-8"))
        reply = section_text(dbody, "學生回覆")
        decision = section_text(dbody, "決定")
        if not reply or reply.startswith("（學生寫"):
            add("E", "W11", f"wiki/{ds[0]}", 1, "討論單沒有學生回覆")
        if not decision or decision.startswith("（AI依回覆"):
            add("E", "W11", f"wiki/{ds[0]}", 1, "討論單沒有寫「決定」")
    return issues


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run")
    ap.add_argument("--target", default="wiki")
    args = ap.parse_args()
    issues = sorted(lint(), key=lambda x: (x[2], x[3], x[1]))
    errs = Counter(c for lv, c, *_ in issues if lv == "E")
    warns = Counter(c for lv, c, *_ in issues if lv == "W")
    owners = {}
    lines = []
    for lv, code, f, ln, msg in issues:
        who = owner_of(f, ln, code, msg)
        if lv == "E":
            owners.setdefault(who, Counter())[code] += 1
        lines.append(f"{lv} {code} {f}:{ln} [{who}] {msg}")
    lines.append(f"錯誤 {sum(errs.values())} 個、警告 {sum(warns.values())} 個"
                 + (f"（{'、'.join(f'{k}×{v}' for k, v in sorted((errs + warns).items()))}）" if issues else ""))
    out = "\n".join(lines)
    print(out)
    if args.run:
        seq = len(runlog.events(args.run)) + 1
        d = W.ROOT / "runs" / args.run / "checks"
        d.mkdir(parents=True, exist_ok=True)
        name = f"{seq:02d}-C1-{args.target}.txt"
        (d / name).write_text(out + "\n", encoding="utf-8")
        note = f"警告{sum(warns.values())}" if warns else ""
        runlog.add(args.run, "C1", args.target, "fail" if errs else "pass", note, dict(errs), name,
                   {k: dict(v) for k, v in owners.items()})
    sys.exit(1 if errs else 0)


if __name__ == "__main__":
    main()
