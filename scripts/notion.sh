#!/bin/bash
# Notion 取数层 —— 每日学习管道的「检索层」
#
# 用法:
#   ./scripts/notion.sh list              # 列出 System III 下的子页面(自动发现)
#   ./scripts/notion.sh fetch [--force]   # 拉取全部页面 → .cache/notion/
#   ./scripts/notion.sh day <N>           # 打印 Day N 那页的 markdown
#   ./scripts/notion.sh diff              # 与上次拉取相比,哪些标题增删了
#   ./scripts/notion.sh audit [N]         # 对账:以 dayN 现场记录为参照,查下游跟上没
#   ./scripts/notion.sh render <N>        # 把 dayN 的 main.rs 渲染成待推 Notion 的 markdown
#
# 日号只在章内唯一(Chapter 2 会重新从 Day 1 开始),跨章重号时写成 <章>.<日>,
# 例如 `day 2.3` = 第 2 章的 Day 3。第 1 章可以省略,直接 `day 3`。
#
# 例:
#   ./scripts/notion.sh fetch
#   ./scripts/notion.sh day 3 | head -60
#
# 为什么存在:MCP 取数每次都会进上下文(System III 曾经 50K 字符 ≈ 15-20K tokens,
# 且逐日增长)。落盘之后只读需要的那一页,成本不随页面增长。完整理由见 PIPELINE.md。
#
# 注意: 这是检索层,不是结论层 —— 和 deepwiki.sh 同一条原则。切片、落盘、diff 是
# 确定性的;「这一节属于哪天」「哪道题该抄进 practice.rs」需要判断,不在这里做。
set -e
cd "$(dirname "$0")/.."

if [ ! -f .env ]; then
  echo "❌ 缺少 .env。需要 NOTION_TOKEN 与 NOTION_SYSTEM_III_ID"
  echo "   建 integration 的步骤见 PIPELINE.md §8"
  exit 1
fi

# .env 里是 KEY=VALUE,自动导出给 python
set -a
# shellcheck disable=SC1091
. ./.env
set +a

: "${NOTION_TOKEN:?❌ .env 里没有 NOTION_TOKEN}"
: "${NOTION_SYSTEM_III_ID:?❌ .env 里没有 NOTION_SYSTEM_III_ID}"
export NOTION_CACHE_DIR="${NOTION_CACHE_DIR:-.cache/notion}"

cmd="${1:-}"
case "$cmd" in
  list | fetch | day | diff | audit | render)
    exec python3 scripts/notion_sync.py "$@"
    ;;
  "")
    sed -n '2,18p' "$0" | sed 's/^# \{0,1\}//'
    exit 1
    ;;
  *)
    echo "❌ 未知命令: $cmd (可用: list / fetch / day / diff / audit / render)"
    exit 1
    ;;
esac
