"""lint、簡報檢查、建置共用的函式：讀前置資料、讀raw原文、正規化比對。"""
import hashlib
import json
import re
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "raw"
WIKI = ROOT / "wiki"
SPECIAL = {"index.md", "log.md"}
TYPES = {"overview", "concept", "topic", "source", "discussion", "query"}

CITE = re.compile(r"〔(S\d{2})〕")
LINK = re.compile(r"\[([^\]]+)\]\(([^)\s]+)\)")
NUM = re.compile(r"(?<![A-Za-z0-9.])\d+(?:\.\d+)?")
CONVERT = re.compile(r"（(?:換算|計算)：[^）]*）")   # v2：自己算的數字寫成（計算：…）
# v2：這些不是來源的數字，W07、P03不檢查（run-01有23個錯是這類）
SKIP_NUM = [
    re.compile(r"`[^`]*`"),                                                  # 行內程式碼：檔名、來源代號
    re.compile(r"第\d+(?:\.\d+)?(?:\s*[到至、～-]\s*\d+)*\s*[頁點步節版次]"),   # 內部編號：第9頁、第4.5節
    re.compile(r"共\d+頁|重點\s*\d+(?:\s*[到至、～-]\s*\d+)*"),
    re.compile(r"（(?:西元)?\d{4}年）|（民國\d+年）"),                        # 年份補註：113年（2024年）
]


def registry():
    return json.loads((RAW / "_sources.json").read_text(encoding="utf-8"))


def fetched():
    """已取得的來源：{Sxx: entry}"""
    return {e["id"]: e for e in registry()["sources"] if e.get("id")}


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def split_front(text):
    """回傳 (前置資料dict, 正文, 正文從第幾行開始)。"""
    meta = {}
    if not text.startswith("---\n"):
        return meta, text, 1
    end = text.find("\n---\n", 4)
    if end < 0:
        return meta, text, 1
    block = text[4:end]
    key = None
    for line in block.split("\n"):
        m = re.match(r"^([A-Za-z_]+):\s*(.*)$", line)
        if m:
            key, val = m.group(1), m.group(2).strip()
            if val.startswith("[") and val.endswith("]"):
                val = [x.strip() for x in val[1:-1].split(",") if x.strip()]
            meta[key] = val
        elif key and line.startswith("  - "):
            if not isinstance(meta.get(key), list):
                meta[key] = []
            meta[key].append(line[4:].strip())
    body = text[end + 5:]
    start = text[:end + 5].count("\n") + 1
    return meta, body, start


_raw_cache = {}


def raw_body(sid):
    if sid not in _raw_cache:
        e = fetched().get(sid)
        if not e:
            return None
        _, body, _ = split_front((RAW / e["file"]).read_text(encoding="utf-8"))
        _raw_cache[sid] = body
    return _raw_cache[sid]


def norm(s):
    """比對用：『』當成「」、全形半形統一（NFKC）、去掉所有空白。"""
    s = s.replace("『", "「").replace("』", "」")
    s = unicodedata.normalize("NFKC", s)
    return re.sub(r"\s+", "", s)


def has_number(num, text):
    """num 是否以獨立數字出現在 text（5 不算出現在 5.0 裡）。"""
    t = unicodedata.normalize("NFKC", text)
    return re.search(rf"(?<![\d.]){re.escape(num)}(?!\.?\d)", t) is not None


def numbers_in(text):
    """抓出要檢查的數字：去掉出處標記、換算和計算括號、連結網址、行內程式碼、內部編號、年份補註。"""
    t = CONVERT.sub("", CITE.sub("", text))   # 換算括號是全形，要在NFKC之前拿掉
    for pat in SKIP_NUM:
        t = pat.sub("", t)
    t = LINK.sub(lambda m: m.group(1), t)
    t = unicodedata.normalize("NFKC", t)
    return NUM.findall(t)


def wiki_pages():
    """wiki/ 底下除了 index.md、log.md 的所有頁面（相對 wiki/ 的路徑）。"""
    out = []
    for p in sorted(WIKI.rglob("*.md")):
        rel = p.relative_to(WIKI).as_posix()
        if rel not in SPECIAL:
            out.append(rel)
    return out


def resolve(from_rel, href):
    """把頁面裡的相對連結換成相對 wiki/ 的路徑；外部連結回傳 None。"""
    if re.match(r"^[a-z]+://", href) or href.startswith("mailto:"):
        return None
    href = href.split("#", 1)[0]
    if not href:
        return from_rel
    base = (WIKI / from_rel).parent
    target = (base / href).resolve()
    try:
        return target.relative_to(WIKI.resolve()).as_posix()
    except ValueError:
        return "../" + href  # 指到 wiki/ 外面
