#!/usr/bin/env python3
"""Obsidian vault → Notion / 博客 的**转换层**。

职责只有两件:发现「哪些笔记是新的/改过的」,以及把 Obsidian 方言转成目标方言。
判断的事(这条概念值不值得发博客、标题怎么写)不在这里做 —— 见 PIPELINE.md
「检索层不是结论层」。

用法(经 scripts/obsidian.sh 调用):
    list                     列出 vault 里全部笔记
    changed                  对照 manifest,列出新增/修改过的笔记
    doctor [--only PREFIX]   按 vault 规范体检 frontmatter 与正文
    notion <path>            输出 Notion-flavored markdown(交给 MCP 写入)
    post <path>              输出博客 .md(含 frontmatter)
    ladder                   打印已注册的难度阶梯
    build-posts              批量生成阶梯文章
    commit                   把当前状态写进 manifest(同步成功后调用)

为什么输出 .md 而不是 .mdx:MDX 会把 `<` 和 `{` 当 JSX 解析,而 Rust 笔记里
`Vec<T>`、`Box<dyn Trait>`、`{color}` 遍地都是。posts 集合的 glob 是
`**/*.{md,mdx}`,.md 一样收,且没有 JSX 风险。
"""
import hashlib
import json
import os
import re
import sys
import unicodedata

VAULT = os.environ.get(
    "OBSIDIAN_VAULT",
    os.path.expanduser("~/Ob_workflow/obsidian/Ideas/2026"),
)
MANIFEST = os.environ.get(
    "OBSIDIAN_MANIFEST", os.path.join(os.path.dirname(__file__), "..", ".cache", "obsidian-manifest.json")
)
SKIP_DIRS = {".obsidian", ".smart-env", "_templates", "_to_delete"}


# ============================================================== 地形模型
# vault 的 frontmatter 不是分类表,是**地形图**。四个字段回答四个不同的问题
# (见 vault 的 `00 2026 Fall MOC.md` §地形元数据):
#
#   type  — 这份知识**怎样产生**?          进入森林的方式
#   layer — 它是生成脚手架还是亲历坐标?    知识与身体经验的相对位置
#   field — 它处在**哪些知识场域**?        森林、山谷与林间空地
#   tags  — 从这里**往哪走**最降低困惑?    局部可走的羊肠小径
#
# 所以 field 是名词性的层级路径(broad/specific),tags 是「动作—对象」。
# 名词说明周围有什么树,动作才说明下一步从哪里穿过去。

# 学习产物只有三种生成方式。
NOTE_TYPES = {
    "lecture":   "手写课堂记录经过识别与重组后的讲义",
    "vibelearn": "沿网站 / Notebook / 代码 / 线上课程主动学习形成的笔记",
    "knot":      "由学习症状、用户提问或概念冲突触发,经互动后形成的解结文档",
    # 下面两种是 2025 vault 迁入时补的(2026-08-28 用户拍板)。MOC 原文写的是
    # 「学习产物只有三种生成方式」—— 这是**修改上游**,不是脚本自作主张,
    # MOC 与模板已同步改。
    "tool":      "从多个已解决的问题里抽出的方法,记录触发条件、执行技术与失效边界",
    "uber":      "由一道具体问题的消化产生的笔记:解法、其中的想法、以及为什么别的路走不通",
}
# moc 是导航基础设施,不伪装成学习产物。
INFRA_TYPES = {"moc"}
LEARNING_LAYERS = {"generated", "the real"}

# `course` 已被 vault 明确废除:「frontmatter 不再用 course 把跨课程知识锁回
# 行政边界」。课程归属由**目录与 MOC** 保存,不由 frontmatter 保存。
# 下游一律不得再读它 —— doctor 会把任何残留报出来。
RETIRED_KEYS = ("course",)

# `course` 是被废除的**键**;下面这些是被废除的**值**。
# 前四个是行政边界(考试与竞赛的名字),与 course 同类 —— 2026-08-28 用户拍板删除,
# 「川大 23 年数分」这类出处改写进正文题目下方,那本来就是它该待的地方。
# `tool_idea` 是 2025 用来标工具笔记的老办法,现在由 `type: tool` 承担。
RETIRED_TAGS = ("考研", "大学数学竞赛", "中学数学竞赛", "高考", "tool_idea")

# 2025 没有可靠的出生日期:全 vault 0 篇有 created,mtime 有 317/561 挤在一次
# 整体拷贝上,git 的 --follow 也有 62% 落在同一个批量导入日。与其灌噪声进
# Holzwege 的时间索引,不如留空(2026-08-28 用户拍板)。
# 按**路径段**匹配(不是前缀):本机是 `Ideas/2025/...`,Cowork 桌面工作区把它
# 挂成 `mnt/2025/...`,`Ideas` 那一段不在。按段匹配两边都成立。
CREATED_EXEMPT = ("2025",)

# slug ↔ 工具笔记名。词表的唯一定义源,批次 1 逐条填。
# 空表时下面两条校验自动空转。
TOOLS = {
    # 批次 1 逐条填。左边是受控词表的 slug(doctor 校验这一层),右边是工具笔记名
    # (人读那一层)。规则:打了 slug 的笔记,正文里必须有对应的中文双链 ——
    # tags 从此不是形容词,是**可验证的调用记录**。工具笔记自己不必自链。
    "estimate-termwise":        "逐项估计",
    "estimate-sum-by-integral": "和的积分估计",
    "split-range-and-estimate": "分段估计",
    "give-an-epsilon-of-room":  "an epsilon of room",
    "summation-by-parts":       "基于分部求和法的和的估计",
    # 第二批
    "bound-a-limsup-of-sets":                  "Borel-Cantelli lemma及其应用",
    "lift-a-difference-bound-to-a-sequence-bound": "序列差分的估计蕴含着序列本身的估计",
    "expand-an-indicator-into-a-sum":          "把条件函数展开为新的求和然后换序",
    "prove-a-set-is-null":                     "an epsilon of room证明集合为0测度的策略",
    "verify-an-identity-on-a-dense-subset":    "identity theorem",
    "swap-the-order-of-summation":             "和以及积分换序",
    "factor-a-diophantine-equation":           "利用因式分解求解丢番图方程",
    "apply-the-pigeonhole-principle":          "鸽笼原理",
    "pass-to-a-better-subsequence":            "用子列来提升收敛或发散性质",
    "descend-to-a-smaller-solution":           "无穷递降",
    # 第三批:先登记 slug 把词表补全(边界小节随后单独补)
    "compose-from-elementary-functions":       "把函数转换为基本初等函数的复合",
    "evaluate-a-real-integral-by-residues":    "利用留数计算实积分",
    "turn-an-integral-into-a-series":          "将积分转换为级数",
    "reduce-a-matrix-to-normal-form":          "把矩阵转换为标准型从而简化问题",
    "globalise-a-local-property-by-compactness":"利用紧性把局部性质转换为全局性质",
    "exploit-an-invariant-of-the-determinant": "利用行列式的不变性简化问题",
    "bootstrap-an-estimate":                   "通过迭代提高估计精度：Bootsrap argument",
    "sum-with-a-generating-function":          "利用生成函数求和",
    "count-the-same-thing-twice":              "双重计数",
    "move-between-transform-and-series":       "傅里叶变换与傅里叶展开",
    "linearise-a-denominator":                 "分母展开公式：局部线性化",
    "induct-over-a-continuum":                 "连续的归纳法",
    "take-logs-to-simplify-monotonicity":      "对数化技巧及其推广",
    "filter-with-roots-of-unity":              "利用roots of unity filter求和",
    "bootstrap-from-a-known-asymptotic":       "利用已知的渐近结果求渐近展开的技巧",
    "set-up-coordinates-in-hilbert-space":     "在Hilbert空间当中建立坐标系从而简化问题",
    "know-a-group-by-its-action":              "Groups, as men, will be known by their actions",
    "decompose-dyadically":                    "Dyadic分解",
    "build-a-fast-rational-approximation":     "构造快速收敛的有理逼近以证明数的无理性",
    "engineer-a-telescoping-sum":              "制造telescoping sum求和",
    "strengthen-a-convergence-hypothesis":     "加强收敛性质的条件与手段",
    "set-up-limsup-liminf-inequalities":       "制造关于上下极限的不等式组",
    "complete-the-square":                     "配方从而制造出平方差",
    "smooth-the-target-with-a-parameter":      "通过添加参数让目标更光滑化",
    "integrate-by-parts":                      "基于分部积分法的积分的估计",
    "apply-combinatorial-nullstellensatz":     "组合零点定理",
    "split-with-the-hyperbola-trick":          "Dirichlet's hyperbola trick",
    "prove-existence-via-expectation":         "通过求期望证明具有某种性质的结构的存在性",
    "turn-a-set-problem-into-a-function-problem":"把集合问题转换为函数问题",
    "renormalise-to-show-nonnegativity":       "通过重整来证明表达式的非负性",
    "give-an-epsilon-of-room-in-linear-algebra":"an epsilon of room在线性代数中的运用",
    "apply-liouville-type-rigidity":           "揭露全纯以及亚纯函数信息的Liouville原则",
    "transfer-convergence-between-series":     "由一个级数收敛证明另一个有关级数的收敛问题",
    "count-in-two-ways":                       "算两次",
    "use-complex-methods-in-real-analysis":    "实分析的复办法",
    "run-backward-induction":                  "柯西的反向归纳法",
    "compute-a-limit-probabilistically":       "用概率计算含参数积分的极限",
    "test-a-polynomial-for-irreducibility":    "判断整系数多项式是否可约的方法",
    "guess-or-check-with-a-plot":              "通过图像猜测或校验答案",
}

# frontmatter 里的标量键与列表键。顺序即 Notion callout 里的呈现顺序。
SCALAR_META = ("type", "layer", "lecture", "created", "horizon", "origin")
LIST_META = ("field", "tags", "websites")

# Holzwege / Questioning 保存的是**尚未证实**的跨场域候选路径。vault 的规范写得
# 很清楚:「类比不能冒充等价;路径失败也保留为地形证据」。发布是一次断言,把候选
# 边发到站上就是让假设冒充结论 —— 所以这两个目录在**上站路径**上显式拒绝,而不是
# 靠 ladder_of 恰好返回 None 侥幸兜住。
#
# 备份路径(to_notion)不拒绝:备份不是断言,而且备份要全。
PUBLISH_DENY = ("Holzwege", "Questioning")


# ============================================================== 难度阶梯
# 阶梯是与 type / field / tags **正交**的第四样东西:它既不是知识怎样产生,也不是
# 它长在哪,而是**学习顺序**。目前只有 Rust 有阶梯。
#
# 这张表是三个平台(Obsidian 文件名前缀 / Notion 页标题 / 官网 frontmatter)编号的
# 唯一定义源。板块必须**连续** —— 阶梯的意义就在于顺着走,跳号的分组读起来是目录
# 不是阶梯。
#
# 想给别的课挂阶梯:在 LADDERS 里加一条,不用改下面任何逻辑。
LADDERS = {
    # key 是**相对 vault 的目录**,注意 "System III  Rust" 是两个空格
    # (原名带半角冒号,macOS Finder 会把冒号显示成斜杠,所以去掉了)。
    "System III  Rust/Concepts": {
        "series": "rust",
        "category": "rust",
        "modules": [
            ("基础语法与内存", "Syntax & Memory", (0, 2)),
            ("复合数据与编码", "Composite Data & Encoding", (3, 4)),
            ("代数数据类型", "Algebraic Data Types", (5, 6)),
            ("标准库与工程组织", "Std Library & Organisation", (7, 10)),
            ("抽象与内存表示进阶", "Abstraction & Representation", (11, 14)),
            ("综合应用", "Putting It Together", (15, 16)),
        ],
        "slugs": {
            0: "00-bindings-mutability-expressions",
            1: "01-ownership-and-memory",
            2: "02-borrowing-references-nll",
            3: "03-arrays-slices-fat-pointers",
            4: "04-strings-and-utf8",
            5: "05-enums-and-sum-types",
            6: "06-pattern-matching",
            7: "07-structs-impl-and-self",
            8: "08-vec-and-hashmap",
            9: "09-option-and-result",
            10: "10-modules-and-visibility",
            11: "11-trait-syntax",
            12: "12-box-and-dst",
            13: "13-recursive-data-structures",
            14: "14-dyn-and-trait-objects",
            15: "15-data-structures-by-hand",
            16: "16-search-algorithms",
        },
    },
}


def rel(path):
    return os.path.relpath(path, VAULT).replace(os.sep, "/")


def _ladder_registration(path):
    """返回命中的阶梯根、配置和根目录内的相对路径。

    阶梯允许把一个概念升级成文件夹。例如 Trait 同时保存学习前的
    `11 trait 语法.md` 与学习后的 `Traits_v1.md`。旧版只接受 Concepts 的
    直接子文件,一旦进入子目录就会静默丢失阶梯坐标。
    """
    r = rel(path)
    for root in sorted(LADDERS, key=len, reverse=True):
        if r == root or r.startswith(root + "/"):
            return root, LADDERS[root], r[len(root):].lstrip("/")
    return None


def _rung_number(path, inside):
    """先读当前文件前缀;版本文件无前缀时,继承同目录 generated 原稿编号。"""
    m = re.match(r"(\d{2}) ", os.path.basename(inside))
    if m:
        return int(m.group(1))

    siblings = []
    try:
        for name in os.listdir(os.path.dirname(path)):
            match = re.match(r"(\d{2}) .+\.md$", name)
            if match:
                siblings.append(int(match.group(1)))
    except OSError:
        return None
    unique = sorted(set(siblings))
    return unique[0] if len(unique) == 1 else None


def ladder_of(path):
    """从阶梯根、概念目录与编号原稿得到公开阅读坐标。"""
    registration = _ladder_registration(path)
    if not registration:
        return None
    _root, lad, inside = registration
    n = _rung_number(path, inside)
    if n is None or n not in lad["slugs"]:
        return None
    parts = inside.split("/")
    concept = parts[0] if len(parts) > 1 else None
    for zh, en, (lo, hi) in lad["modules"]:
        if lo <= n <= hi:
            return {
                "order": n,
                "slug": lad["slugs"][n],
                "module": zh,
                "module_en": en,
                "series": lad["series"],
                "category": lad["category"],
                "concept": concept,
            }
    return None


def created_exempt(path):
    """按绝对路径的**路径段**判,不按 rel(),也不按前缀。

    两个坑都踩过:
    - rel() 是相对 OBSIDIAN_VAULT 的。把 vault 直接指到 `Ideas/2025` 时,
      rel() 不会以 `Ideas/2025/` 开头,按 rel 判会静默失效。
    - 按 `Ideas/2025/` 做子串匹配也不行:Cowork 桌面工作区把它挂成
      `mnt/2025/`,`Ideas` 那一段根本不在路径里。
    """
    segs = os.path.abspath(path).replace(os.sep, "/").split("/")
    return any(pfx in segs for pfx in CREATED_EXEMPT)


def publish_denied(path):
    """这条笔记是否禁止进入上站路径。"""
    r = rel(path)
    return any(r == d or r.startswith(d + "/") for d in PUBLISH_DENY)


# ================================================================== 发现

def notes():
    out = []
    for root, dirs, files in os.walk(VAULT):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for f in sorted(files):
            if f.endswith(".md"):
                out.append(os.path.join(root, f))
    return sorted(out)


def assets():
    """vault 里的非 .md 文件(图片、PDF 等)。

    用于校验 `![[...]]` 嵌入是否落空 —— 这类目标本来就不在 `stems` 里,
    旧版把它们一律当断链报出来。2026 vault 一张图都没嵌,所以这个 bug 从未显形。
    统一按 NFC 归一:macOS 落盘的文件名是 NFD。
    """
    out = set()
    for root, dirs, files in os.walk(VAULT):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for f in files:
            if not f.endswith(".md"):
                out.add(unicodedata.normalize("NFC", f))
    return out


def _unquote(v):
    v = v.strip()
    if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'":
        return v[1:-1]
    return v


def parse_frontmatter(head):
    """list-aware 的 frontmatter 解析。

    旧版是行式的(`if ":" in line` 然后 partition),遇到 YAML 块列表:

        field:
          - type-systems/error-handling

    会把 `field` 解析成空字符串,列表项因为不含 `:` 被整行丢弃 —— 新地形模型里
    信息量最大的两个字段一条都进不了管道。这里按「键行 / 列表项行」两种形态解析,
    值为空且后随 `- ` 行的键收成列表。

    只支持 vault 实际用到的子集:标量、块列表、内联列表。不做嵌套。
    """
    fm, key = {}, None
    for raw in head.split("\n"):
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        m = re.match(r"^([A-Za-z_][\w-]*):\s*(.*)$", raw)
        if m:
            key, val = m.group(1), m.group(2).strip()
            if val == "":
                fm[key] = []            # 可能是块列表,等 `- ` 行来填
            elif val.startswith("[") and val.endswith("]"):
                inner = val[1:-1].strip()
                fm[key] = [_unquote(x) for x in inner.split(",") if x.strip()] if inner else []
                key = None
            else:
                fm[key] = _unquote(val)
                key = None              # 标量写完就不再接收 `- ` 行
            continue
        m = re.match(r"^\s*-\s+(.*)$", raw)
        if m and key is not None:
            if not isinstance(fm.get(key), list):
                fm[key] = []
            fm[key].append(_unquote(m.group(1)))
    return fm


def parse(path):
    with open(path, encoding="utf-8") as handle:
        raw = handle.read()
    fm, body = {}, raw
    if raw.startswith("---\n"):
        head, _, rest = raw[4:].partition("\n---\n")
        body = rest
        fm = parse_frontmatter(head)
    return fm, body, hashlib.sha256(raw.encode()).hexdigest()[:16]


def load_manifest():
    try:
        return json.load(open(MANIFEST, encoding="utf-8"))
    except (FileNotFoundError, ValueError):
        return {}


# =================================================== 方言转换的公共工具

FENCE = re.compile(r"```.*?```", re.S)


def _protect(text):
    """把围栏代码块和行内代码换成占位符,避免被转义规则误伤。"""
    store = []

    def keep(m):
        store.append(m.group(0))
        return f"\x00{len(store) - 1}\x00"

    text = FENCE.sub(keep, text)
    text = re.sub(r"`[^`\n]+`", keep, text)
    return text, store


def _protect_xml(text):
    """保护本脚本自己生成的 XML 标签,免得下一步的转义把它们变成字面量。"""
    store = []

    def keep(m):
        store.append(m.group(0))
        return f"\x01{len(store) - 1}\x01"

    return re.sub(r"</?(?:table|tr|td|colgroup|col|callout|br)[^>]*/?>", keep, text), store


def _restore(text, store, mark="\x00"):
    return re.sub(mark + r"(\d+)" + mark, lambda m: store[int(m.group(1))], text)


def strip_wikilinks(text, link=lambda target, label: f"**{label}**"):
    text = re.sub(r"\[\[([^\]|#]+)(?:#[^\]|]*)?\|([^\]]+)\]\]", lambda m: link(m.group(1), m.group(2)), text)
    text = re.sub(r"\[\[([^\]|#]+)(?:#([^\]|]*))?\]\]", lambda m: link(m.group(1), m.group(2) or m.group(1)), text)
    return text


def pipe_tables_to_xml(body):
    """标准 markdown 管道表 → Notion 的 <table> XML。Notion 不认管道表。"""
    lines = body.split("\n")
    out, i = [], 0
    while i < len(lines):
        if (
            lines[i].strip().startswith("|")
            and i + 1 < len(lines)
            and re.fullmatch(r"\s*\|[\s:\-|]+\|\s*", lines[i + 1])
        ):
            rows = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                if not re.fullmatch(r"\s*\|[\s:\-|]+\|\s*", lines[i]):
                    rows.append([c.strip() for c in lines[i].strip().strip("|").split("|")])
                i += 1
            out.append('<table header-row="true">')
            for r in rows:
                out.append("\t<tr>")
                for c in r:
                    out.append(f"\t\t<td>{c}</td>")
                out.append("\t</tr>")
            out.append("</table>")
            continue
        out.append(lines[i])
        i += 1
    return "\n".join(out)


def fold_quotes(body):
    """连续的 `> ` 行 → 一个多行 quote(Notion 用 <br>,不用换行)。"""
    lines, out, buf = body.split("\n"), [], []

    def flush():
        if buf:
            out.append("> " + "<br>".join(buf))
            buf.clear()

    for ln in lines:
        if ln.startswith(">"):
            buf.append(ln.lstrip(">").strip())
        else:
            flush()
            out.append(ln)
    flush()
    return "\n".join(out)


def escape_for_notion(text):
    """Notion 要求转义的结构字符,只在正文(非代码)里做。
    行首的 `>` 是引用标记,不能转义 —— 转了就变成字面量。"""
    out = []
    for ln in text.split("\n"):
        head, rest = "", ln
        m = re.match(r"^(\s*>\s?)(.*)$", ln)
        if m:
            head, rest = m.group(1), m.group(2)
        for ch in ["<", ">", "{", "}", "|", "^"]:
            rest = rest.replace(ch, "\\" + ch)
        out.append(head + rest)
    return "\n".join(out)


# =============================================================== Notion

def _meta_lines(fm):
    """地形元数据 → callout 里的几行。

    只输出真的有值的字段 —— 旧版无条件写一行 `tags: `,而 tags 因为解析器丢了
    列表永远是空的,于是每一页备份顶上都挂着一行空标签。
    """
    scal = [f"{k}: {fm[k]}" for k in SCALAR_META if isinstance(fm.get(k), str) and fm[k]]
    lines = []
    if scal:
        lines.append("备份自 Obsidian · " + " · ".join(scal))
    else:
        lines.append("备份自 Obsidian")
    for k in LIST_META:
        v = fm.get(k)
        if isinstance(v, list) and v:
            lines.append(f"{k}: " + " · ".join(v))
        elif isinstance(v, str) and v:
            lines.append(f"{k}: {v}")
    return lines


def to_notion(path):
    """顺序很讲究:先做需要原始 `|` 的表格,再保护已生成的 XML,最后才转义。
    颠倒任何一步都会把表格或引用块转义坏。"""
    fm, body, _ = parse(path)
    body = strip_wikilinks(body, lambda t, l: f"**{l}**")
    body = re.sub(r"^#\s+.*\n", "", body, count=1, flags=re.M)   # 标题走 properties
    body = pipe_tables_to_xml(body)                      # 1) 此时 | 还有意义
    body, code = _protect(body)                          # 2) 护住代码
    body, xml = _protect_xml(body)                       # 3) 护住刚生成的 <table> 标签
    body = escape_for_notion(body)                       # 4) 只转义正文里的结构字符
    body = fold_quotes(body)                             # 5) 之后才产生 `> ` 标记
    body = re.sub(r"(?<!\$)\$([^$\n]+)\$(?!\$)", lambda m: "$`" + m.group(1) + "`$", body)
    body = _restore(_restore(body, xml, "\x01"), code, "\x00")

    head = '<callout icon="🗂️" color="gray_bg">\n'
    head += "".join("\t" + ln + "\n" for ln in _meta_lines(fm))
    head += "</callout>\n\n"
    return head + body.strip() + "\n"


# ================================================================= 博客

# 上站时要砍掉的尾部小节。**只是不发,不是不该存在** —— 这两件事必须分开:
#
# 「相关」是指向 vault 内其他笔记的 wikilink,站上根本解析不了。
#
# 「开放问题」在 vault 里是正当且被认可的结构:那 3–5 问是留着以后在别的学科里
# 再撞见的,答案不在本篇。正因为答案不在本篇,放上站就成了一篇答不上来的文章 ——
# 所以裁掉是**发布侧的取舍**,与源文的正确性无关。
#
# (MOC 那句「课程笔记不自动生成开放问题」约束的是 AI 往后怎么写新笔记,
#  不是要求清掉已有的。别再把它读成删除指令。)
TAIL_SECTIONS = ("开放问题", "开放性问题", "提问", "相关", "相关笔记", "相关文章")


def cut_tail_sections(body):
    """从第一个尾部小节的标题处截断。要绕开围栏代码,否则代码里的
    `## 相关` 注释会把正文腰斩。返回 (正文, 被砍掉的小节名或 None)。"""
    lines = body.split("\n")
    in_fence = False
    for i, ln in enumerate(lines):
        if ln.lstrip().startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        m = re.match(r"^#{2,3}\s+(.+?)\s*$", ln)
        if m:
            name = m.group(1).strip().strip("·、 ")
            if name in TAIL_SECTIONS:
                return "\n".join(lines[:i]).rstrip() + "\n", name
    return body, None


def to_post(path, category=None, draft=True):
    if publish_denied(path):
        raise SystemExit(
            f"✋ 拒绝上站:{rel(path)}\n"
            "   Holzwege / Questioning 保存的是尚未证实的候选路径。vault 规范:\n"
            "   「类比不能冒充等价;路径失败也保留为地形证据」。发布是一次断言。"
        )
    fm, body, _ = parse(path)
    body, _cut = cut_tail_sections(body)
    m = re.search(r"^#\s+(.*)$", body, re.M)
    title = m.group(1).strip() if m else os.path.basename(path)[:-3]
    # H1 **留在正文里**。这个主题的文章模板不渲染 frontmatter 的 title
    # (src/pages/posts/[...id].astro 只把它给 SEO),旧的 day-* 文章也都是
    # 自己在正文写 H1。剥掉就等于整篇没有标题。
    body = strip_wikilinks(body, lambda t, l: f"**{l}**")

    # description 取「定位句」:紧跟标题的那条 quote,或第一段正文。
    # 不能无脑取第一条 quote —— 那往往是文中的「抽象断裂点」,不是摘要。
    desc = ""
    in_fence = False
    for ln in body.strip().split("\n"):
        t = ln.strip()
        if t.startswith("```"):          # 围栏代码不是摘要 —— 不跳过会取到 "rust"
            in_fence = not in_fence
            continue
        if in_fence or not t:
            continue
        # 只跳列表项与表格,不能跳 `**` 开头的段落 —— 那往往正是定位句
        if t.startswith(("#", "|", "<table", "- ", "* ", "1. ")):
            continue
        if t.startswith(">"):
            t = t.lstrip("> ").strip()
        if t.startswith("**抽象断裂点"):
            desc = ""
            break
        desc = re.sub(r"[*`]", "", t).replace('"', "'").strip()
        break
    # 兜底用标题。旧版兜底是 `fm['course'] · 文件名`,而 course 已废除,那行
    # 只会产出一个前导的孤零零 " · "。地形元数据(field/tags)是内部导航词汇,
    # 按用户决定不上站,更不该漏进 description。
    if not desc:
        desc = title

    lad = ladder_of(path)
    out = [
        "---",
        f'title: "{title.replace(chr(34), chr(39))}"',
        f'pubDate: "{fm.get("created", "")}"',
        'author: "Roddy"',
        f'description: "{desc[:180]}"',
        f"categories: ['{category or (lad or {}).get('category', 'notes')}']",
    ]
    if lad:
        # Archive 消费这些公开投影坐标。type / field / tags 仍然只属于 vault;
        # layer 例外,因为 Archive 必须区分学习前脚手架与亲历后坐标。
        out += [
            f"series: '{lad['series']}'",
            f"order: {lad['order']}",
            f"module: \"{lad['module']}\"",
        ]
        if lad.get("concept"):
            out.append(f"concept: \"{lad['concept'].replace(chr(34), chr(39))}\"")
    layer = fm.get("layer")
    if layer in LEARNING_LAYERS:
        out.append(f"layer: '{layer}'")
    version = re.search(r"_v(\d+)$", os.path.splitext(os.path.basename(path))[0], re.I)
    if version:
        out.append(f"revision: {int(version.group(1))}")
    out += [
        f"draft: {'true' if draft else 'false'}",
        "---",
        "",
        body.strip(),
        "",
    ]
    return "\n".join(out)


def post_slug(path):
    lad = ladder_of(path)
    if not lad:
        return None
    fm, _body, _hash = parse(path)
    if fm.get("layer") != "the real":
        return lad["slug"]
    stem = os.path.splitext(os.path.basename(path))[0].lower()
    suffix = re.sub(r"[^a-z0-9]+", "-", stem).strip("-")
    version = re.search(r"_v(\d+)$", stem, re.I)
    if not suffix:
        suffix = f"v{version.group(1)}" if version else "the-real"
    return f"{lad['slug']}/{suffix}"


# ================================================================ doctor

def doctor(only=None):
    """按 vault 现行规范体检。只报告,不修改 —— 源头永远由人改。

    only: 相对 vault 的路径前缀,只过滤**报告范围**。stems 与 assets 仍扫全 vault ——
    否则「只想体检一个子目录」就得把 OBSIDIAN_VAULT 指过去,stems 随之缩水,
    凭空造出断链告警(实测五个子目录合计 74 条 vs 全 vault 口径下的 50 条)。
    """
    stems = {unicodedata.normalize("NFC", os.path.basename(p)[:-3]) for p in notes()}
    files = assets()
    targets = [p for p in notes() if only is None or rel(p).startswith(only)]
    problems = 0
    notes_only = []   # 参考信息,不算问题
    for p in targets:
        fm, body, _ = parse(p)
        r = rel(p)
        msgs = []
        # 扫正文前先摘掉代码。numpy 的数组输出 `[[1, 2, 3]]`、Rust 的
        # `Vec<Vec<T>>`,以及代码注释里的 `## 相关`,都会被下面的规则误判。
        # 这和 cut_tail_sections 绕开围栏是同一个理由。
        scan, _code = _protect(body)

        t = fm.get("type", "")
        if not t:
            msgs.append("缺 type")
        elif t not in NOTE_TYPES and t not in INFRA_TYPES:
            msgs.append(
                f"type 不在枚举内:{t}"
                "(应为 lecture / vibelearn / knot / tool / uber / moc)"
            )

        layer = fm.get("layer")
        if layer and layer not in LEARNING_LAYERS:
            msgs.append(f"layer 不在枚举内:{layer}(应为 generated / the real)")

        for k in RETIRED_KEYS:
            if k in fm:
                msgs.append(f"残留已废除的字段 `{k}` —— 课程归属由目录与 MOC 保存")

        if not fm.get("created") and not created_exempt(p):
            msgs.append("缺 created")
        for k in ("field", "tags"):
            if not fm.get(k):
                msgs.append(f"缺 {k}")

        if t == "knot" and not fm.get("origin"):
            msgs.append("knot 缺 origin(要记录触发来源)")
        if t in ("lecture", "vibelearn") and not fm.get("horizon"):
            msgs.append("缺 horizon(lecture / vibelearn 要记录兑现时间尺度)")

        for k in ("field", "tags"):
            v = fm.get(k)
            if isinstance(v, str) and v:
                msgs.append(f"{k} 写成了标量,应为 YAML 列表")

        # tags 是「动作—对象」路线,不是名词标签
        stem = os.path.basename(r)[:-3]
        for tag in fm.get("tags", []) if isinstance(fm.get("tags"), list) else []:
            if tag in RETIRED_TAGS:
                # 先判废除,再判形状 —— 否则一个废除标签会同时挨两条报错
                msgs.append(f"残留已废除的标签 `{tag}`")
                continue
            if not tag.isascii():
                # 用户 2026-08-29 定:tags 一律英文。field 与正文照旧用中文 ——
                # tags 是**受控词表**,要跨语言稳定、可被脚本对齐,中文名词进来
                # 就会和 field 混成一团。
                msgs.append(f"tags `{tag}` 含非 ASCII 字符:tag 一律用英文")
            elif "-" not in tag:
                msgs.append(f"tags `{tag}` 不像「动作—对象」路线(如 trace-expression-evaluation)")
            # 工具 tag 必须真的调用了那个工具。这条把 tags 从形容词变成
            # **可验证的调用记录** —— 打了 `estimate-termwise` 的笔记,正文里
            # 就得有 [[逐项估计]]。例外:工具笔记自己不必自链。
            note = TOOLS.get(tag)
            if note and note != stem and f"[[{note}" not in scan:
                msgs.append(f"tags `{tag}` 无对应双链:正文里没有 [[{note}]]")

        # 工具笔记必须在词表里注册,否则 slug 是私设的,别人打不出这个 tag
        if t == "tool" and TOOLS and stem not in TOOLS.values():
            msgs.append(f"type: tool 但未登记进 TOOLS 词表:{stem}")

        if ":" in os.path.basename(r):
            msgs.append("文件名含半角冒号(macOS Finder 会显示成斜杠)")

        # 文末「开放问题」**不是缺陷**,不在这里报。它在 vault 里是正当结构;
        # 上站时裁掉是发布侧的取舍,见 TAIL_SECTIONS 的注释。

        # 抽象断裂点只作为**参考数字**打印,不计入问题数。MOC 写的是「一篇 1–3 处,
        # 不铺满」,但那是写作时的自我提醒,不是可以由脚本判定的硬约束 ——
        # 判断一处断裂点该不该在,只有写的人知道。
        # 工具的失效边界。**写在正文末尾的小节里,不写进 frontmatter**
        # (用户 2026-08-29 决定):边界是内容不是元数据,而且 frontmatter 里的
        # 双链在 Obsidian 的图谱里未必算数,放正文才一定连得上。
        # 约定:小节标题以「边界」开头。
        #
        # 只作参考、不计入问题数,理由同「抽象断裂点」—— 2025 的 55 篇里迁移前
        # 只有 2 篇写过独立边界小节,做成硬错等于 doctor 永远红着。
        if t == "tool" and not re.search(r"^#{2,}\s*边界", scan, re.M):
            notes_only.append(f"{r}:tool 未写「边界」小节(失效条件)")

        if t in ("lecture", "vibelearn"):
            n = scan.count("抽象断裂点")
            if n == 0 or n > 3:
                notes_only.append(f"{r}:抽象断裂点 {n} 处(MOC 参考值 1–3)")

        # 双链与嵌入。两个坑:
        #   ① `![[图.png]]` 是**嵌入**不是双链,目标在附件里而不在 stems 里;
        #   ② macOS 落盘的文件名是 NFD,正文里写的是 NFC(`Alberto Calderón`),
        #      不归一就会把明明存在的笔记报成断链。
        # 顺序必须是「先查 stems,再按扩展名分流」—— 反过来会把 `Nof1.AI`、
        # `11.1 多巴胺分布和日常作息` 这种 stem 自带点号的笔记永久判成附件。
        for m in re.finditer(r"(!?)\[\[([^\]|#]+)", scan):
            tgt = unicodedata.normalize("NFC", m.group(2).strip())
            if tgt in stems:
                continue
            if m.group(1) or os.path.splitext(tgt)[1]:
                if tgt not in files:
                    msgs.append(f"附件不存在:[[{tgt}]]")
                continue
            msgs.append(f"双链无法解析:[[{tgt}]]")

        if msgs:
            problems += 1
            print(f"\n■ {r}")
            for m in dict.fromkeys(msgs):
                print(f"    · {m}")
    total = len(targets)
    if notes_only:
        print("\n参考(不算问题):")
        for n in notes_only:
            print(f"    · {n}")
    print(f"\n--- 体检完毕:{total} 篇,{problems} 篇有问题,{total - problems} 篇干净 ---")
    return 1 if problems else 0


# =================================================================== CLI

def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "list":
        for p in notes():
            print(rel(p))
    elif cmd == "changed":
        man, n = load_manifest(), 0
        for p in notes():
            r = rel(p)
            _, _, h = parse(p)
            if man.get(r) != h:
                print(("NEW    " if r not in man else "CHANGED") + "  " + r)
                n += 1
        print(f"--- {n} 条待同步 ---", file=sys.stderr)
    elif cmd == "commit":
        man = {}
        for p in notes():
            _, _, h = parse(p)
            man[rel(p)] = h
        os.makedirs(os.path.dirname(MANIFEST), exist_ok=True)
        json.dump(man, open(MANIFEST, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print(f"✓ manifest 已更新:{len(man)} 条")
    elif cmd == "doctor":
        only = None
        if "--only" in sys.argv:
            i = sys.argv.index("--only")
            only = sys.argv[i + 1] if len(sys.argv) > i + 1 else None
            if not only:
                raise SystemExit("--only 需要一个相对 vault 的路径前缀")
        raise SystemExit(doctor(only))
    elif cmd == "notion":
        sys.stdout.write(to_notion(sys.argv[2]))
    elif cmd == "post":
        sys.stdout.write(to_post(sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else None))
    elif cmd == "ladder":
        for d, lad in LADDERS.items():
            print(f"# {d}  (series={lad['series']})")
            for p in notes():
                l = ladder_of(p)
                if l and rel(p).startswith(d + "/"):
                    print(
                        f"{l['order']:02d}\t{l['module']}\t{post_slug(p)}\t"
                        f"{os.path.basename(p)[:-3]}"
                    )
    elif cmd == "build-posts":
        publish = "--publish" in sys.argv[2:]
        positional = [arg for arg in sys.argv[2:] if not arg.startswith("--")]
        dest_arg = positional[0] if positional else None
        n = 0
        outputs = {}
        for p in notes():
            lad = ladder_of(p)
            if not lad or publish_denied(p):
                continue
            dest = dest_arg or os.path.join("src/content/posts", lad["series"])
            slug = post_slug(p)
            target = os.path.join(dest, slug + ".md")
            if target in outputs:
                raise SystemExit(
                    f"输出冲突:{rel(p)} 与 {outputs[target]} 都映射到 {target}"
                )
            outputs[target] = rel(p)
            os.makedirs(os.path.dirname(target), exist_ok=True)
            with open(target, "w", encoding="utf-8") as handle:
                handle.write(to_post(p, draft=not publish))
            n += 1
        state = "发布" if publish else "草稿"
        print(f"✓ 已生成 {n} 篇阶梯文章({state})")
    else:
        raise SystemExit(
            "用法: list | changed | doctor [--only PREFIX] | commit | notion <path> | post <path> [category] "
            "| ladder | build-posts [dest] [--publish]"
        )


if __name__ == "__main__":
    main()
