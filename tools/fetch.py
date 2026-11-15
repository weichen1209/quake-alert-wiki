"""取得資料（N1）：把來源清單裡的一篇來源下載、轉成文字，存進 raw/。

用法：
  python3 tools/fetch.py --list          列出來源清單與是否已取得
  python3 tools/fetch.py <key>           取得一篇，自動編號 Sxx
raw/ 裡的檔案寫入後不能修改（lint 的 W10 比對 SHA-256）。
HTML 只用標準函式庫解析；PDF 用 poppler 的 pdftotext 轉文字。
"""
import datetime
import hashlib
import html
import json
import re
import subprocess
import sys
import tempfile
import urllib.request
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "raw"
REGISTRY = RAW / "_sources.json"
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130 Safari/537.36"

BLOCK = {"p", "div", "li", "ul", "ol", "h1", "h2", "h3", "h4", "h5", "h6", "tr", "table",
         "section", "article", "header", "footer", "blockquote", "figure", "figcaption", "dd", "dt"}
SKIP = {"script", "style", "noscript", "svg", "button", "nav", "form", "select", "iframe"}
VOID = {"br", "img", "meta", "link", "input", "hr", "source", "wbr", "area", "col", "embed", "param", "track"}
CJK = r"　-〿㐀-鿿＀-￯"


class Extract(HTMLParser):
    """擷取符合條件的元素（可多個）裡的文字，區塊元素換行、表格儲存格用「 | 」分隔。"""

    def __init__(self, specs):
        super().__init__(convert_charrefs=True)
        self.specs = specs  # [(tag, 屬性名, 要包含的字串)]
        self.depth = 0      # >0 表示正在擷取
        self.skip = 0
        self.cell = 0       # >0 表示在表格儲存格裡（區塊元素不換行）
        self.out = []

    def _match(self, tag, attrs):
        a = dict(attrs)
        for t, name, needle in self.specs:
            if tag == t and needle in (a.get(name) or ""):
                return True
        return False

    def handle_starttag(self, tag, attrs):
        if tag in VOID:
            if self.depth and tag == "br":
                self.out.append("\n")
            return
        if self.depth:
            self.depth += 1
            if tag in SKIP:
                self.skip += 1
            if tag in ("td", "th"):
                self.cell += 1
            elif tag in BLOCK:
                self.out.append(" " if self.cell else "\n")
        elif self._match(tag, attrs):
            self.depth = 1
            self.out.append("\n\n")

    def handle_endtag(self, tag):
        if tag in VOID or not self.depth:
            return
        if tag in SKIP and self.skip:
            self.skip -= 1
        if tag in ("td", "th"):
            self.cell = max(0, self.cell - 1)
            self.out.append(" | ")
        elif tag in BLOCK:
            self.out.append(" " if self.cell and tag != "tr" else "\n")
        self.depth -= 1

    def handle_data(self, data):
        if self.depth and not self.skip:
            # HTML 原始碼裡的換行和縮排只算空白，換行由區塊元素決定
            self.out.append(re.sub(r"\s+", " ", data))


def tidy(text):
    """只整理空白：刪掉中文字旁邊的空白、合併多餘空白與空行，文字本身不改。"""
    lines = []
    for line in text.split("\n"):
        line = re.sub(r"[ \t ]+", " ", line).strip(" |")
        if " | " in line:  # 表格列：同一格裡被區塊隔開的兩段中文用「／」分開
            line = re.sub(rf"(?<=[{CJK}]) (?=[{CJK}])", "／", line)
        line = re.sub(rf"(?<=[{CJK}]) +", "", line)
        line = re.sub(rf" +(?=[{CJK}])", "", line)
        line = line.strip()
        if line:
            lines.append(line)
    return "\n".join(lines)


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=40) as r:
        return r.read()


def from_html(url, specs, title_spec=None):
    raw = get(url).decode("utf-8", "replace")
    parts = []
    if title_spec:
        p = Extract(title_spec)
        p.feed(raw)
        parts.append(tidy("".join(p.out)))
    p = Extract(specs)
    p.feed(raw)
    parts.append(tidy("".join(p.out)))
    return "\n".join(x for x in parts if x)


def from_pdf(url):
    data = get(url)
    with tempfile.NamedTemporaryFile(suffix=".pdf") as f:
        f.write(data)
        f.flush()
        txt = subprocess.run(["pdftotext", "-enc", "UTF-8", f.name, "-"],
                             capture_output=True, text=True, check=True).stdout
    # 中文 PDF 的換行多半是排版折行：前後都是中文字或數字時接回去
    txt = txt.replace("\f", "\n")
    txt = re.sub(rf"(?<=[{CJK}0-9A-Za-z）)])\n(?=[{CJK}0-9（(])", "", txt)
    return tidy(txt)


def trim(body, part):
    """去掉分享鈕、上一篇下一篇、側欄選單這類不是正文的行（規則寫在 _sources.json）。"""
    lines = body.split("\n")
    if part.get("start"):
        idx = next((i for i, l in enumerate(lines) if re.search(part["start"], l)), 0)
        lines = lines[idx:]
    if part.get("stop"):
        idx = next((i for i, l in enumerate(lines) if re.search(part["stop"], l)), len(lines))
        lines = lines[:idx]
    drops = [re.compile(x) for x in part.get("drop", [])]
    lines = [l for l in lines if not any(d.fullmatch(l) for d in drops)]
    if part.get("dedupe"):
        seen, kept = set(), []
        for l in lines:
            if l not in seen:
                kept.append(l)
                seen.add(l)
        lines = kept
    return "\n".join(lines)


def build_text(entry):
    chunks = []
    for part in entry["parts"]:
        if part["kind"] == "html":
            body = from_html(part["url"], [tuple(s) for s in part["specs"]],
                             [tuple(s) for s in part.get("title_specs", [])] or None)
        else:
            body = from_pdf(part["url"])
        body = trim(body, part)
        head =f"【{part['heading']}】\n網址：{part['url']}\n" if part.get("heading") else ""
        chunks.append(head + body)
    return "\n\n".join(chunks)


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load():
    return json.loads(REGISTRY.read_text(encoding="utf-8"))


def save(reg):
    REGISTRY.write_text(json.dumps(reg, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main():
    reg = load()
    if len(sys.argv) < 2 or sys.argv[1] == "--list":
        for e in reg["sources"]:
            print(f"{e.get('id') or '---'}  {e['key']:<22} {e['title']}")
        return
    key = sys.argv[1]
    entry = next((e for e in reg["sources"] if e["key"] == key), None)
    if entry is None:
        sys.exit(f"來源清單裡沒有 {key}")
    if entry.get("id"):
        sys.exit(f"{key} 已經取得（{entry['id']}），raw/ 的檔案不能覆蓋")
    used = [int(e["id"][1:]) for e in reg["sources"] if e.get("id")]
    sid = f"S{(max(used) + 1 if used else 1):02d}"
    today = datetime.date.today().isoformat()
    body = build_text(entry)
    urls = "\n".join(f"  - {p['url']}" for p in entry["parts"])
    front = (
        "---\n"
        f"id: {sid}\n"
        f"title: {entry['title']}\n"
        f"publisher: {entry['publisher']}\n"
        f"published: {entry.get('published', '未標示')}\n"
        f"urls:\n{urls}\n"
        f"retrieved: {today}\n"
        f"license: {entry['license']}\n"
        f"note: {entry.get('note', '只收文字，圖片未收錄；空白已整理，文字未改')}\n"
        "---\n\n"
    )
    path = RAW / f"{sid}-{key}.md"
    path.write_text(front + body + "\n", encoding="utf-8")
    entry.update({"id": sid, "file": path.name, "retrieved": today,
                  "sha256": sha256(path), "chars": len(body)})
    save(reg)
    print(f"{sid} {entry['title']}：{len(body)} 字元 → raw/{path.name}")


if __name__ == "__main__":
    main()
