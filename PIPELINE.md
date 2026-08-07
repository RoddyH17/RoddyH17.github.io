# 每日学习管道 · 架构说明

> 这份文档说的是**为什么**存在这条管道,以及它由哪几层构成。
> 「博客怎么用」在 [README.md](./README.md),「Rust 怎么学」在 [rust_learn](https://github.com/RoddyH17/rust_learn)。

---

## 1. 为什么存在

这条管道不是为了「把笔记同步到三个地方」。同步只是副产品。真正的目标有两个:

**① 让 AI 拥有一套关于「我在学什么」的记忆系统。**
AI 需要知道我每天在学什么、卡在哪、想通了什么,才能在后续对话里接得上,而不是每次
从零问起。散落在 Notion 里的原始笔记做不到这件事——它没有结构,没有时间轴,也没有
「这一天到底完成了没有」的判定。

**② 让每天的知识变成可再利用的素材。**
现在有大量 AI 视频/内容工具。我希望能灵活调用自己每天的动态,并且**直接从博客就能
看出当天的亮点与特色**。

> 例:今天学了 Rust 的 Ownership。这套抽象范式能不能映射到生活里的例子,做成一个
> 更好懂的 exemplify?「所有权只能有一个持有者,转移之后原持有者失效」——这跟房产
> 过户、跟借书证、跟接力棒有什么异同?
>
> 这类玩法还有很多,但前提是**每天的材料必须以机器能直接消费的形态存在**。

所以有一条贯穿全文的原则:

> **这条管道的产物,首要读者是 AI,其次才是人。**

人读的部分(博客正文)已经有了。缺的是 AI 读的部分——这就是下面 L4 那一层。

---

## 2. 四层架构

```mermaid
flowchart TD
    V["📹 视频学习"]

    subgraph L1["L1 · 源头 —— 他现场写"]
        M["rust_learn/dayN/&lt;crate&gt;/src/main.rs<br/>注释即笔记,代码即还原<br/>一边记录一边编译"]
    end

    subgraph L2["L2 · 训练"]
        P["examples/practice.rs<br/>Claude 读 main.rs 生成,他做"]
    end

    subgraph L3["L3 · 归档中介"]
        N["Notion System III / DayN<br/>可分享、手机可读<br/>不再是权威"]
    end

    subgraph L4["L4 · 叙事与记忆"]
        NO["dayN/NOTES.md"]
        B["blog/day-N-*.mdx → 网站"]
        ME["Claude 的记忆"]
    end

    V --> M
    M -->|"读 main.rs"| P
    M -->|"notion.sh render + MCP 写入"| N
    M --> NO
    M --> B
    M --> ME

    style L1 fill:#3d3020,stroke:#8b6914,color:#e2e8f0
    style L2 fill:#2d3748,stroke:#4a5568,color:#e2e8f0
    style L3 fill:#2d3748,stroke:#4a5568,color:#e2e8f0
    style L4 fill:#2d3748,stroke:#4a5568,color:#e2e8f0
```

| 层                                | 是什么                                                                               | 谁写               | 状态    |
| --------------------------------- | ------------------------------------------------------------------------------------ | ------------------ | ------- |
| **L1** `dayN/<crate>/src/main.rs` | **唯一源头**。看视频时现场写:注释是笔记,代码是对老师内容的还原,随时 `cargo run` 验证 | **Roddy**          | ✅ 在用 |
| **L2** `examples/practice.rs`     | 课后训练。Claude 读完 L1 生成题目                                                    | Claude 生成 / 他做 | ✅ 在用 |
| **L3** Notion System III / DayN   | **归档中介**:可分享、手机可读、长期沉淀。**不再是信息源**                            | Claude 推送        | ✅ 在用 |
| **L4** `NOTES.md` / 博客 / 记忆   | 叙事与再利用                                                                         | Claude 生成        | ✅ 在用 |

### 2026-08-07:Notion 从信息源降级为中介

原架构是 **Notion → rust_learn / blog**,Notion 是 source of truth。Roddy 重新定义了它:

> 「所以现在我重新思考了一下 notion 的位置,它并非作为信息源,而是信息中介和数据管道。」

**方向整个反了。** 现在的源头是他在 VSCode 里现场敲的那个 `main.rs` —— 因为学习本身
就发生在那里:看视频、记笔记、把老师的代码敲出来跑通,是同一个动作。让这个动作的产物
直接当源头,中间就没有任何一步会丢东西。

Notion 仍然重要 —— 它是可分享、手机上能翻、能长期沉淀的那一份。但它现在**从 L1 生成**,
而不是反过来。

### 三层现在共用一条切分轴:天

**2026-08-06 起,Notion 也按天切**——Roddy 把 Day 1/2/3 拆成了 System III 下的三个
子页面。三层从此同构,`audit` 之所以能做,就是因为三边可以逐天对齐。

原先 L1 是按主题(章/节)切的,理由写在
[`src/content.config.ts`](./src/content.config.ts) 里(research 集合那段注释):

> posts 是时间流、是写完就定稿的;research notes 是一个会被反复修订几个月的矩阵。

按那个分类,System III 更像后者,所以本文档原先建议**不要**按天拆。改了之后换来的是
一个明显更结实的 join key(见下一节),这笔交易是划算的。

**但代价要记在这里,免得以后忘**:到第 60 天,「借用规则怎么写来着」会变成
「那是第几天学的来着」。等日页多到查不动时,解法是在父页维护一份**主题索引**
(概念 → 哪一天),而不是把日页再拆回主题结构。

---

## 3. 日号由 `dayN/` 目录决定

源头是文件系统:`rust_learn/day4/` 存在,Day 4 就存在。Notion 的 `Day4: …` 子页是它的
投影,不是它的定义。

### 契约

1. **`dayN/` 目录名就是日号。** `audit` 枚举 `rust_learn/day*/` 来决定要查哪几天。
2. **一天一个 crate**:`dayN/<topic>/`,`src/main.rs` 是现场记录,
   `examples/practice.rs` 是训练。`new_day.sh` 一条命令建好,含 `.vscode/launch.json`。
3. **现场记录的结构约定**(`render` 靠它解析):
   - `//!` 开头的模块文档 → 当天导语(Markdown,rust-analyzer 悬停可渲染)
   - `// ---------- N. 标题 ----------` → 一个小节
   - 小节里,**第一行代码之前**的整行注释算散文,之后的全部算代码(含行内注释)——
     因为代码前的注释通常是「老师说 / 我的理解」,穿插在代码里的是在解释那几行本身
4. **日号只在章内唯一。** 开 Chapter 2 时会重新从 Day 1 开始,真正的标识是 (章, 日)。
   命令行写 `day 2.3`;第 1 章可省略。**跨章的目录约定尚未决定** —— `audit` 遇到第 2 章
   会直接报「尚无目录约定」,不替人发明。

### 往 Notion 里写什么 —— 两条硬规则

**① 不放练习。** 练习在 `practice.rs` 里做,Notion 再放一份就是重复。往 Notion 放的是:
解释、中英文对照解释、细致知识点、对笔记的总结。🌟 分级同理,只属于 `practice.rs`。

**② 一个大标题,底下逐条列重点。** 不要 `###` / `####` 堆成多层树 —— 用加粗编号引导句

- 代码 + 表格把要点一条条列出来。

中英文分工:**英文承载 The Rust Book 的参考文本,中文承载他自己的理解。** 原样保留,
`render` 不翻译不改写。

### 读和写走两条不同的路

| 方向             | 用什么                                                      | 为什么                               |
| ---------------- | ----------------------------------------------------------- | ------------------------------------ |
| **读**(回读校验) | `scripts/notion.sh fetch` + `.env` 里的只读 token           | 不进上下文,成本固定                  |
| **写**(推送内容) | `notion.sh render <N>` 渲染 → MCP `notion-update-page` 写入 | 脚本那个 integration **只读,写不了** |

`render` 负责把 `main.rs` 变成符合上面两条硬规则的 markdown 并校验;实际写入必须走 MCP。

## 4. 一天的生命周期

```mermaid
sequenceDiagram
    participant R as Roddy
    participant M as dayN/src/main.rs
    participant C as Claude
    participant N as Notion DayN
    participant B as blog / 网站

    Note over R: new_day.sh N topic<br/>(建目录 + 现场记录骨架 + launch.json)
    R->>M: 看视频,边记边敲<br/>注释即笔记,代码即还原
    Note over M: cargo run 随时验证 —— 记录和还原是同一个动作

    M-->>C: Claude 读 main.rs
    C->>M: 生成 examples/practice.rs
    Note over R: 做课后训练<br/>cargo run --example practice

    C->>N: notion.sh render N → MCP 写入
    C->>B: 生成 NOTES.md + 博客草稿
    Note over C: 吸收进记忆
    R->>B: 删掉 draft: true → sync.sh → 上线
```

**为什么源头是 `main.rs` 而不是别的:** 学习这件事本身就发生在编辑器里 —— 看视频、
记笔记、把老师的代码敲出来跑通,是同一个动作。让这个动作的产物直接当源头,中间就没有
任何一步会丢东西。以前 Notion 当源头时,漏的永远是「记在 Notion 里但没流到下游」那一段。

## 5. 「一天算完成」的定义

以 `dayN` 的现场记录为参照,五项齐全才算完成:

| 检查项       | 判据                                                                                        |
| ------------ | ------------------------------------------------------------------------------------------- |
| **main.rs**  | 编号节都写了内容,且 `cargo run` 通过                                                        |
| **practice** | `examples/practice.rs` 有真题目(不是 TODO 骨架),`cargo run --example practice` **原样通过** |
| **Notion**   | System III 下有对应的 DayN 页,内容与 `render` 输出一致                                      |
| **NOTES.md** | `dayN/NOTES.md` 写完(Goals 表学前填,其余学后填)                                             |
| **blog**     | `src/content/posts/rust/day-N-*.mdx` 存在且已发布(无 `draft: true`)                         |

跑 `./scripts/notion.sh audit` 得到这张表 —— **不要手抄,它会过期**。

`audit` 的三条硬规则:

- **查文件系统,不查 git。**「存在但未提交」和「不存在」是两种状态,分开报。
- **不做假的覆盖率。** 源头与 Notion 的标题不同源,做相似度匹配只会给出虚假的精确感。
  并排列出两边小节,标「需人工判断」,不出百分比。
- **真的编译。** `main.rs` 和 `practice.rs` 都跑 `cargo build`,不只查文件存在 ——
  这是「原样可编译」那条铁律唯一可靠的检查方式。

## 6. L4 · 再利用层(🚧 提案,未实现)

前三层都是「存放」。第四层是「抽取」——它要回答的问题是:

> **每天除了笔记和文章,还应该额外产出什么,才能让 AI 直接消费?**

### 形状:博客文章 frontmatter 上的再利用钩子

```yaml
---
title: Day 3 · Ownership — 谁负责释放这块内存
pubDate: 2026-08-06
categories: [rust]
mood: [sorge, frage]

# ── L4 再利用钩子 ──────────────────────────────
# 当天的核心抽象。AI 用它判断"这天讲了什么"
concepts: [ownership, move, borrow, NLL, dangling-reference]

# 一句话说清当天最反直觉的点 —— 视频/类比生成的种子
hook: '把一个变量赋值给另一个,原变量当场失效 —— 赋值是转移,不是拷贝'

# 已经想到的生活类比。可以留空,由 AI 补
analogies:
  - '房产证只能有一个持有人;过户之后,原持有人不再有权处置那套房'
  - '借出去的书:借阅期间你不能再借给第二个人,也不能把书卖掉'
---
```

### 为什么放 frontmatter,而不是单独的 index.json

沿用 research 集合已经确立的模式(见 `src/content.config.ts` 里 `sources[]` /
`deepwiki[]` 那段注释):**出处放 frontmatter,正文改了也不脱节。**

具体到这里:

- 博客本来就要按天写。钩子跟着文章走,**一次编辑同时喂人和喂 AI**
- 不产生第二个需要同步的地方——多一个 index.json 就多一处会漂移的真相
- Astro 的 `getCollection('posts')` 一次调用就能拿到全部钩子,渲染和消费都免费

### 这一层解锁什么

| 能力                           | 靠哪个字段                           |
| ------------------------------ | ------------------------------------ |
| AI 知道我这周学了什么          | `concepts` 按天聚合                  |
| 「今天这个概念,能类比成什么」  | `hook` 当种子,`analogies` 当已有积累 |
| 生成短视频脚本 / 讲解稿        | `hook` + 正文 + `practice.rs` 的题目 |
| 博客上直接看出当天亮点         | `hook` 渲染成文章卡片的副标题        |
| 找出「学过但从没复用过」的概念 | `concepts` 出现过但 `analogies` 为空 |

> **状态:提案。** 本文档只立靶心,`src/content.config.ts` 尚未改动,现有文章也还
> 没有这些字段。

---

## 7. 脚本清单

### rust_learn(`~/rust_learn`)—— 源头这一侧

| 脚本                                   | 职责                                                                                                                |
| -------------------------------------- | ------------------------------------------------------------------------------------------------------------------- |
| `new_day.sh <N> [topic] [slug] [date]` | 建 `dayN/` + cargo 项目 + **现场记录骨架** + practice 骨架 + NOTES.md,并自动写入 `.vscode/launch.json` 两条调试配置 |
| `sync.sh ["msg"]`                      | commit + push                                                                                                       |

`new_day.sh` 产出的 `src/main.rs` 不是 cargo 默认的 hello world,而是带 `//!` 头
(日期 / 主题 / 待填主线)和编号空节的骨架,**打开就能往里写,而且原样可编译**。

### blog(`~/blog`)—— 生成这一侧

| 脚本                               | 职责                                                                           |
| ---------------------------------- | ------------------------------------------------------------------------------ |
| `scripts/notion.sh`                | `list` / `fetch` / `day` / `diff`(读) · `render`(渲染待推内容) · `audit`(对账) |
| `scripts/notion_sync.py`           | 上者的实现:Notion REST 拉取、block→markdown、现场记录解析、对账。仅标准库      |
| `scripts/deepwiki.sh`              | DeepWiki 检索层(research 管道用)                                               |
| `new_post.sh <类别> <slug> [标题]` | 新建博客草稿(`.mdx`,默认 `draft: true`)                                        |
| `new_research.sh`                  | 新建协议研究笔记                                                               |
| `sync.sh ["msg"]`                  | commit + push,触发 GitHub Actions 部署                                         |

```bash
./scripts/notion.sh render 4     # dayN 现场记录 → 待推 Notion 的 markdown
./scripts/notion.sh audit        # 五层对账,以 dayN 为参照
./scripts/notion.sh audit 4      # 只看某一天
```

缓存在 `.cache/notion/`(已 gitignore),每页一份 `.md` / `.json` / `.prev.md`,
外加 `meta.json`。页面改名会换 slug,`fetch` 自动清理孤儿文件。

### 一条贯穿的原则:检索层不是结论层

这句话写在 `scripts/deepwiki.sh` 顶部,对整条管道同样成立:

> DeepWiki 是检索层,不是结论层。它答出来的东西必须回原始源码核对再写进笔记。

对应到这里 —— **渲染、对账、diff 是确定性的,交给脚本;「这一节讲的是什么」
「哪道题值得出」需要判断,由 Claude 做。** 混淆这两者,就会得到一个看起来自动、
实际上悄悄写错的管道。

## 8. 已知约束

### 认证:已打通(2026-08-06)

Notion MCP 走的是 Claude 这边的 OAuth,脚本用不了。因此建了一个 internal
integration,凭据放在 `~/blog/.env`(已被 `.gitignore` 忽略):

```
NOTION_TOKEN=ntn_...
NOTION_SYSTEM_III_ID=3995432c-88e6-80cf-8319-d77f1bc72634
```

**权限范围:只共享了 System III 一个页面**(2026-08-06 用 `/v1/search` 验证,
返回且仅返回该页)。将来要接别的页面,得在 Notion 里逐个把页面共享给这个
integration——父页共享会级联到子页。

连通性验证结果:整页递归走完 **444 个 block,29 次 API 调用**,43 个标题层级完整。

> **为什么这件事值得做:** MCP 的返回一定会进上下文。System III 现在 50K 字符
> ≈ 15–20K tokens,每次取数都要付,而且逐日增长。脚本落盘则是零上下文成本,
> 之后只读需要的切片(单天约 600 tokens),**不随页面增长**。

### 解析:REST API 返回结构化 block,不是 HTML

用 `/v1/blocks/{id}/children` 递归拉取,拿到的是 typed block JSON,代码块是独立的
`code` 类型、`plain_text` 原样保留。所以**在这条路径上不存在剥标签/反转义的问题**,
不需要任何 HTML 清洗。已验证 `if n < 10 && n > -10` 在 67 个 code block 中完整保留。

⚠️ 但那个坑对**另一个源**依然成立:抓 [Rust By Practice](https://practice-rust-zh.beatai.org/)
的题目时拿到的是 HTML,**必须先剥标签再反转义实体**,顺序反了 `<[^>]+>` 会把
`if n < 10 && n > -10` 整段吃掉。两个源两套处理,别混。

### 解析:图片 URL 必须剥掉签名串

Notion 托管的图片是 S3 签名链接,**每次拉取签名都不一样**。若原样写进缓存,每跑一次
`fetch`,`diff` 就会把这些行全报成「改动过」(Day3 有 7 张图 = 每次 7 行假差异,
`diff` 永远安静不下来)。

所以转换时剥掉 `?` 后的查询串,只留稳定路径,并在下一行留 `<!-- notion-block: <id> -->`。
代价是缓存里的图链**不能直接访问**;要真的用图,拿 block id 回 Notion 换新链接。

### 解析的真实工作量(已完成)

REST API 不返回 markdown,转换器要自己写:16 种 block、富文本标注(inline code 出现
210 次,最高频)、`has_children` 递归、表格的 `has_column_header`、以及遇到
`child_page` 必须停止递归。实际约 330 行,落在 `scripts/notion_sync.py`,仅用标准库。

### 检索:wiki 型 database 的搜索是坏的

Roddy's Wiki 是 wiki 型 database,`notion-search` 带 `data_source_url` 参数时
**恒返回空结果**。要用 `notion-query-data-sources` 走 SQL:

```
collection://1d35432c-88e6-80f2-9c31-000bb9d9e9f0
```

(2026-08-06 验证)

### 体积:拆页之后不再是问题

拆页前 System III 是一整页 50K 字符,单次 `notion-fetch` 就超出一次工具响应上限。
拆成日页之后,最大的一页(Day3)是 12.7K 字符,而且 `fetch` 按页比对
`last_edited_time`,平时只重拉当天那一页。

**Token 账**:改版前每次取数 ≈ 15–20K tokens 且逐日增长;现在 `notion.sh day 3`
读一页缓存,成本固定,且不随全库增长。

---

## 9. 下一步

1. ~~管道反转:源头改为 `dayN/src/main.rs`~~ —— ✅ 2026-08-07
2. ~~`new_day.sh` 产出现场记录骨架 + 自动写 launch.json~~ —— ✅
3. ~~`notion.sh render` / `audit` 反转参照系~~ —— ✅
4. **Day 4 跑通全流程** —— 他记完 `main.rs` 之后:生成 practice → 推 Notion →
   生成 NOTES 与博客 → 更新记忆
5. L4 再利用钩子:改 `src/content.config.ts` 加 `concepts` / `hook` / `analogies`,回填 Day 1–4
6. 第 2 章开始前,定 `rust_learn` 的跨章目录约定(见 §3 契约第 4 条)

---

_最后更新:2026-08-07_
