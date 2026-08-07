import type { CollectionEntry } from 'astro:content'

export type Post = CollectionEntry<'posts'>
export type Research = CollectionEntry<'research'>
export * from './themeConfig.ts'
