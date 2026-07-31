# blog — 个人学习博客 (roddyh17.github.io)

Next.js + MDX 静态博客(dillionverma/portfolio 模板改造),GitHub Actions 自动部署到 GitHub Pages 根域名。

- 🌐 **线上**: https://roddyh17.github.io/
- 📦 **仓库**: github.com/RoddyH17/RoddyH17.github.io(本地目录 `~/blog`)
- ✍️ **写文章**: 往 `content/` 丢一个 `.mdx` 文件即可,无需改代码
- 🏷️ **分类**: frontmatter `category` 字段驱动列表页筛选 chips。当前: `rust`;以后随意加(`quant` / `ai` / `life` …),出现即自动生成筛选按钮

## 结构

```
blog/
├── content/                 # ★ 文章目录,一篇 = 一个 .mdx
├── new_post.sh              # 新建文章草稿脚手架
├── sync.sh                  # 一键 commit + push + 触发部署
├── src/data/resume.tsx      # 首页个人信息(名字/简介/技能/项目)
├── src/app/                 # 页面(首页 / /blog 列表 / /blog/<slug> 详情)
├── src/components/blog-list.tsx  # 列表 + 分类筛选(client)
└── .github/workflows/deploy.yml
```

## 写作流程

```bash
./new_post.sh day-2-ownership rust "Day 2 · 所有权"   # 生成草稿 (draft: true)
# ... 编辑 content/day-2-ownership.mdx,写完删掉 draft: true 那行 ...
./sync.sh "post: day 2 ownership"                     # 发布,~1 分钟上线
```

frontmatter 字段:

```yaml
---
title: "Day 2 · 所有权"
publishedAt: "2026-08-01"
author: "Roddy"
category: "rust"        # 分类,驱动筛选
summary: "一句话摘要"
draft: true             # 草稿不上线;删掉这行即发布
---
```

## 本地预览

```bash
npm run dev    # → http://localhost:3000
```

## 注意(静态导出限制)

- 新页面不要用 `searchParams` / edge runtime(如 opengraph-image),`output: "export"` 不支持
- URL 带 trailing slash(`trailingSlash: true`),GitHub Pages 需要
