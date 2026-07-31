#!/bin/bash
# 新建一篇博客草稿
# 用法: ./new_post.sh <slug> [category] ["标题"]
# 例:  ./new_post.sh day-2-ownership rust "Day 2 · 所有权"
# 生成的文章默认 draft: true(不上线),写完把这行删掉再 sync 即发布
set -e
cd "$(dirname "$0")"

slug="${1:?用法: ./new_post.sh <slug> [category] [\"标题\"]}"
category="${2:-rust}"
title="${3:-$slug}"
file="content/${slug}.mdx"

if [ -e "$file" ]; then
  echo "❌ $file 已存在"
  exit 1
fi

cat > "$file" <<EOF
---
title: "$title"
publishedAt: "$(date +%Y-%m-%d)"
author: "Roddy"
category: "$category"
summary: "TODO: 一句话摘要"
draft: true
---

# $title

TODO: 正文

## 今天的反思(vs C++)

TODO
EOF

echo "✅ 已创建 $file (草稿状态)"
echo "   写完后删掉 'draft: true' 那一行,再跑 ./sync.sh 即发布"
