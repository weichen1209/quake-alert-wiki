"""C2a 簡報檢查：照 AGENTS.md 第8.2節檢查 slides/deck.html。

  python3 tools/check_slides.py                       只檢查
  python3 tools/check_slides.py --run run-01 --target deck   檢查並記錄到執行紀錄
有錯誤（E）時結束碼為1。
"""
import argparse
import re
import sys
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import runlog  # noqa: E402
import wikilib as W  # noqa: E402

DECK = W.ROOT / "slides" / "deck.html"
KINDS = {"title", "objectives", "hook", "concept", "process", "practice", "misconception",
         "quiz", "summary", "sources"}
TAGS = {"section", "h1", "h2", "h3", "p", "ul", "ol", "li", "strong", "em", "small", "span", "div",
        "table", "thead", "tbody", "tr", "th", "td", "aside", "figure", "figcaption", "button", "a", "br"}
CLASSES = {"slide", "lead", "compare", "card", "steps", "timeline", "callout", "warn", "cols", "big",
           "muted", "notes", "scale", "quiz", "calc-eew", "src", "why"}
ATTRS = {"class", "data-kind", "data-wiki", "data-answer", "data-opt", "data-vs", "data-alert",
         "href", "colspan", "rowspan", "id", "title"}
QUOTE = re.compile(r"「([^「」]*)」")


class Node:
    def __init__(self, tag, attrs, line):
        self.tag, self.attrs, self.line = tag, dict(attrs), line
        self.children, self.text = [], []

    def classes(self):
        return set((self.attrs.get("class") or "").split())

    def all_text(self, skip_notes=False):
        out = []
        for c in self.children:
            if isinstance(c, str):
                out.append(c)
            elif not (skip_notes and "notes" in c.classes()):
                out.append(c.all_text(skip_notes))
        return "".join(out)

    def walk(self):
        yield self
        for c in self.children:
            if isinstance(c, Node):
                yield from c.walk()


class Tree(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root = Node("root", [], 0)
        self.stack = [self.root]

    def handle_starttag(self, tag, attrs):
        n = Node(tag, attrs, self.getpos()[0])
        self.stack[-1].children.append(n)
        if tag not in ("br",):
            self.stack.append(n)

    def handle_startendtag(self, tag, attrs):
        self.stack[-1].children.append(Node(tag, attrs, self.getpos()[0]))

    def handle_endtag(self, tag):
        for i in range(len(self.stack) - 1, 0, -1):
            if self.stack[i].tag == tag:
                del self.stack[i:]
                break

    def handle_data(self, data):
        self.stack[-1].children.append(data)


def wiki_text(paths):
    """把 data-wiki 列的頁面讀進來（去掉出處標記），找不到的回傳在 missing。"""
    texts, missing = [], []
    for p in paths:
        f = W.WIKI / p
        if f.exists() and f.suffix == ".md":
            _, body, _ = W.split_front(f.read_text(encoding="utf-8"))
            texts.append(W.CITE.sub("", body))
        else:
            missing.append(p)
    return "\n".join(texts), missing


def check():
    issues = []

    def add(level, code, ln, msg):
        issues.append((level, code, ln, msg))

    if not DECK.exists():
        add("E", "P01", 0, "沒有 slides/deck.html")
        return issues, 0
    t = Tree()
    t.feed(DECK.read_text(encoding="utf-8"))
    slides = [n for n in t.root.children if isinstance(n, Node) and n.tag == "section"]
    stray = [n for n in t.root.children if isinstance(n, Node) and n.tag != "section"]
    for n in stray:
        add("E", "P06", n.line, f"section 外面不能放 <{n.tag}>")

    # P06 標籤、class、屬性、連結
    for s in slides:
        for n in s.walk():
            if n.tag not in TAGS:
                add("E", "P06", n.line, f"不允許的標籤 <{n.tag}>")
            bad = n.classes() - CLASSES
            if bad:
                add("E", "P06", n.line, f"不允許的 class：{' '.join(sorted(bad))}")
            for a in n.attrs:
                if a not in ATTRS:
                    add("E", "P06", n.line, f"不允許的屬性 {a}")
            if n.tag == "a":
                href = n.attrs.get("href", "")
                if not re.fullmatch(r"[^:]+\.md", href) or not (W.WIKI / href).exists():
                    add("E", "P06", n.line, f"連結只能指到存在的Wiki頁（相對 wiki/）：{href}")

    # P01 種類與順序
    kinds = [s.attrs.get("data-kind", "") for s in slides]
    for s, k in zip(slides, kinds):
        if k not in KINDS:
            add("E", "P01", s.line, f"data-kind「{k}」不合法")
    if kinds[:2] != ["title", "objectives"]:
        add("E", "P01", slides[0].line if slides else 0, f"開頭要是 title、objectives，現在是 {kinds[:2]}")
    tail = kinds[::-1]
    if tail[:2] != ["sources", "summary"] or len(tail) < 3 or tail[2] != "quiz":
        add("E", "P01", slides[-1].line if slides else 0, f"結尾要是 quiz…、summary、sources，現在是 {kinds[-3:]}")
    if "practice" not in kinds:
        add("E", "P01", 0, "沒有 practice 頁")
    # 結尾的quiz以前不能再出現quiz、summary、sources
    end_quiz = len(kinds) - 2
    while end_quiz > 0 and kinds[end_quiz - 1] == "quiz":
        end_quiz -= 1
    for i, k in enumerate(kinds[:end_quiz]):
        if k in ("quiz", "summary", "sources"):
            add("E", "P01", slides[i].line, f"{k} 只能放在結尾")

    for s, k in zip(slides, kinds):
        paths = (s.attrs.get("data-wiki") or "").split()
        # P02 出處
        if k not in ("title", "sources") and not paths:
            add("E", "P02", s.line, f"{k} 頁沒有 data-wiki")
        text_all, missing = wiki_text(paths)
        for m in missing:
            add("E", "P02", s.line, f"data-wiki 指到不存在的頁面：{m}")
        # 頁內元件可以有自己的 data-wiki（測驗解析、試算）
        extra = []
        for n in s.walk():
            if n is not s and n.attrs.get("data-wiki"):
                ep = n.attrs["data-wiki"].split()
                et, emiss = wiki_text(ep)
                for m in emiss:
                    add("E", "P02", n.line, f"data-wiki 指到不存在的頁面：{m}")
                extra.append(et)
        source = text_all + "\n" + "\n".join(extra)
        visible = s.all_text()
        if k == "sources":
            continue
        # P03 數字
        for num in sorted(set(W.numbers_in(visible))):
            if not W.has_number(num, source):
                add("E", "P03", s.line, f"數字 {num} 在 data-wiki 的頁面找不到")
        # P04 引文
        for m in QUOTE.finditer(visible):
            q = m.group(1)
            if len(q) > 12 and W.norm(q) not in W.norm(source):
                add("E", "P04", s.line, f"引文在 data-wiki 的頁面找不到：「{q[:30]}」")
        # P05 互動元件數值；P08 測驗
        for n in s.walk():
            if "calc-eew" in n.classes():
                own, _ = wiki_text((n.attrs.get("data-wiki") or "").split())
                for a in ("data-vs", "data-alert"):
                    v = n.attrs.get(a)
                    if not v or not re.fullmatch(r"\d+(\.\d+)?", v):
                        add("E", "P05", n.line, f"{a} 要是數字")
                    elif not W.has_number(v, own + "\n" + text_all):
                        add("E", "P05", n.line, f"{a}={v} 在試算的 data-wiki 頁面找不到")
            if "quiz" in n.classes():
                opts = [b.attrs.get("data-opt") for b in n.walk() if b.tag == "button"]
                ans = n.attrs.get("data-answer")
                whys = [w for w in n.walk() if "why" in w.classes()]
                if sorted(opts) != ["a", "b", "c", "d"]:
                    add("E", "P08", n.line, f"選項要是 a、b、c、d 四個，現在是 {opts}")
                if ans not in ("a", "b", "c", "d"):
                    add("E", "P08", n.line, "data-answer 要是 a～d")
                if not whys or not whys[0].attrs.get("data-wiki"):
                    add("E", "P08", n.line, "缺解析 <p class=\"why\" data-wiki=…>")
        # P07 份量
        body = re.sub(r"\s+", "", s.all_text(skip_notes=True))
        if len(body) > 160 and k not in ("quiz", "sources"):
            add("W", "P07", s.line, f"正文 {len(body)} 字，超過160字")
    if not 10 <= len(slides) <= 22:
        add("W", "P07", 0, f"共 {len(slides)} 頁，不在10到22頁")
    return issues, len(slides)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run")
    ap.add_argument("--target", default="deck")
    args = ap.parse_args()
    issues, n = check()
    issues.sort(key=lambda x: (x[2], x[1]))
    errs = Counter(c for lv, c, *_ in issues if lv == "E")
    warns = Counter(c for lv, c, *_ in issues if lv == "W")
    lines = [f"{lv} {code} slides/deck.html:{ln} {msg}" for lv, code, ln, msg in issues]
    lines.append(f"共 {n} 頁；錯誤 {sum(errs.values())} 個、警告 {sum(warns.values())} 個"
                 + (f"（{'、'.join(f'{k}×{v}' for k, v in sorted((errs + warns).items()))}）" if issues else ""))
    out = "\n".join(lines)
    print(out)
    if args.run:
        seq = len(runlog.events(args.run)) + 1
        d = W.ROOT / "runs" / args.run / "checks"
        d.mkdir(parents=True, exist_ok=True)
        name = f"{seq:02d}-C2a-{args.target}.txt"
        (d / name).write_text(out + "\n", encoding="utf-8")
        note = f"警告{sum(warns.values())}" if warns else ""
        runlog.add(args.run, "C2a", args.target, "fail" if errs else "pass", note, dict(errs), name)
    sys.exit(1 if errs else 0)


if __name__ == "__main__":
    main()
