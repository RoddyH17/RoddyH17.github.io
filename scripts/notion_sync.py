#!/usr/bin/env python3
"""Notion 取数层的实现 —— 由 scripts/notion.sh 调用,不建议直接跑。

职责只有两件:把 System III 及其日页拉下来,把 block 树转成 markdown 落盘。
判断的事(这一节属于哪天、哪道题值得抄进 practice.rs)不在这里做 —— 见 PIPELINE.md
「检索层不是结论层」。

为什么是 Python 而不是像其它脚本一样纯 bash:block → markdown 要覆盖 16 种 block
类型和富文本标注,塞进 bash 的 python3 -c 里没法维护。CLI 手感仍由 notion.sh 保持。
"""
import difflib
import glob
import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request

API = "https://api.notion.com/v1"
VERSION = "2022-06-28"  # 固定版本:新版把 database 拆成 data source,这里用不到
TOKEN = os.environ.get("NOTION_TOKEN", "")
ROOT_ID = os.environ.get("NOTION_SYSTEM_III_ID", "")
CACHE = os.environ.get("NOTION_CACHE_DIR", ".cache/notion")

# Notion 限流约 3 req/s。留一点余量。
THROTTLE = 0.34
_calls = 0


# ---------------------------------------------------------------- API 客户端

def _request(method, path, body=None):
    global _calls
    url = path if path.startswith("http") else f"{API}{path}"
    data = json.dumps(body).encode() if body is not None else None
    headers = {"Authorization": f"Bearer {TOKEN}", "Notion-Version": VERSION}
    if data:
        headers["Content-Type"] = "application/json"

    for attempt in range(5):
        time.sleep(THROTTLE)
        _calls += 1
        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            # 429 按 Retry-After 退避;5xx 指数退避。其余直接抛。
            if e.code == 429:
                wait = float(e.headers.get("Retry-After", 1))
                print(f"   限流,{wait}s 后重试…", file=sys.stderr)
                time.sleep(wait)
                continue
            if 500 <= e.code < 600 and attempt < 4:
                time.sleep(2 ** attempt)
                continue
            detail = e.read().decode(errors="replace")[:300]
            raise SystemExit(f"❌ Notion API {e.code}: {detail}")
    raise SystemExit("❌ 重试多次仍失败")


def children(block_id):
    """分页拉取一个 block 的所有直接子块。"""
    out, cursor = [], None
    while True:
        q = f"/blocks/{block_id}/children?page_size=100"
        if cursor:
            q += f"&start_cursor={cursor}"
        d = _request("GET", q)
        out += d["results"]
        if not d.get("has_more"):
            return out
        cursor = d["next_cursor"]


def fetch_tree(block_id):
    """递归拉成嵌套树。

    遇到 child_page 必须停 —— 子页会各自单独落一个文件,内联进来就会存两遍。
    """
    out = []
    for b in children(block_id):
        if b.get("has_children") and b["type"] != "child_page":
            b["_children"] = fetch_tree(b["id"])
        out.append(b)
    return out


def page_title(page):
    for v in page.get("properties", {}).values():
        if v.get("type") == "title":
            return "".join(x["plain_text"] for x in v["title"]).strip()
    return "(无标题)"


# ------------------------------------------------------------ markdown 转换

def _wrap(s, left, right=None):
    """给文本加标记,但把首尾空白留在标记外面。

    Notion 的加粗常常把尾随空格也包进去,直接写成 `** x **` 在 markdown 里不生效。
    """
    right = right or left
    core = s.strip()
    if not core:
        return s
    lead = s[: len(s) - len(s.lstrip())]
    trail = s[len(s.rstrip()):]
    return f"{lead}{left}{core}{right}{trail}"


def rich(rts):
    """rich_text 数组 → markdown 内联文本。

    顺序要紧:code 最内层,再 bold/italic,链接最外层。
    """
    parts = []
    for t in rts or []:
        s = t.get("plain_text", "")
        if t.get("type") == "equation":
            s = f"${s}$"
        a = t.get("annotations", {})
        if a.get("code"):
            s = _wrap(s, "`")
        if a.get("bold"):
            s = _wrap(s, "**")
        if a.get("italic"):
            s = _wrap(s, "*")
        if a.get("strikethrough"):
            s = _wrap(s, "~~")
        if t.get("href"):
            s = f"[{s.strip()}]({t['href']})"
        parts.append(s)
    return "".join(parts)


def _text(b):
    return rich(b.get(b["type"], {}).get("rich_text"))


def _table(b):
    """table 的行都在 children 里,cells 是 [列][rich_text]。"""
    body = b.get("table", {})
    rows = b.get("_children", [])
    lines = []
    for i, row in enumerate(rows):
        cells = row.get("table_row", {}).get("cells", [])
        lines.append("| " + " | ".join(rich(c).replace("|", "\\|") for c in cells) + " |")
        if i == 0 and body.get("has_column_header"):
            lines.append("|" + "|".join([" --- "] * len(cells)) + "|")
    return lines


def render(blocks, _depth=0):
    """block 列表 → markdown 行列表。"""
    lines = []
    counter = 0  # 有序列表的连续编号,被别的块打断就归零

    for b in blocks:
        t = b["type"]
        kids = b.get("_children", [])
        counter = counter + 1 if t == "numbered_list_item" else 0

        if t.startswith("heading_"):
            lines += ["", "#" * int(t[-1]) + " " + _text(b), ""]

        elif t == "paragraph":
            lines.append(_text(b))

        elif t == "code":
            body = b["code"]
            lang = (body.get("language") or "").replace("plain text", "text")
            lines += ["", f"```{lang}"]
            lines += "".join(x["plain_text"] for x in body["rich_text"]).split("\n")
            lines += ["```", ""]
            if body.get("caption"):
                lines += [rich(body["caption"]), ""]

        elif t == "quote":
            inner = [_text(b)] + (render(kids, _depth + 1) if kids else [])
            lines += ["", *[f"> {ln}" if ln else ">" for ln in inner], ""]

        elif t == "callout":
            # 沿用 Notion 侧已有的写法(见 PIPELINE.md 的 house style)
            body = b["callout"]
            icon = (body.get("icon") or {}).get("emoji", "")
            color = body.get("color", "default")
            inner = [_text(b)] + (render(kids, _depth + 1) if kids else [])
            lines += ["", f'<callout icon="{icon}" color="{color}">']
            lines += [f"\t{ln}" for ln in inner]
            lines += ["</callout>", ""]

        elif t == "toggle":
            lines += ["", "<details>", f"<summary>{_text(b)}</summary>", ""]
            lines += render(kids, _depth + 1)
            lines += ["", "</details>", ""]

        elif t in ("bulleted_list_item", "numbered_list_item"):
            marker = "- " if t == "bulleted_list_item" else f"{counter}. "
            lines.append(marker + _text(b))
            if kids:
                lines += ["  " + ln for ln in render(kids, _depth + 1)]

        elif t == "to_do":
            box = "x" if b["to_do"].get("checked") else " "
            lines.append(f"- [{box}] " + _text(b))
            if kids:
                lines += ["  " + ln for ln in render(kids, _depth + 1)]

        elif t == "table":
            lines += ["", *_table(b), ""]

        elif t == "image":
            body = b["image"]
            kind = body["type"]  # file = Notion 托管(签名) / external = 外链
            url = body.get(kind, {}).get("url", "")
            cap = rich(body.get("caption")) or ""
            # Notion 托管的图是 S3 签名链接,约 1 小时过期,而且**每次拉取签名都不同**。
            # 直接写进缓存的话,每跑一次 fetch,diff 就会把这些行全报成"改动过"
            # (Day3 有 7 张图 = 每次 7 行假差异)。所以剥掉查询串只留稳定路径:
            # 它不能直接访问,但 diff 从此干净;要真的用图,靠下面的 block id 回 Notion 换新链接。
            if kind == "file":
                url = url.split("?", 1)[0]
            lines += ["", f"![{cap}]({url})", f"<!-- notion-block: {b['id']} -->", ""]

        elif t == "equation":
            lines += ["", "$$", b["equation"]["expression"], "$$", ""]

        elif t == "divider":
            lines += ["", "---", ""]

        elif t == "child_page":
            lines += ["", f"<!-- child page: {b['child_page']['title']} "
                          f"(id {b['id']}) 单独落文件,不内联 -->", ""]

        elif t == "table_of_contents":
            pass  # 目录是 Notion 的渲染件,不是内容

        else:
            lines.append(f"<!-- 未处理的 block 类型: {t} -->")
            if kids:
                lines += render(kids, _depth + 1)

    return lines


def to_markdown(title, tree):
    lines = [f"# {title}", ""] + render(tree)
    out, blank = [], False
    for ln in lines:  # 折叠连续空行
        if not ln.strip():
            if blank:
                continue
            blank = True
        else:
            blank = False
        out.append(ln.rstrip())
    return "\n".join(out).strip() + "\n"


# ------------------------------------------------------------------ 缓存层

def slugify(title):
    s = re.sub(r"[^\w一-鿿]+", "-", title.lower()).strip("-")
    return s or "page"


def meta_path():
    return os.path.join(CACHE, "meta.json")


def load_meta():
    try:
        with open(meta_path()) as f:
            return json.load(f)
    except FileNotFoundError:
        return {}


CHAPTER_RE = re.compile(r"chapter\s*(\d+)", re.I)
# 半天(Day 5.5 这类补课日)是独立的一天,有自己的目录、笔记、博客和 Notion 页。
# 只抓整数会把 "Day5.5" 读成 5,和 Day 5 撞成同一个日号,_find_day 直接报重号退出。
DAY_RE = re.compile(r"day\s*(\d+(?:\.\d+)?)", re.I)

# 直接挂在 System III 下的日页归第 1 章 —— 这是当前的实际布局(Chapter 1 只是父页
# 正文里的一个标题,没有单独成页)。以后 Chapter 2 会单独建页,日页挂在它下面。
DEFAULT_CHAPTER = 1


def day_of(title):
    m = DAY_RE.search(title)
    if not m:
        return None
    raw = m.group(1)
    # 整天保持 int,这样 f"day{day}" 仍然是 day5 而不是 day5.0。
    return float(raw) if "." in raw else int(raw)


def discover():
    """父页 → (可选的 Chapter 页) → 日页,自动发现,加一天/加一章都不用改代码。

    日号只在章内唯一:Chapter 2 会重新从 Day 1 开始,所以标识是 (chapter, day)。
    """
    root = _request("GET", f"/pages/{ROOT_ID}")
    pages = [{"id": ROOT_ID, "title": page_title(root) or "System III",
              "last_edited": root["last_edited_time"],
              "kind": "root", "chapter": None, "day": None}]

    def scan(parent_id, chapter):
        for b in children(parent_id):
            if b["type"] != "child_page":
                continue
            title = b["child_page"]["title"].strip()
            cm = CHAPTER_RE.search(title)
            entry = {"id": b["id"], "title": title,
                     "last_edited": b["last_edited_time"],
                     "kind": "chapter" if cm else "day",
                     "chapter": int(cm.group(1)) if cm else chapter,
                     "day": None if cm else day_of(title)}
            pages.append(entry)
            if cm:  # 章页:继续往里找日页
                scan(b["id"], int(cm.group(1)))

    scan(ROOT_ID, DEFAULT_CHAPTER)
    return pages


# ------------------------------------------------------------------ 子命令

def _label(p):
    if p["kind"] == "root":
        return "父页"
    if p["kind"] == "chapter":
        return f"第 {p['chapter']} 章"
    if p["day"] is None:
        return "⚠️ 无日号"
    return f"C{p['chapter']}·Day {p['day']}"


def cmd_list():
    pages = discover()
    days = [p for p in pages if p["kind"] == "day"]
    print(f"System III 下共 {len(days)} 个日页:\n")
    for p in pages:
        indent = "  " if p["kind"] == "day" and any(q["kind"] == "chapter" for q in pages) else ""
        print(f"  [{_label(p):>10}] {indent}{p['title'][:50]:52} edited {p['last_edited'][:16]}")

    nameless = [p["title"] for p in days if p["day"] is None]
    if nameless:
        print(f"\n⚠️  以下页面标题里没有 Day 号,管道认不出来:")
        for t in nameless:
            print(f"   {t}")
    print(f"\nAPI 调用: {_calls}")


def cmd_fetch(force=False):
    os.makedirs(CACHE, exist_ok=True)
    meta = load_meta()
    pages = discover()
    changed = 0

    for p in pages:
        slug = slugify(p["title"])
        old = meta.get(p["id"], {})
        md_file = os.path.join(CACHE, f"{slug}.md")

        if not force and old.get("last_edited") == p["last_edited"] and os.path.exists(md_file):
            # 正文没变,但页面可能被改名或挪到别的章下 —— 这些来自 discover(),不要钱,
            # 所以跳过内容拉取时仍要把它们刷新,否则改名/换章后 meta 会永远停在旧值。
            old.update({"title": p["title"], "slug": slug, "kind": p["kind"],
                        "chapter": p["chapter"], "day": p["day"]})
            meta[p["id"]] = old
            print(f"  ⏭  {p['title'][:46]:48} 未变更,跳过")
            continue

        before = _calls
        tree = fetch_tree(p["id"])
        md = to_markdown(p["title"], tree)

        if os.path.exists(md_file):  # 留一份给 diff 比对
            os.replace(md_file, os.path.join(CACHE, f"{slug}.prev.md"))
        with open(md_file, "w") as f:
            f.write(md)
        with open(os.path.join(CACHE, f"{slug}.json"), "w") as f:
            json.dump(tree, f, ensure_ascii=False)

        meta[p["id"]] = {"title": p["title"], "slug": slug,
                         "last_edited": p["last_edited"], "kind": p["kind"],
                         "chapter": p["chapter"], "day": p["day"],
                         "chars": len(md), "blocks": len(tree),
                         "fetched": time.strftime("%Y-%m-%dT%H:%M:%S")}
        changed += 1
        print(f"  ✅ {p['title'][:46]:48} {len(md):>6} 字符, {_calls - before} 次调用")

    # 页面改名会换 slug,旧文件会留在缓存里变成孤儿 —— 清掉,免得 day/audit 读到旧内容
    live = {m["slug"] for m in meta.values()}
    orphans = [f for f in os.listdir(CACHE)
               if f != "meta.json"
               and re.sub(r"\.(prev\.md|md|json)$", "", f) not in live]
    for f in orphans:
        os.remove(os.path.join(CACHE, f))

    with open(meta_path(), "w") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    print(f"\n{changed} 页更新,{len(pages) - changed} 页跳过。API 调用: {_calls}")
    if orphans:
        print(f"清理了 {len(orphans)} 个改名遗留的孤儿缓存文件")
    print(f"缓存目录: {CACHE}/")


def _day_pages():
    return [m for m in load_meta().values() if m.get("day")]


def _find_day(day, chapter=None):
    """日号只在章内唯一,跨章重号时必须指明是哪一章。"""
    hits = [m for m in _day_pages()
            if m["day"] == day and (chapter is None or m.get("chapter") == chapter)]
    if len(hits) > 1:
        chs = sorted(m.get("chapter") for m in hits)
        raise SystemExit(f"❌ Day {day} 在第 {chs} 章里都有。请指明,例如: day {chs[0]}.{day}")
    return hits[0] if hits else None


def _parse_day_arg(arg):
    """接受 `3` 或 `2.3`(第 2 章 Day 3)。"""
    if "." in arg:
        c, d = arg.split(".", 1)
        return int(d), int(c)
    return int(arg), None


def cmd_day(arg):
    day, chapter = _parse_day_arg(arg)
    m = _find_day(day, chapter)
    if not m:
        have = sorted((x.get("chapter"), x["day"]) for x in _day_pages())
        listed = ", ".join(f"C{c}·Day{d}" for c, d in have) or "(空,先跑 fetch)"
        raise SystemExit(f"❌ 缓存里没有这一天。已有: {listed}")
    with open(os.path.join(CACHE, f"{m['slug']}.md")) as f:
        sys.stdout.write(f.read())


def cmd_diff():
    meta = load_meta()
    if not meta:
        raise SystemExit("❌ 还没有缓存,先跑 fetch")
    changed, no_history = 0, []

    for m in meta.values():
        cur_p = os.path.join(CACHE, f"{m['slug']}.md")
        prev_p = os.path.join(CACHE, f"{m['slug']}.prev.md")
        # 「没有历史」和「没有变化」是两回事,不能混为一谈报成「无变化」
        if not os.path.exists(prev_p):
            no_history.append(m["title"])
            continue
        with open(cur_p) as f:
            cur = f.read().splitlines()
        with open(prev_p) as f:
            prev = f.read().splitlines()
        if cur == prev:
            continue

        changed += 1
        add = rm = 0
        for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, prev, cur).get_opcodes():
            if tag in ("replace", "delete"):
                rm += i2 - i1
            if tag in ("replace", "insert"):
                add += j2 - j1
        print(f"\n【{m['title']}】 +{add} / -{rm} 行")
        for ln in difflib.unified_diff(prev, cur, lineterm="", n=0):
            if ln.startswith("@@") or ln[:3] in ("---", "+++"):
                continue
            if re.match(r"^[+-]#{1,4} ", ln):  # 标题增删最值得看
                print(f"   {ln[:76]}")

    if no_history:
        print(f"⚠️  {len(no_history)} 页尚无历史版本可比(首次拉取):")
        for t in no_history:
            print(f"   {t}")
    if not changed and not no_history:
        print("与上次拉取相比没有变化。")


# ------------------------------------------------- render(现场记录 → Notion)

RUST_LEARN = os.path.expanduser(os.environ.get("RUST_LEARN_DIR", "~/rust_learn"))
BLOG_POSTS = "src/content/posts/rust"

SECTION_RE = re.compile(r"^\s*//\s*-{4,}\s*(.*?)\s*-{4,}\s*$")


def _dedent(lines):
    body = [l for l in lines if l.strip()]
    if not body:
        return lines
    pad = min(len(l) - len(l.lstrip()) for l in body)
    return [l[pad:] if l.strip() else "" for l in lines]


def parse_live_notes(src):
    """把现场记录的 main.rs 拆成 {narrative, sections}。

    约定(new_day.sh 生成的骨架就是这个形状):
      //!  开头的模块文档 → 当天的导语
      // ---------- N. 标题 ----------  → 一个小节的开始
      小节里:第一行代码之前的整行注释算散文,之后的全部算代码(含行内注释)

    这样划分是因为代码前的注释通常是「老师说 / 我的理解」,而穿插在代码里的注释是
    在解释那几行代码本身 —— 把后者留在围栏里,读起来才连贯。
    """
    lines = src.split("\n")

    narrative, i = [], 0
    while i < len(lines) and (lines[i].startswith("//!") or not lines[i].strip()):
        if lines[i].startswith("//!"):
            narrative.append(lines[i][3:].strip())
        elif narrative:
            break
        i += 1

    sections, cur = [], None
    for line in lines[i:]:
        m = SECTION_RE.match(line)
        if m:
            cur = {"title": m.group(1).strip(), "prose": [], "code": []}
            sections.append(cur)
            continue
        if cur is None:
            continue
        stripped = line.strip()
        # 整行注释 + 还没出现过代码 → 散文
        if stripped.startswith("//") and not cur["code"]:
            cur["prose"].append(stripped.lstrip("/").strip())
        elif stripped or cur["code"]:
            cur["code"].append(line)

    for s in sections:
        while s["code"] and not s["code"][-1].strip():
            s["code"].pop()
        # 最后一节会把 fn main 的收尾 } 吃进来。不能无条件删最后一行 ——
        # 那一行也可能是某个辅助函数自己的闭合括号。用大括号配平来判断:
        # 只有当 } 比 { 多出一个时,末尾那个才是 main 的。
        code_only = re.sub(r"//.*", "", "\n".join(s["code"]))
        if code_only.count("}") - code_only.count("{") == 1:
            for i in range(len(s["code"]) - 1, -1, -1):
                if s["code"][i].rstrip() == "}":
                    del s["code"][i]
                    break
            while s["code"] and not s["code"][-1].strip():
                s["code"].pop()
        s["code"] = _dedent(s["code"])
        # 骨架里的「老师说:」「我的理解:」冒号后没东西 = 还没写,不是内容
        s["prose"] = [p for p in s["prose"] if p and not re.fullmatch(r".{0,6}[:：]", p)]

    return {"narrative": [n for n in narrative if n], "sections": sections}


def render_day(day, title=None):
    """dayN 的现场记录 → 要推进 Notion 的 markdown。

    两条硬规则(见 PIPELINE.md):不放练习、不放 🌟 分级;一个大标题,底下逐条列重点。
    中英文原样保留 —— 英文承载参考文本,中文承载他自己的理解,都不改写。
    """
    d, why = _day_dir(1, day)
    if why:
        raise SystemExit(f"❌ {why}")
    if not d or not d["crates"]:
        raise SystemExit(f"❌ 没找到 {RUST_LEARN}/day{day}/*/Cargo.toml")

    out = []
    for crate in d["crates"]:
        main_rs = os.path.join(crate, "src", "main.rs")
        if not os.path.exists(main_rs):
            continue
        with open(main_rs) as f:
            parsed = parse_live_notes(f.read())

        head = title or (parsed["narrative"][0] if parsed["narrative"] else f"Day {day}")
        head = re.sub(r"^Day\s*\d+\s*[—–-]\s*", "", head).strip() or f"Day {day}"
        out.append(f"# {head}")

        rest = [n for n in parsed["narrative"][1:] if n]
        if rest:
            out += ["", *[f"> {n}" for n in rest]]

        idx = 0
        for s in parsed["sections"]:
            label = re.sub(r"^\d+\.\s*", "", s["title"] or "").strip()
            body = " ".join(s["prose"])
            # 空节(标题、散文、代码都没有)是还没写的骨架,不推半成品进 Notion
            if not label and not body and not s["code"]:
                continue
            idx += 1
            out += ["", f"**{idx}. {label or '(未命名)'}**" + (f" — {body}" if body else "")]
            if s["code"]:
                out += ["", "```rust", *s["code"], "```"]

        if idx == 0:
            raise SystemExit(f"❌ day{day} 的 main.rs 还是空骨架,没有可推送的内容")

    return "\n".join(out).strip() + "\n"


# ------------------------------------------------------------------- audit


def _headings(md_text, skip_first=False):
    hs = re.findall(r"^#{1,4} (.+)$", md_text, re.M)
    return hs[1:] if skip_first and hs else hs


def _git_tracked(repo, path):
    """未追踪 ≠ 不存在。查 git 而不是拿 git 当存在性判据 —— 两件事。"""
    try:
        r = subprocess.run(["git", "-C", repo, "ls-files", "--error-unmatch", path],
                           capture_output=True, timeout=20)
        return r.returncode == 0
    except Exception:
        return None


def _day_dir(chapter, day):
    """(chapter, day) → rust_learn 目录。

    第 1 章沿用既有的扁平 dayN/。第 2 章之后会和第 1 章重号(都从 Day 1 开始),
    届时需要一个新约定 —— 这里不替他发明,直接报出来让人决定。
    """
    if chapter != 1:
        return None, f"第 {chapter} 章尚无目录约定(会与第 1 章的 day{day}/ 重名),需先决定"
    hits = sorted(glob.glob(os.path.join(RUST_LEARN, f"day{day}", "*", "Cargo.toml")))
    base = os.path.join(RUST_LEARN, f"day{day}")
    if not os.path.isdir(base):
        return None, None
    return {"base": base, "crates": [os.path.dirname(h) for h in hits]}, None


def _cargo(crate, *args, label=""):
    """真的编译一次。文件存在不等于能跑 —— 这是「原样可编译」唯一可靠的检查方式。"""
    try:
        r = subprocess.run(["cargo", "build", "--quiet", *args],
                           cwd=crate, capture_output=True, text=True, timeout=300)
        if r.returncode == 0:
            return "✅", "编译通过"
        errs = len(re.findall(r"^error", r.stderr, re.M))
        first = next((l for l in r.stderr.splitlines() if l.startswith("error")), "")
        return "⚠️", f"**编译失败**({errs} 个错误) {first[:70]}"
    except FileNotFoundError:
        return "⚠️", "本机没有 cargo,无法验证"
    except subprocess.TimeoutExpired:
        return "⚠️", "编译超时(>300s)"


def _audit_one(day):
    """以 dayN 的现场记录为参照,逐项查下游跟上了没有。

    方向很重要:源头是 rust_learn/dayN/<crate>/src/main.rs(他看视频时写的),
    Notion / NOTES / blog 都是它的下游产物。
    """
    d, why = _day_dir(1, day)
    if why:
        print(f"\nDay {day}\n  ⚠️  {why}")
        return
    if not d or not d["crates"]:
        print(f"\nDay {day}\n  ❌  {RUST_LEARN}/day{day}/ 不存在或没有 crate")
        return

    crate = d["crates"][0]
    topic = os.path.basename(crate)
    print(f"\nDay {day} — {topic}")

    # --- 源头:现场记录 ----------------------------------------------------
    main_rs = os.path.join(crate, "src", "main.rs")
    src_heads = []
    if os.path.exists(main_rs):
        with open(main_rs) as f:
            parsed = parse_live_notes(f.read())
        src_heads = [s["title"] for s in parsed["sections"] if s["title"] or s["code"]]
        mark, msg = _cargo(crate)
        filled = [s for s in parsed["sections"] if s["code"] or s["prose"]]
        print(f"  main.rs   {mark}  {len(parsed['sections'])} 个编号节"
              f"({len(filled)} 个已写内容) — {msg}")
        if not filled:
            print(f"            └─ 还是空骨架,今天的内容还没记")
        rel = os.path.relpath(main_rs, RUST_LEARN)
        if _git_tracked(RUST_LEARN, rel) is False:
            print(f"            └─ ⚠️ 未被 git 追踪(存在但没提交)")
    else:
        print(f"  main.rs   ❌  {os.path.relpath(main_rs, RUST_LEARN)} 不存在")

    # --- 调试配置 ---------------------------------------------------------
    # 改目录名或改 Cargo.toml 的包名都会静默弄坏 launch.json —— cargo 不看目录名,
    # 照跑不误,只有按 F5 才发现调试起不来。这里主动查一次。
    lj = os.path.join(RUST_LEARN, ".vscode", "launch.json")
    if os.path.exists(lj):
        with open(lj) as f:
            raw = re.sub(r"^\s*//.*$", "", f.read(), flags=re.M)
        try:
            confs = json.loads(raw).get("configurations", [])
        except json.JSONDecodeError:
            confs = None
        if confs is None:
            print("  debug     ⚠️  .vscode/launch.json 不是合法 JSON")
        else:
            # \b 会让 "Day 5" 命中 "Day 5.5 · more_match"(5 和 . 之间就是词边界),
            # 于是半天的配置被算进整天里,报出假的包名不符。禁掉后面跟数字或小数点。
            pat = rf"Day {re.escape(str(day))}(?![\d.])"
            mine = [c for c in confs if re.search(pat, c.get("name", ""))]
            if not mine:
                print(f"  debug     ❌  launch.json 里没有 Day {day} 的配置")
            else:
                pkg = ""
                toml = os.path.join(crate, "Cargo.toml")
                if os.path.exists(toml):
                    m = re.search(r'^name\s*=\s*"([^"]+)"', open(toml).read(), re.M)
                    pkg = m.group(1) if m else ""
                bad = []
                for c in mine:
                    cwd = (c.get("cwd") or "").replace("${workspaceFolder}/", "")
                    if not os.path.isdir(os.path.join(RUST_LEARN, cwd)):
                        bad.append(f"{c['name']} → 路径不存在: {cwd}")
                    f_ = (c.get("cargo") or {}).get("filter") or {}
                    if f_.get("kind") == "bin" and pkg and f_.get("name") != pkg:
                        bad.append(f"{c['name']} → filter 名 {f_.get('name')!r} ≠ 包名 {pkg!r}")
                if bad:
                    print(f"  debug     ❌  {len(mine)} 条配置有问题:")
                    for b in bad:
                        print(f"            {b}")
                else:
                    print(f"  debug     ✅  {len(mine)} 条配置,路径与包名都对得上")

    # --- practice ---------------------------------------------------------
    prac = os.path.join(crate, "examples", "practice.rs")
    if not os.path.exists(prac):
        print(f"  practice  ❌  day{day}/{topic}/examples/practice.rs 不存在")
    else:
        with open(prac) as f:
            body = f.read()
        # 数**不重复的**题号 —— 正文和注释里会多次引用同一题(如「Exercise 3(b)」、
        # 「Exercise 7 / 8」),按出现次数数会虚高。
        # mini project 用 Stage 分段而不是 Exercise,不认它会把整份练习报成 0 题。
        n_ex = len(set(re.findall(r"Exercise\s+(\d+)", body)))
        n_st = len(set(re.findall(r"Stage\s+(\d+)", body)))
        unit = "题" if n_ex >= n_st else "个 Stage"
        n_ex = max(n_ex, n_st)
        mark, msg = _cargo(crate, "--example", "practice")
        todo = "(还是 TODO 骨架)" if "Exercise 1: TODO" in body else ""
        print(f"  practice  {mark}  {n_ex} {unit}{todo} — {msg}")

    # --- Notion(中介层,不再是权威)---------------------------------------
    page = _find_day(day)
    if not page:
        print(f"  Notion    ❌  System III 下没有 Day {day} 页(或缓存过期,先 fetch)")
    else:
        n_heads = _headings(open(os.path.join(CACHE, f"{page['slug']}.md")).read(), skip_first=True)
        print(f"  Notion    ✅  {page['title']} — {page['chars']} 字符, {len(n_heads)} 个小节")
        if src_heads:
            # 不做相似度匹配 —— 两边标题不同源,自动匹配只会给出虚假的精确感。
            print(f"            源头: {' / '.join(h[:20] for h in src_heads[:5])}"
                  + (" …" if len(src_heads) > 5 else ""))
            print(f"            Notion: {' / '.join(h[:20] for h in n_heads[:5])}"
                  + (" …" if len(n_heads) > 5 else ""))
            print(f"            ↑ 是否同步需人工判断(不做自动匹配)")

    # --- NOTES.md ---------------------------------------------------------
    notes = os.path.join(d["base"], "NOTES.md")
    if os.path.exists(notes):
        with open(notes) as f:
            nh = _headings(f.read(), skip_first=True)
        print(f"  NOTES.md  ✅  day{day}/NOTES.md — {len(nh)} 个小节")
    else:
        print(f"  NOTES.md  ❌  day{day}/NOTES.md 不存在")

    # --- blog -------------------------------------------------------------
    # 文件名里小数点写成连字符:day5.5 → day-5-5-*.mdx。
    # 但这样 day-5-* 会把 day-5-5-pattern-matching.mdx 也捞进 Day 5,所以紧跟前缀
    # 的那一段不能再是数字 —— 那是下一个半天,不是这一天的正文。
    prefix = "day-" + str(day).replace(".", "-")
    slug_re = re.compile(rf"^{re.escape(prefix)}-(?!\d+-)\S*\.mdx?$")
    posts = sorted(p for p in glob.glob(os.path.join(BLOG_POSTS, f"{prefix}-*.md*"))
                   if slug_re.match(os.path.basename(p)))
    if not posts:
        print(f"  blog      ❌  {BLOG_POSTS}/{prefix}-*.mdx 不存在")
    for p in posts:
        with open(p) as f:
            head = f.read(600)
        draft = re.search(r"^draft:\s*true", head, re.M)
        print(f"  blog      {'⚠️' if draft else '✅'}  {os.path.basename(p)}"
              + ("  — 仍是草稿(draft: true),未上线" if draft else ""))


def _audit_project(path):
    """项目式学习的检查项和 dayN 不同。

    dayN 问的是「下游跟上了没有」;项目问的是「他做到哪一阶段了」。
    所以既不查 Notion 也不查博客 —— 项目做完才写博客,做的过程中不该被报成缺失。
    """
    name = os.path.basename(path)
    print(f"\n项目 {name}")

    if not os.path.exists(os.path.join(path, "Cargo.toml")):
        print(f"  ❌  {path}/Cargo.toml 不存在,不是一个 crate")
        return

    mark, msg = _cargo(path)
    print(f"  编译      {mark}  {msg}")

    main_rs = os.path.join(path, "src", "main.rs")
    if not os.path.exists(main_rs):
        print(f"  阶段      ❌  src/main.rs 不存在")
        return
    with open(main_rs) as f:
        body = f.read()

    # 「在这里写阶段 N:」后面还是空的,就说明这一阶段没动。空的判据是紧跟着
    # 下一个分隔线或下一个阶段标题,中间没有非注释代码。
    stages = re.findall(r"^//\s*[=─]*\s*阶段\s*(\d+)\s*·", body, re.M)
    # 标记整行都要吃掉(含行尾的冒号)—— 否则那个孤零零的「:」会被当成他写的代码,
    # 每一阶段都会被误报成已完成。标题后面可能还有括号说明,所以用 [^\n]* 收尾。
    marker = re.compile(r"^//\s*在这里写阶段\s*(\d+)[^\n]*\n", re.M)
    todo, done = [], []
    for m in marker.finditer(body):
        todo.append(m.group(1))
        seg = re.split(r"^// ═{10,}", body[m.end():], maxsplit=1, flags=re.M)[0]
        # 段内有非注释、非空白的行 = 他写了东西
        if any(l.strip() and not l.strip().startswith("//") for l in seg.splitlines()):
            done.append(m.group(1))
    if stages:
        total = len(todo) or len(set(stages))
        print(f"  阶段      {'✅' if done else '⚪'}  {len(done)}/{total} 已动手"
              + (f"(已写:{', '.join(done)})" if done else "(还没开始)"))

    # reflection 是这套项目式学习的核心产物,空着就等于没学
    blanks = body.count("______")
    filled_hint = "全部空着" if blanks else "已填完"
    print(f"  reflection {'⚠️' if blanks else '✅'}  {blanks} 处待填 —— {filled_hint}")

    rel = os.path.relpath(main_rs, RUST_LEARN)
    if _git_tracked(RUST_LEARN, rel) is False:
        print(f"            └─ ⚠️ 未被 git 追踪(存在但没提交)")


def cmd_audit(arg=None):
    # 以文件系统为准枚举天数 —— 源头是 dayN 目录,不是 Notion。
    # 半天(day5.5/)也是独立的一天,要单独出一行,所以日号可能是小数。
    days = sorted(float(m.group(1)) if "." in m.group(1) else int(m.group(1))
                  for m in (re.match(r"day(\d+(?:\.\d+)?)$", os.path.basename(p))
                            for p in glob.glob(os.path.join(RUST_LEARN, "day*")))
                  if m)
    if not days:
        raise SystemExit(f"❌ {RUST_LEARN} 下没有 dayN 目录")

    if arg:
        day, _chapter = _parse_day_arg(arg)
        if day not in days:
            raise SystemExit(f"❌ 没有 day{day}/。已有: {days}")
        days = [day]

    for m in days:
        _audit_one(m)

    # 项目和天是两回事:天是「看视频学了什么」,项目是「用学过的东西造了什么」,
    # 跨多天、没有 Notion 日页、也没有 examples/practice.rs。不并进 dayN 的检查里。
    if not arg:
        for p in sorted(glob.glob(os.path.join(RUST_LEARN, "projects", "*"))):
            if os.path.isdir(p):
                _audit_project(p)

    # 父页正文里还没被任何一天认领的内容 —— 最容易被忽略的一种漏
    root = next((m for m in load_meta().values() if m.get("kind") == "root"), None)
    if root and not arg:
        with open(os.path.join(CACHE, f"{root['slug']}.md")) as f:
            heads = _headings(f.read(), skip_first=True)
        # 章标题是父页的结构,不是没人认领的内容 —— 它本来就该待在那儿
        heads = [h for h in heads if not CHAPTER_RE.search(h)]
        if heads:
            print(f"\n⚠️  父页正文里还有 {len(heads)} 个小节没有被任何一天认领:")
            for h in heads[:12]:
                print(f"   {h[:66]}")
            print("   这些内容写在 Notion 里,但不属于任何一天,永远不会流向下游。")


# --------------------------------------------------------------------- main

def main():
    if not TOKEN or not ROOT_ID:
        raise SystemExit("❌ 缺 NOTION_TOKEN / NOTION_SYSTEM_III_ID(应由 notion.sh 从 .env 载入)")

    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    args = sys.argv[2:]

    if cmd == "list":
        cmd_list()
    elif cmd == "fetch":
        cmd_fetch(force="--force" in args)
    elif cmd == "day":
        if not args or not re.fullmatch(r"\d+(\.\d+)?", args[0]):
            raise SystemExit("❌ 用法: notion.sh day <N>  或  day <章>.<N>")
        cmd_day(args[0])
    elif cmd == "diff":
        cmd_diff()
    elif cmd == "audit":
        if args and not re.fullmatch(r"\d+(\.\d+)?", args[0]):
            raise SystemExit("❌ 用法: notion.sh audit [N]  或  audit <章>.<N>")
        cmd_audit(args[0] if args else None)
    elif cmd == "render":
        if not args or not args[0].isdigit():
            raise SystemExit("❌ 用法: notion.sh render <N>")
        sys.stdout.write(render_day(int(args[0])))
    else:
        raise SystemExit(f"❌ 未知命令: {cmd or '(空)'}")


if __name__ == "__main__":
    main()
