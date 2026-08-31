import mdx from '@astrojs/mdx'
import sitemap from '@astrojs/sitemap'
import swup from '@swup/astro'
import robotsTxt from 'astro-robots-txt'
import { defineConfig } from 'astro/config'
import rehypeKatex from 'rehype-katex'
import remarkMath from 'remark-math'
import UnoCSS from 'unocss/astro'
import devtoolsJson from 'vite-plugin-devtools-json'
import { themeConfig } from './src/.config'

// https://astro.build/config
export default defineConfig({
  site: themeConfig.site.website,
  prefetch: true,
  base: '/',
  // 2026-08-25:Rust 系列从「按天」改成「按难度阶梯」(见 PIPELINE.md §10)。
  // 旧的 day-N 文章已归档到 src/content/_archive-day-posts/,不再发布。
  // 这十条把已经流出去的 URL 接到它主要变成的那一级台阶上 —— 不留 404。
  redirects: {
    '/posts/rust/day-1-hello-rust': '/posts/rust/00-bindings-mutability-expressions',
    '/posts/rust/day-2-variables': '/posts/rust/00-bindings-mutability-expressions',
    '/posts/rust/day-3-ownership': '/posts/rust/01-ownership-and-memory',
    '/posts/rust/day-4-arrays-and-slices': '/posts/rust/03-arrays-slices-fat-pointers',
    '/posts/rust/day-5-enums-and-match': '/posts/rust/05-enums-and-sum-types',
    '/posts/rust/day-5-5-pattern-matching': '/posts/rust/06-pattern-matching',
    '/posts/rust/day-6-structs-and-traits': '/posts/rust/07-structs-impl-and-self',
    '/posts/rust/day-7-data-structure-cookbook': '/posts/rust/08-vec-and-hashmap',
    '/posts/rust/day-7-5-option-and-result': '/posts/rust/09-option-and-result',
    '/posts/rust/day-8-module': '/posts/rust/10-modules-and-visibility',
  },
  devToolbar: {
    enabled: false,
  },
  vite: {
    plugins: [
      // eslint-disable-next-line ts/ban-ts-comment
      // @ts-ignore
      devtoolsJson(),
    ],
  },
  markdown: {
    remarkPlugins: [
      remarkMath,
    ],
    rehypePlugins: [
      rehypeKatex,
    ],
    shikiConfig: {
      theme: 'dracula',
      wrap: true,
    },
  },
  integrations: [
    UnoCSS({ injectReset: true }),
    mdx({}),
    robotsTxt(),
    sitemap(),
    swup({
      theme: false,
      animationClass: 'transition-swup-',
      cache: true,
      preload: true,
      accessibility: true,
      smoothScrolling: true,
      updateHead: true,
      updateBodyClass: true,
    }),
  ],
})
