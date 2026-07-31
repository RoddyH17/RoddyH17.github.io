#!/bin/bash
# 博客发布:提交全部更改并推送到 GitHub
# push 到 main 后,GitHub Actions 会自动重建并部署
# 用法: ./sync.sh ["commit message"]
set -e
cd "$(dirname "$0")"

msg="${1:-post: daily update $(date +%Y-%m-%d)}"

git add -A
if git diff --cached --quiet; then
  echo "Nothing to commit."
  exit 0
fi
git commit -m "$msg"
git push origin main

echo ""
echo "✅ 已推送。构建进度: https://github.com/RoddyH17/blog/actions"
echo "🌐 博客地址: https://roddyh17.github.io/blog/"
