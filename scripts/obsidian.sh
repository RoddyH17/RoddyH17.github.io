#!/bin/bash
# Obsidian vault → Notion / 博客 的转换层入口(原型,2026-08-25)
#
# 用法:
#   ./scripts/obsidian.sh list             # 列出 vault 里全部笔记
#   ./scripts/obsidian.sh changed          # 只列出新增/改过的(对照 manifest)
#   ./scripts/obsidian.sh doctor [--only P] # 按 vault 规范体检(--only 只过滤报告范围)
#   ./scripts/obsidian.sh notion <path>    # 输出 Notion-flavored markdown
#   ./scripts/obsidian.sh post <path> [类别] # 输出博客 .md(默认 rust,draft: true)
#   ./scripts/obsidian.sh commit           # 同步成功后,把当前状态写进 manifest
#
# 为什么 changed/commit 分开:同步这一步必须由人或 Claude 判断(哪几条值得发、
# 标题怎么写),脚本只负责「有哪些变了」这个确定性问题。同 PIPELINE.md
# 「检索层不是结论层」。
#
# ⚠️ 写 Notion 仍然要走 MCP:.env 里那个 integration 是**只读**的,
#    和 notion.sh 的处境一样(见 PIPELINE.md §3「读和写走两条不同的路」)。
set -e
cd "$(dirname "$0")/.."

export OBSIDIAN_VAULT="${OBSIDIAN_VAULT:-$HOME/Ob_workflow/obsidian/Ideas/2026}"

if [ ! -d "$OBSIDIAN_VAULT" ]; then
  echo "❌ 找不到 vault: $OBSIDIAN_VAULT"
  echo "   用 OBSIDIAN_VAULT=... 覆盖"
  exit 1
fi

cmd="${1:-}"
case "$cmd" in
  list | changed | doctor | commit | notion | post | ladder | build-posts)
    exec python3 scripts/obsidian_sync.py "$@"
    ;;
  "")
    sed -n '2,17p' "$0" | sed 's/^# \{0,1\}//'
    exit 1
    ;;
  *)
    echo "❌ 未知命令: $cmd (可用: list / changed / doctor / commit / notion / post / ladder / build-posts)"
    exit 1
    ;;
esac
