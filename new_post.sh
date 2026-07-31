#!/bin/bash
# 新建一篇博客草稿(按类别归入 content/<category>/ 文件夹)
# 用法: ./new_post.sh <category> <slug> ["标题"]
# 例:  ./new_post.sh rust_learn day-3-structs "Day 3 · 结构体"
#      ./new_post.sh crypto_map dune-sql-notes "Dune SQL 笔记"
# 类别文件夹不存在会自动创建,网站筛选按钮随之自动出现
# 生成的文章默认 draft: true(不上线),写完把这行删掉再 sync 即发布
set -e
cd "$(dirname "$0")"

category="${1:?用法: ./new_post.sh <category> <slug> [\"标题\"]}"
slug="${2:?用法: ./new_post.sh <category> <slug> [\"标题\"]}"
title="${3:-$slug}"
file="content/${category}/${slug}.mdx"

if [ -e "$file" ]; then
  echo "❌ $file 已存在"
  exit 1
fi

mkdir -p "content/${category}"

cat > "$file" <<EOF
---
title: "$title"
publishedAt: "$(date +%Y-%m-%d)"
author: "Roddy"
summary: "TODO: 一句话摘要"
draft: true
---

# $title

TODO: 正文
EOF

echo "✅ 已创建 $file (草稿状态, 类别: $category)"
echo "   写完后删掉 'draft: true' 那一行,再跑 ./sync.sh 即发布"
echo "   上线后 URL: https://roddyh17.github.io/blog/${category}/${slug}/"
