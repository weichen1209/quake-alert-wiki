"""N7 建置：把 wiki/、raw/、slides/、runs/ 轉成 docs/（GitHub Pages 從 main 的 /docs 發佈）。

  python3 tools/build.py
只用標準函式庫；docs/ 每次整個重建，不要手改。
"""
import html
import json
import math
import os
import random
import re
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import wikilib as W  # noqa: E402

ROOT = W.ROOT
DOCS = ROOT / "docs"
REPO = "https://github.com/weichen1209/quake-alert-wiki"
TYPE_LABEL = {"overview": "總覽", "concept": "概念", "topic": "主題", "source": "來源摘要",
              "discussion": "討論單", "query": "查詢"}
TYPE_COLOR = {"overview": "#1c1b18", "concept": "#2c6e8f", "topic": "#c4362c", "source": "#7a7366",
              "discussion": "#d47a22", "query": "#2f7d4f"}


def esc(s):
    return html.escape(s, quote=True)


def rel(from_out, to_out):
    """docs 底下兩個檔案之間的相對路徑。"""
    return os.path.relpath(to_out, os.path.dirname(from_out) or ".").replace(os.sep, "/")


# ---------------- Markdown（只支援 AGENTS.md 第4.7節的範圍，外加程式碼區塊） ----------------

class Ctx:
    def __init__(self, out_rel, cite_map, md_dir="", keep_cites=False):
        self.out_rel = out_rel      # 這頁輸出到 docs/ 的哪裡
        self.cite_map = cite_map    # Sxx -> docs 底下來源摘要頁的位置
        self.md_dir = md_dir
        self.keep_cites = keep_cites   # 執行紀錄照原樣顯示〔Sxx〕，不轉成上標連結

    def href(self, h):
        if re.match(r"^[a-z]+://", h) or h.startswith("#") or h.startswith("mailto:"):
            return h
        path, _, frag = h.partition("#")
        if path.endswith(".md"):
            path = path[:-3] + ".html"
            if path.endswith("README.html") and "runs/" in (self.md_dir + "/" + path):
                pass
        elif path.endswith(".txt"):
            path = path[:-4] + ".html"
        return path + ("#" + frag if frag else "")


def inline(text, ctx):
    out = []
    for part in re.split(r"(`[^`]+`)", text):
        if len(part) > 1 and part.startswith("`") and part.endswith("`"):
            out.append(f"<code>{esc(part[1:-1])}</code>")
            continue
        s = esc(part)
        s = re.sub(r"\[([^\]]+)\]\(([^)\s]+)\)",
                   lambda m: f'<a href="{esc(ctx.href(html.unescape(m.group(2))))}">{m.group(1)}</a>', s)
        s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)

        def cite(m):
            sid = m.group(1)
            target = ctx.cite_map.get(sid)
            if not target:
                return f'<span class="cite">{sid}</span>'
            return f'<a class="cite" href="{esc(rel(ctx.out_rel, target))}">{sid}</a>'
        if not ctx.keep_cites:
            s = re.sub(r"〔(S\d{2})〕", cite, s)
        out.append(s)
    return "".join(out)


def md_to_html(md, ctx):
    lines = md.split("\n")
    out, i = [], 0
    while i < len(lines):
        line = lines[i]
        s = line.strip()
        if not s:
            i += 1
            continue
        if s.startswith("```"):
            j = i + 1
            while j < len(lines) and not lines[j].strip().startswith("```"):
                j += 1
            out.append("<pre><code>" + esc("\n".join(lines[i + 1:j])) + "</code></pre>")
            i = j + 1
            continue
        m = re.match(r"^(#{1,4})\s+(.*)$", s)
        if m:
            lv = len(m.group(1))
            text = m.group(2)
            hid = re.sub(r"[^\w㐀-鿿]+", "-", text).strip("-")
            out.append(f'<h{lv} id="{esc(hid)}">{inline(text, ctx)}</h{lv}>')
            i += 1
            continue
        if re.fullmatch(r"(-{3,}|\*{3,})", s):
            out.append("<hr>")
            i += 1
            continue
        m = re.fullmatch(r"!\[([^\]]*)\]\(([^)\s]+\.svg)\)", s)  # 只給 FLOW.md 放流程圖（templates/ 的svg複製到 docs/ 根目錄）
        if m:
            out.append(f'<figure class="flow"><img src="{esc(m.group(2).split("/")[-1])}" alt="{esc(m.group(1))}">'
                       f"<figcaption>{inline(m.group(1), ctx)}</figcaption></figure>")
            i += 1
            continue
        if s.startswith("|") and i + 1 < len(lines) and re.match(r"^\s*\|?\s*:?-{3,}", lines[i + 1]):
            head = [c.strip() for c in s.strip("|").split("|")]
            rows = []
            j = i + 2
            while j < len(lines) and lines[j].strip().startswith("|"):
                rows.append([c.strip() for c in lines[j].strip().strip("|").split("|")])
                j += 1
            t = ["<div class=\"tablewrap\"><table><thead><tr>"] + [f"<th>{inline(c, ctx)}</th>" for c in head] + ["</tr></thead><tbody>"]
            for r in rows:
                t.append("<tr>" + "".join(f"<td>{inline(c, ctx)}</td>" for c in r) + "</tr>")
            t.append("</tbody></table></div>")
            out.append("".join(t))
            i = j
            continue
        if s.startswith(">"):
            j, buf = i, []
            while j < len(lines) and lines[j].strip().startswith(">"):
                buf.append(lines[j].strip()[1:].strip())
                j += 1
            out.append("<blockquote>" + md_to_html("\n".join(buf), ctx) + "</blockquote>")
            i = j
            continue
        if re.match(r"^\s*([-*]|\d+\.)\s+", line):
            j, items = i, []
            while j < len(lines):
                l2 = lines[j]
                mm = re.match(r"^(\s*)([-*]|\d+\.)\s+(.*)$", l2)
                if mm:
                    items.append([len(mm.group(1).replace("\t", "  ")), mm.group(2), mm.group(3)])
                    j += 1
                elif l2.strip() and l2.startswith("  ") and items:
                    items[-1][2] += " " + l2.strip()
                    j += 1
                else:
                    break
            out.append(render_list(items, ctx))
            i = j
            continue
        j, buf = i, []
        while j < len(lines):
            l2 = lines[j].strip()
            if not l2 or l2.startswith(("#", "|", ">", "```")) or re.match(r"^\s*([-*]|\d+\.)\s+", lines[j]):
                break
            buf.append(l2)
            j += 1
        out.append(f"<p>{inline(' '.join(buf), ctx)}</p>")
        i = j
    return "\n".join(out)


def render_list(items, ctx):
    base = items[0][0]
    ordered = items[0][1][0].isdigit()
    tag = "ol" if ordered else "ul"
    html_parts, k = [f"<{tag}>"], 0
    while k < len(items):
        ind, _, text = items[k]
        sub = []
        k2 = k + 1
        while k2 < len(items) and items[k2][0] > base:
            sub.append(items[k2])
            k2 += 1
        html_parts.append(f"<li>{inline(text, ctx)}" + (render_list(sub, ctx) if sub else "") + "</li>")
        k = k2
    html_parts.append(f"</{tag}>")
    return "".join(html_parts)


# ---------------- 網站版型 ----------------

CSS = """
:root{--paper:#f4efe6;--paper-2:#ebe3d3;--card:#fbf8f2;--ink:#1c1b18;--ink-2:#45413a;--muted:#7a7366;--rule:#d8cfbd;
--alert:#c4362c;--alert-soft:#f6dcd6;--p:#2c6e8f;--p-soft:#dbe9ef;--ok:#2f7d4f;
--serif:"Noto Serif TC","Songti TC",serif;--sans:"Noto Sans TC","PingFang TC","Microsoft JhengHei",sans-serif;--mono:"JetBrains Mono",ui-monospace,Menlo,monospace}
*{box-sizing:border-box}html{-webkit-text-size-adjust:100%}
body{margin:0;background:var(--paper);color:var(--ink);font:16px/1.75 var(--sans)}
a{color:var(--p)}a:hover{color:var(--alert)}
header.top{border-bottom:1px solid var(--rule);background:var(--card)}
header.top .in{max-width:1180px;margin:0 auto;padding:12px 16px;display:flex;flex-wrap:wrap;gap:8px 18px;align-items:baseline}
header.top .brand{font:900 20px/1.2 var(--serif);color:var(--ink);text-decoration:none}
header.top nav a{font-size:14px;color:var(--ink-2);text-decoration:none;margin-right:12px}
header.top nav a:hover,header.top nav a.on{color:var(--alert)}
.wrap{max-width:1180px;margin:0 auto;padding:24px 16px 64px;display:grid;grid-template-columns:minmax(0,1fr) 260px;gap:40px}
.wrap.single{grid-template-columns:minmax(0,1fr)}
main{min-width:0}
aside.side{font-size:14px;border-left:1px solid var(--rule);padding-left:20px}
aside.side h4{font:700 13px var(--mono);letter-spacing:.06em;color:var(--muted);margin:18px 0 6px}
aside.side ul{list-style:none;padding:0;margin:0}aside.side li{margin:2px 0}
aside.side a{text-decoration:none;color:var(--ink-2)}aside.side a.on{color:var(--alert);font-weight:700}
h1,h2,h3,h4{font-family:var(--serif);line-height:1.35}
h1{font-size:30px;margin:.2em 0 .4em}h2{font-size:22px;margin:1.6em 0 .5em;padding-top:.4em;border-top:1px solid var(--rule)}
h3{font-size:18px;margin:1.3em 0 .4em}
.meta{font-size:14px;color:var(--muted);margin:0 0 1.2em;padding:10px 14px;background:var(--card);border:1px solid var(--rule);border-radius:8px}
.meta .type{font:600 12px var(--mono);color:#fff;padding:2px 8px;border-radius:4px;margin-right:8px}
.meta .summary{display:block;color:var(--ink-2);font-size:15px;margin-top:4px}
.meta code,.meta a{overflow-wrap:anywhere;word-break:break-all}
a.cite,span.cite{font:600 11px var(--mono);vertical-align:super;text-decoration:none;color:var(--alert);margin:0 1px}
blockquote{margin:1em 0;padding:.6em 1em;border-left:4px solid var(--p);background:var(--p-soft)}
blockquote p{margin:.2em 0}
.tablewrap{overflow-x:auto;margin:1em 0}
table{border-collapse:collapse;min-width:60%;background:var(--card);font-size:15px}
th,td{border:1px solid var(--rule);padding:6px 10px;vertical-align:top;text-align:left}th{background:var(--paper-2)}
code{font:14px var(--mono);background:var(--paper-2);padding:1px 4px;border-radius:3px}
pre{background:#22201c;color:#efe9dc;padding:14px 16px;border-radius:8px;overflow-x:auto;font:13px/1.6 var(--mono)}
pre code{background:none;color:inherit;padding:0}
pre.raw{background:var(--card);color:var(--ink);border:1px solid var(--rule);white-space:pre-wrap;word-break:break-all;font:14px/1.8 var(--sans)}
.backlinks{margin-top:2.5em;padding-top:1em;border-top:1px dashed var(--rule);font-size:14px}
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(230px,1fr));gap:14px;margin:1.2em 0}
.cards a{display:block;background:var(--card);border:1px solid var(--rule);border-top:5px solid var(--ink);border-radius:10px;padding:14px 16px;text-decoration:none;color:var(--ink)}
.cards a:hover{border-top-color:var(--alert)}
.cards b{display:block;font:900 18px var(--serif);margin-bottom:4px}.cards span{font-size:14px;color:var(--muted)}
.stats{display:flex;flex-wrap:wrap;gap:22px;margin:1em 0}.stats div{font:600 28px var(--mono);color:var(--alert)}
.stats small{display:block;font:13px var(--sans);color:var(--muted)}
.graph svg{width:100%;height:auto;background:var(--card);border:1px solid var(--rule);border-radius:10px}
.graph text{font:12px var(--sans);fill:var(--ink)}.graph line{stroke:#bdb3a0;stroke-width:1}
.legend span{display:inline-block;margin-right:14px;font-size:13px}.legend i{display:inline-block;width:10px;height:10px;border-radius:50%;margin-right:5px}
figure.flow{margin:1em 0 2em}figure.flow img{width:100%;height:auto;background:var(--card);border:1px solid var(--rule);border-radius:10px}
figure.flow figcaption{font-size:14px;color:var(--muted)}
footer.bot{border-top:1px solid var(--rule);font-size:13px;color:var(--muted);text-align:center;padding:18px 16px}
@media(max-width:860px){.wrap{grid-template-columns:minmax(0,1fr)}aside.side{border-left:0;border-top:1px solid var(--rule);padding:12px 0 0}}
"""

NAV = [("index.html", "首頁"), ("slides/index.html", "教學簡報"), ("wiki/index.html", "Wiki目錄"),
       ("graph.html", "頁面關係圖"), ("flow.html", "流程圖"), ("runs/index.html", "執行紀錄"),
       ("map.html", "簡報對應表"), ("AGENTS.html", "規則")]


def page(out_rel, title, body, side=""):
    nav = "".join(f'<a href="{esc(rel(out_rel, h))}"{" class=on" if h == out_rel else ""}>{t}</a>' for h, t in NAV)
    css = rel(out_rel, "assets/site.css")
    wrap = "wrap" if side else "wrap single"
    side_html = f'<aside class="side">{side}</aside>' if side else ""
    return f"""<!doctype html>
<html lang="zh-Hant"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)}｜地震預警LLM Wiki</title>
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Noto+Sans+TC:wght@400;700&family=Noto+Serif+TC:wght@600;900&family=JetBrains+Mono:wght@400;600&display=swap" rel="stylesheet">
<link rel="stylesheet" href="{esc(css)}"></head>
<body><header class="top"><div class="in"><a class="brand" href="{esc(rel(out_rel, 'index.html'))}">地震預警LLM Wiki</a><nav>{nav}</nav></div></header>
<div class="{wrap}"><main>{body}</main>{side_html}</div>
<footer class="bot">資料來源：交通部中央氣象署等公開資料（見各來源頁的授權說明）｜<a href="{REPO}">GitHub</a></footer>
</body></html>
"""


def write(out_rel, text):
    p = DOCS / out_rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")


# ---------------- 主程式 ----------------

def main():
    if DOCS.exists():
        shutil.rmtree(DOCS)
    DOCS.mkdir()
    write("assets/site.css", CSS)
    (DOCS / ".nojekyll").write_text("", encoding="utf-8")

    got = W.fetched()
    pages = W.wiki_pages()
    metas, bodies = {}, {}
    for r in pages:
        meta, body, _ = W.split_front((W.WIKI / r).read_text(encoding="utf-8"))
        metas[r], bodies[r] = meta, body
    cite_map = {}
    for sid in got:
        c = [r for r in pages if r.startswith(f"sources/{sid}-")]
        if c:
            cite_map[sid] = "wiki/" + c[0][:-3] + ".html"

    # 連結關係（給反向連結和關係圖）
    edges = set()
    for r in pages:
        for m in W.LINK.finditer(bodies[r]):
            t = W.resolve(r, m.group(2))
            if t in metas and t != r:
                edges.add((r, t))

    # 側欄：依類型列出頁面
    def side_for(out_rel, current=None):
        groups = []
        for typ in ["overview", "concept", "topic", "source", "query", "discussion"]:
            items = [r for r in pages if metas[r].get("type") == typ]
            if not items:
                continue
            lis = "".join(
                f'<li><a href="{esc(rel(out_rel, "wiki/" + r[:-3] + ".html"))}"{" class=on" if r == current else ""}>{esc(metas[r].get("title", r))}</a></li>'
                for r in items)
            groups.append(f"<h4>{TYPE_LABEL[typ]}（{len(items)}）</h4><ul>{lis}</ul>")
        return "".join(groups)

    # Wiki 各頁
    for r in pages:
        out_rel = "wiki/" + r[:-3] + ".html"
        meta = metas[r]
        ctx = Ctx(out_rel, cite_map)
        typ = meta.get("type", "")
        srcs = meta.get("sources") or []
        chips = " ".join(
            f'<a class="cite" href="{esc(rel(out_rel, cite_map[s]))}">{s}</a>' if s in cite_map else s for s in srcs)
        head = (f'<div class="meta"><span class="type" style="background:{TYPE_COLOR.get(typ, "#555")}">{TYPE_LABEL.get(typ, typ)}</span>'
                f'更新{esc(str(meta.get("updated", "")))}　來源{chips or "－"}'
                f'<span class="summary">{inline(str(meta.get("summary", "")), ctx)}</span></div>')
        body = md_to_html(bodies[r], ctx)
        if not body.lstrip().startswith("<h1"):
            body = f"<h1>{esc(meta.get('title', r))}</h1>" + head + body
            head = ""
        else:
            body = body.replace("</h1>", "</h1>" + head, 1)
            head = ""
        back = sorted(a for a, b in edges if b == r)
        bl = ""
        if back:
            bl = '<div class="backlinks"><b>連到這頁的頁面</b><ul>' + "".join(
                f'<li><a href="{esc(rel(out_rel, "wiki/" + a[:-3] + ".html"))}">{esc(metas[a].get("title", a))}</a></li>' for a in back) + "</ul></div>"
        if typ == "source":
            sid = (srcs or [""])[0]
            e = got.get(sid)
            if e:
                raw_out = "raw/" + e["file"][:-3] + ".html"
                bl = f'<p><a href="{esc(rel(out_rel, raw_out))}">看原始來源全文（{sid}）</a></p>' + bl
        write(out_rel, page(out_rel, meta.get("title", r), (head if head else "") + body + bl, side_for(out_rel, r)))

    for special in ["index.md", "log.md"]:
        f = W.WIKI / special
        if f.exists():
            out_rel = "wiki/" + special[:-3] + ".html"
            ctx = Ctx(out_rel, cite_map)
            write(out_rel, page(out_rel, "Wiki目錄" if special == "index.md" else "Wiki紀錄",
                                md_to_html(f.read_text(encoding="utf-8"), ctx), side_for(out_rel)))

    # 原始來源
    for sid, e in sorted(got.items()):
        text = (W.RAW / e["file"]).read_text(encoding="utf-8")
        meta, body, _ = W.split_front(text)
        out_rel = "raw/" + e["file"][:-3] + ".html"
        urls = meta.get("urls") or []
        if isinstance(urls, str):
            urls = [urls]
        info = (f"<h1>{sid} {esc(e['title'])}</h1><div class=\"meta\">發布者：{esc(e['publisher'])}<br>"
                f"發布日期：{esc(str(meta.get('published', '')))}<br>取得日期：{esc(e['retrieved'])}<br>"
                f"授權：{esc(e['license'])}<br>網址：" + "<br>".join(f'<a href="{esc(u)}">{esc(u)}</a>' for u in urls) +
                f"<br>SHA-256：<code>{e['sha256']}</code></div>"
                "<p>這是<code>tools/fetch.py</code>取得時存下的文字，之後不再修改；只收文字，圖片沒有收錄。</p>")
        write(out_rel, page(out_rel, f"{sid}原始來源", info + f'<pre class="raw">{esc(body.strip())}</pre>'))

    # 簡報
    deck_src = ROOT / "slides" / "deck.html"
    slides_info = []
    if deck_src.exists():
        tpl = (ROOT / "templates" / "deck.html").read_text(encoding="utf-8")
        deck = deck_src.read_text(encoding="utf-8")
        out_rel = "slides/index.html"

        def wiki_href(p):
            return rel(out_rel, "wiki/" + p[:-3] + ".html")

        def fix_links(m):
            return f'href="{esc(wiki_href(m.group(1)))}"'

        all_wiki = []

        def per_slide(m):
            open_tag, inner = m.group(1), m.group(2)
            kind = re.search(r'data-kind="([^"]*)"', open_tag)
            kind = kind.group(1) if kind else ""
            wl = re.search(r'data-wiki="([^"]*)"', open_tag)
            paths = wl.group(1).split() if wl else []
            inner_paths = re.findall(r'data-wiki="([^"]*)"', inner)
            for ip in inner_paths:
                paths += [p for p in ip.split() if p not in paths]
            title = re.search(r"<h[12][^>]*>(.*?)</h[12]>", inner, re.S)
            title = re.sub(r"<[^>]+>", "", title.group(1)).strip() if title else ""
            slides_info.append({"kind": kind, "title": title, "wiki": paths})
            for p in paths:
                if p not in all_wiki:
                    all_wiki.append(p)
            inner = re.sub(r'href="([^":#]+\.md)"', fix_links, inner)
            foot = ""
            if paths:
                foot = '<div class="src"><span>出處</span>' + "".join(
                    f'<a href="{esc(wiki_href(p))}">{esc(metas.get(p, {}).get("title", p))}</a>' for p in paths if p in metas) + "</div>"
            if kind == "sources":
                used_src = []
                for p in all_wiki:
                    for s in metas.get(p, {}).get("sources") or []:
                        if s not in used_src:
                            used_src.append(s)
                lst = "<div class=\"cols\"><div><h3>用到的Wiki頁（%d）</h3><ul>%s</ul></div><div><h3>這些頁引用的來源（%d）</h3><ul>%s</ul></div></div>" % (
                    len(all_wiki), "".join(f'<li><a href="{esc(wiki_href(p))}">{esc(metas.get(p, {}).get("title", p))}</a></li>' for p in all_wiki),
                    len(used_src), "".join(
                        f'<li><a href="{esc(rel(out_rel, cite_map[s]))}">{s} {esc(got[s]["title"])}</a></li>' for s in sorted(used_src) if s in cite_map and s in got))
                inner = inner + lst
            return f"{open_tag}{inner}{foot}</section>"

        deck_html = re.sub(r"(<section\b[^>]*>)(.*?)</section>", per_slide, deck, flags=re.S)
        title = slides_info[0]["title"] if slides_info else "教學簡報"
        out = tpl.replace("{{TITLE}}", esc(title)).replace("{{SLIDES}}", deck_html).replace(
            "{{WIKI_HOME}}", esc(rel(out_rel, "index.html")))
        write(out_rel, out)

    # 簡報對應表
    rows = []
    for i, s in enumerate(slides_info, 1):
        srcs = []
        for p in s["wiki"]:
            for x in metas.get(p, {}).get("sources") or []:
                if x not in srcs:
                    srcs.append(x)
        rows.append(f'<tr><td><a href="slides/index.html#{i}">{i}</a></td><td>{esc(s["kind"])}</td><td>{esc(s["title"])}</td><td>' +
                    "<br>".join(f'<a href="wiki/{esc(p[:-3])}.html">{esc(metas.get(p, {}).get("title", p))}</a>' for p in s["wiki"]) +
                    "</td><td>" + " ".join(f'<a class="cite" href="{esc(cite_map[x])}">{x}</a>' for x in sorted(srcs) if x in cite_map) + "</td></tr>")
    used = {}
    for i, s in enumerate(slides_info, 1):
        for p in s["wiki"]:
            used.setdefault(p, []).append(i)
    rows2 = "".join(f'<tr><td><a href="wiki/{esc(p[:-3])}.html">{esc(metas[p].get("title", p))}</a></td><td>{TYPE_LABEL.get(metas[p].get("type"), "")}</td><td>' +
                    ("、".join(f'<a href="slides/index.html#{n}">{n}</a>' for n in used.get(p, [])) or "－") + "</td></tr>"
                    for p in pages if metas[p].get("type") in ("concept", "topic", "overview"))
    body = ("<h1>簡報對應表</h1><p>每一頁簡報用到哪些Wiki頁、這些頁引用哪些原始來源。由<code>tools/build.py</code>依簡報的<code>data-wiki</code>和Wiki頁的前置資料產生。</p>"
            "<h2>簡報 → Wiki → 來源</h2><div class=\"tablewrap\"><table><thead><tr><th>頁</th><th>種類</th><th>標題</th><th>Wiki頁</th><th>來源</th></tr></thead><tbody>"
            + "".join(rows) + "</tbody></table></div>"
            "<h2>概念、主題頁被哪幾頁簡報用到</h2><div class=\"tablewrap\"><table><thead><tr><th>Wiki頁</th><th>類型</th><th>簡報頁</th></tr></thead><tbody>"
            + rows2 + "</tbody></table></div>")
    write("map.html", page("map.html", "簡報對應表", body))

    # 頁面關係圖（簡單的力導向排版，固定亂數種子；連結照排序處理，每次建置的位置相同）
    nodes = [r for r in pages]
    rnd = random.Random(3)
    pos = {n: [rnd.uniform(0, 1), rnd.uniform(0, 1)] for n in nodes}
    k = 1 / math.sqrt(max(1, len(nodes)))
    und = {(a, b) for a, b in edges} | {(b, a) for a, b in edges}
    for it in range(400):
        disp = {n: [0.0, 0.0] for n in nodes}
        for n in nodes:   # 往中心的引力，取代每一輪把座標夾在0到1（夾住會讓節點排在邊框上）
            disp[n][0] -= (pos[n][0] - 0.5) * 0.6
            disp[n][1] -= (pos[n][1] - 0.5) * 0.6
        for a in nodes:
            for b in nodes:
                if a == b:
                    continue
                dx, dy = pos[a][0] - pos[b][0], pos[a][1] - pos[b][1]
                d = math.hypot(dx, dy) or 1e-4
                f = k * k / d
                disp[a][0] += dx / d * f
                disp[a][1] += dy / d * f
        for a, b in sorted(und):
            dx, dy = pos[a][0] - pos[b][0], pos[a][1] - pos[b][1]
            d = math.hypot(dx, dy) or 1e-4
            f = d * d / k / 2
            disp[a][0] -= dx / d * f
            disp[a][1] -= dy / d * f
        temp = 0.1 * (1 - it / 400) + 0.002
        for n in nodes:
            dx, dy = disp[n]
            d = math.hypot(dx, dy) or 1e-4
            pos[n][0] += dx / d * min(d, temp)
            pos[n][1] += dy / d * min(d, temp)
    for i in (0, 1):   # 排完再依實際範圍縮放到0到1
        lo, hi = min(p[i] for p in pos.values()), max(p[i] for p in pos.values())
        for p in pos.values():
            p[i] = (p[i] - lo) / ((hi - lo) or 1)
    Wd, Hd, pad = 1000, 700, 70

    def label(n):
        """討論單、來源、查詢頁只寫代號，完整標題放在<title>。"""
        t = metas[n].get("title", n)
        m = re.search(r"\b([DSQ]\d{2})\b", t) if metas[n].get("type") in ("discussion", "source", "query") else None
        return m.group(1) if m else t

    def xy(n):
        return pad + pos[n][0] * (Wd - 2 * pad), pad + pos[n][1] * (Hd - 2 * pad)
    deg = {n: 0 for n in nodes}
    for a, b in und:
        deg[a] += 1
    # 標籤避讓：圓點加標籤的範圍互相重疊時，把兩個節點上下推開（字寬用中文13、英數7.5估算）
    P = {n: list(xy(n)) for n in nodes}
    rad = {n: 5 + min(10, deg[n] * 0.9) for n in nodes}

    def box(n):
        x, y = P[n]
        r, w = rad[n], sum(13 if ord(c) > 255 else 7.5 for c in label(n))
        lx0, lx1 = (x - r - 3 - w, x - r - 3) if x > Wd / 2 else (x + r + 3, x + r + 3 + w)
        return min(x - r, lx0) - 2, min(y - r, y - 10) - 2, max(x + r, lx1) + 2, max(y + r, y + 6) + 2
    for _ in range(300):
        moved = False
        for i, a in enumerate(nodes):
            for b in nodes[i + 1:]:
                A, B = box(a), box(b)
                ox, oy = min(A[2], B[2]) - max(A[0], B[0]), min(A[3], B[3]) - max(A[1], B[1])
                if ox > 0 and oy > 0:
                    s = (oy / 2 + 0.5) * (1 if P[a][1] >= P[b][1] else -1)
                    P[a][1] += s
                    P[b][1] -= s
                    moved = True
        for n in nodes:
            P[n][1] = min(Hd - 22, max(22, P[n][1]))
        if not moved:
            break

    def xy(n):   # 之後畫線、畫點都用避讓後的位置
        return P[n][0], P[n][1]
    svg = [f'<svg viewBox="0 0 {Wd} {Hd}" role="img" aria-label="Wiki頁面之間的連結">']
    for a, b in sorted({tuple(sorted(e)) for e in und}):
        (x1, y1), (x2, y2) = xy(a), xy(b)
        svg.append(f'<line x1="{x1:.0f}" y1="{y1:.0f}" x2="{x2:.0f}" y2="{y2:.0f}"/>')
    for n in nodes:
        x, y = xy(n)
        r = 5 + min(10, deg[n] * 0.9)
        col = TYPE_COLOR.get(metas[n].get("type"), "#555")
        right = x > Wd / 2   # 右半邊的標籤寫在圓點左邊，才不會超出圖框
        tx, anchor = (x - r - 3, "end") if right else (x + r + 3, "start")
        svg.append(f'<a href="wiki/{esc(n[:-3])}.html"><title>{esc(metas[n].get("title", n))}</title>'
                   f'<circle cx="{x:.0f}" cy="{y:.0f}" r="{r:.1f}" fill="{col}"/>'
                   f'<text x="{tx:.0f}" y="{y + 4:.0f}" text-anchor="{anchor}">{esc(label(n))}</text></a>')
    svg.append("</svg>")
    legend = "".join(f'<span><i style="background:{TYPE_COLOR[t]}"></i>{TYPE_LABEL[t]}</span>' for t in TYPE_LABEL)
    body = (f"<h1>頁面關係圖</h1><p>{len(nodes)}個頁面、{len({tuple(sorted(e)) for e in und})}條連結（不含目錄和紀錄）。圓點越大，連到它或它連出去的頁面越多。討論單、來源和查詢頁只寫代號，滑鼠移到圓點上會顯示完整標題，點圓點可以開頁面。</p>"
            f'<p class="legend">{legend}</p><div class="graph">{"".join(svg)}</div>')
    write("graph.html", page("graph.html", "頁面關係圖", body))

    # 執行紀錄
    runs = sorted(p for p in (ROOT / "runs").glob("run-*") if p.is_dir())
    run_links = []
    for rd in runs:
        name = rd.name
        for md in sorted(rd.glob("*.md")):
            out_rel = f"runs/{name}/{md.stem}.html"
            write(out_rel, page(out_rel, f"{name} {md.stem}", md_to_html(md.read_text(encoding="utf-8"), Ctx(out_rel, cite_map, keep_cites=True))))
        for txt in sorted((rd / "checks").glob("*.txt")) if (rd / "checks").exists() else []:
            out_rel = f"runs/{name}/checks/{txt.stem}.html"
            write(out_rel, page(out_rel, txt.name, f"<h1>{esc(txt.name)}</h1><pre class=\"raw\">{esc(txt.read_text(encoding='utf-8'))}</pre>"))
        run_links.append(f'<li><a href="{name}/README.html">{name}</a>' +
                         (f'　<a href="{name}/review.html">AI審查</a>' if (rd / "review.md").exists() else "") + "</li>")
    write("runs/index.html", page("runs/index.html", "執行紀錄",
                                  "<h1>執行紀錄</h1><p>每次照流程圖執行一遍就開一個資料夾，記下每個節點的結果和檢查輸出。</p><ul>" + "".join(run_links) + "</ul>"))

    # 規則、流程圖、首頁
    for name, out_rel, title in [("AGENTS.md", "AGENTS.html", "規則AGENTS.md"), ("FLOW.md", "flow.html", "流程圖"),
                                 ("README.md", "index.html", "首頁")]:
        f = ROOT / name
        if not f.exists():
            continue
        body = md_to_html(f.read_text(encoding="utf-8"), Ctx(out_rel, cite_map))
        if name == "README.md":
            n_pages = len(pages)
            stats = (f'<div class="stats"><div>{len(got)}<small>原始來源</small></div><div>{n_pages}<small>Wiki頁面</small></div>'
                     f'<div>{len(slides_info)}<small>簡報頁</small></div><div>{len(runs)}<small>執行紀錄</small></div></div>')
            body = body.replace("<p>&lt;!--STATS--&gt;</p>", stats)   # README裡的 <!--STATS--> 經過轉義
        write(out_rel, page(out_rel, title, body))
    for svg_file in (ROOT / "templates").glob("flow-*.svg"):
        shutil.copy(svg_file, DOCS / svg_file.name)

    print(f"docs/：Wiki {len(pages)} 頁、原始來源 {len(got)} 篇、簡報 {len(slides_info)} 頁、執行紀錄 {len(runs)} 次")


if __name__ == "__main__":
    main()
