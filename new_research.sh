#!/bin/bash
# 新建一篇协议研究笔记(MDX,归入 src/content/research/<protocol>/)
# 用法: ./new_research.sh <protocol> <slug> ["标题"] [version]
# 例:  ./new_research.sh uniswap amm-v2-lp "AMM v2 LP" v2
#      ./new_research.sh uniswap tick-math "Tick and sqrt price" v3
#
# 与 new_post.sh 同构:默认 draft: true(不上线),写完删掉那行再 sync 即发布。
# 与博客文章的区别:research 不是时间流,是 protocol x version 的矩阵,
# 会反复修订。所有出处(代码锚点、DeepWiki 检索轨迹)都放 frontmatter,
# 由 /research/<id> 页面自动渲染,不写进正文,避免正文改着改着和出处脱节。
set -e
cd "$(dirname "$0")"

protocol="${1:?用法: ./new_research.sh <protocol> <slug> [\"标题\"] [version]}"
slug="${2:?用法: ./new_research.sh <protocol> <slug> [\"标题\"] [version]}"
title="${3:-$slug}"
version="${4:-}"
file="src/content/research/${protocol}/${slug}.mdx"

if [ -e "$file" ]; then
  echo "❌ $file 已存在"
  exit 1
fi

mkdir -p "src/content/research/${protocol}"

# 模板用引号 heredoc 写死,再用 sed 替换占位符 —— 和 new_day.sh 一致。
# (必须引号 heredoc:正文里的 $$ 是 KaTeX 块级公式,不能被 shell 展开)
cat > "$file" <<'TEMPLATE'
---
title: "__TITLE__"
protocol: "__PROTOCOL__"
version: "__VERSION__"
topic: "__TOPIC__"
# revision = 这篇笔记自己的第几次重写(协议版本是上面的 version,两者独立)
revision: 1
# mechanism-math | architecture | economics | security | empirical
category: mechanism-math
# 这篇研究的主要目标 —— 每篇不同,渲染在正文之上
goal: "TODO: what this note is for"
pubDate: "__DATE__"
description: "TODO: one line — what question this note answers"
# exploring = still reading | working = derived, not verified | stable = verified against source + passing test
status: exploring
confidence: 0
# Reusable mechanism cards this note derives from or feeds into.
mechanisms: []
# Pinned code anchors. commit is required for a claim to count as a finding.
#   - repo: "Uniswap/v2-core"
#     commit: "1136544ac842ff48ae0b1b939701436598d74075"
#     path: "contracts/UniswapV2Pair.sol"
#     lines: "170-182"
#     note: "optimistic transfer, then K check"
sources: []
# DeepWiki retrieval trail — appended automatically by:
#   ./scripts/deepwiki.sh ask <repo> "<question>" --note __FILE__
deepwiki: []
open: []
draft: true
---

{/* Two sections, and only two. The first says what is being taken apart and
    why it is not the traditional version of itself; the second is what the
    source actually turned out to say. Everything else is either provenance
    (already in the frontmatter above) or a conclusion that has not been
    reached yet. */}

## 1. The question we came in with

{/* What is being researched, and what it replaces.

    Name the traditional counterpart explicitly — a limit order book, a
    market maker's quote, a bank's rate desk, a clearing house — and say
    what it could rely on that this mechanism cannot: a counterparty, a
    trusted operator, the ability to cancel, off-chain state, unbounded
    precision.

    The interesting question is almost always what had to be given up to
    remove that reliance, and what the mechanism got in exchange.

    One paragraph. If it takes three, the note is scoped too wide. */}

TODO

## 2. Reading the source

{/* Not a tour of the repository. What was found by reading it, in the
    order it was found, with the reasoning left in.

    Three things belong here and nowhere else:

    - What DeepWiki claimed, and whether the source agreed. It is a
      retrieval layer, not a conclusion layer, and it does answer wrongly
      — a broad question about UniswapV2Pair.swap put the K check before
      the optimistic transfer, which is backwards. When it disagrees with
      the code, the code wins and the disagreement gets written down here,
      pinned to repo@commit:path#lines in `sources:` above.

    - Where clean algebra and shipped code diverge: the fixed-point format,
      which direction a quantity rounds, and whom that rounding favours.
      The divergence is never an accident; say who it is for. This is the
      part a second-hand summary cannot produce.

    - What was misread first, and what corrected it. Future-you needs the
      wrong turn more than the clean result. */}

TODO
TEMPLATE

topic="${title}"
sed -i '' \
  -e "s|__TITLE__|${title}|g" \
  -e "s|__PROTOCOL__|${protocol}|g" \
  -e "s|__VERSION__|${version}|g" \
  -e "s|__TOPIC__|${topic}|g" \
  -e "s|__DATE__|$(date +%Y-%m-%d)|g" \
  -e "s|__FILE__|${file}|g" \
  "$file"

echo "✅ 已创建 $file (草稿状态)"
echo ""
echo "下一步:"
# 协议实体(logo / 目标 / 代币)在 protocols.yaml 里,不在笔记里。
# 没有对应条目的话,/research 卡片墙上不会出现这个协议。
if ! grep -q "^- id: ${protocol}\$" src/data/protocols.yaml 2>/dev/null; then
  echo "  0. ⚠️  src/data/protocols.yaml 里还没有 '${protocol}',先加一条(logo/目标/代币),"
  echo "        再跑 ./scripts/fetch-logos.sh 补 logo"
fi
echo "  1. 检索:  ./scripts/deepwiki.sh structure <Org>/<repo>"
echo "  2. 提问:  ./scripts/deepwiki.sh ask <repo> \"<问题>\" --note ${file}"
echo "  3. 预览:  npm run dev   →  http://localhost:4321/research/${protocol}/${slug}"
echo "  4. 发布:  删掉 frontmatter 里的 'draft: true',再 ./sync.sh"
