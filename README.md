# blog — 个人学习博客

Next.js + MDX 静态博客(dillionverma/portfolio 模板改造),GitHub Actions 自动部署到 GitHub Pages。

- 🌐 **线上**: https://roddyh17.github.io/blog/
- ✍️ **写文章**: 往 `content/` 丢一个 `.mdx` 文件即可,无需改代码
- 📦 当前内容线: 每日 Rust 学习(代码在 [RoddyH17/rust_learn](https://github.com/RoddyH17/rust_learn)),后续可扩展其他系列

## 结构

```
blog/
├── content/                 # ★ 文章目录,一篇 = 一个 .mdx
├── src/data/resume.tsx      # 首页个人信息(名字/简介/技能/项目)
├── src/app/                 # 页面(首页 / 文章列表 / 文章详情,自动读 content/)
├── next.config.mjs          # 静态导出: output export + basePath /blog
├── sync.sh                  # 一键 commit + push + 触发部署
└── .github/workflows/deploy.yml
```

## 文章格式

`content/day-2-ownership.mdx`:

```yaml
---
title: "Day 2 · 所有权"
publishedAt: "2026-08-01"
author: "Roddy"
summary: "一句话摘要,显示在列表页"
---
```

正文为标准 Markdown/MDX,支持代码块(shiki 高亮)、表格、图片。

## 本地预览

```bash
npm run dev    # → http://localhost:3000/blog
```

## 发布

```bash
./sync.sh "post: day 2 ownership"
```

## 注意(静态导出限制)

- 新页面不要用 `searchParams` / edge runtime(如 opengraph-image),`output: "export"` 不支持
- URL 带 trailing slash(`trailingSlash: true`),GitHub Pages 需要
