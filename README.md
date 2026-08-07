# blog — Roddy 的学习志 (roddyh17.github.io)

基于 [astro-theme-typography](https://github.com/Moeyua/astro-theme-typography)(活版印字主题)的 Astro 静态博客,GitHub Actions 自动部署到 GitHub Pages 根域名。

- 🌐 **线上**: https://roddyh17.github.io/
- 📦 **仓库**: github.com/RoddyH17/RoddyH17.github.io(本地目录 `~/blog`;上一版 Next.js 站在 `nextjs-archive` 分支)
- ✍️ **写文章**: 往 `src/content/posts/<类别>/` 丢一个 `.md` / `.mdx` 即可
- 🏷️ **分类 = 文件夹 + frontmatter categories**:新类别自动出现在 /categories/
- 🔧 **架构说明**: [PIPELINE.md](./PIPELINE.md) —— 每日学习管道(Notion → rust_learn → blog)为什么存在、由哪几层构成

## 结构

```
blog/
├── src/content/posts/
│   ├── rust/                # ★ Rust 系列 (day-N-*.mdx)
│   └── crypto/              # ★ Crypto 数据系列;新类别=新文件夹
├── src/content/research/    # ★ 协议研究笔记(独立集合,不是 posts 类别)
├── src/content/spec/about.md  # 关于页
├── src/.config/user.ts      # ★ 站点配置(标题/作者/导航/社交链接/KaTeX)
├── scripts/deepwiki.sh      # DeepWiki 检索层(research 管道)
├── new_post.sh              # 新建文章草稿脚手架
├── new_research.sh          # 新建研究笔记脚手架
├── sync.sh                  # 一键 commit + push + 触发部署
├── PIPELINE.md              # ★ 每日学习管道架构说明
└── .github/workflows/deploy.yml
```

## 写作流程

```bash
./new_post.sh rust day-3-ownership "Day 3 · 所有权"
# ... 编辑 src/content/posts/rust/day-3-ownership.md,写完删掉 draft: true ...
./sync.sh "post: day 3 ownership"      # 发布,~1 分钟上线
```

frontmatter 字段(主题 schema):

```yaml
---
title: Day 3 · 所有权
pubDate: 2026-08-06 # 注意是 pubDate 不是 publishedAt
author: Roddy
description: 一句话摘要 # 注意是 description 不是 summary
categories: [rust] # 数组;与所在文件夹保持一致
mood: [zen] # 可选,学习心情标签(私有,不在页面上显示)
draft: true # 草稿不上线;删掉这行即发布
---
```

## 页面

- `/` 文章列表(分页) · `/archive` 归档 · `/categories` 分类筛选 · `/about` 关于 · `/atom.xml` RSS
- 文章 URL: `/posts/<类别>/<slug>/`
- 支持 KaTeX 数学公式(`$...$` / `$$...$$`)

## 本地预览

```bash
npm run dev    # → http://localhost:4321
```
