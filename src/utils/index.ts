import type { Post } from '~/types'
import { getCollection } from 'astro:content'
import dayjs from 'dayjs'
import MarkdownIt from 'markdown-it'
import sanitizeHtml from 'sanitize-html'

export async function getCategories() {
  const posts = await getPosts()
  const categories = new Map<string, Post[]>()

  for (const post of posts) {
    if (post.data.categories) {
      for (const c of post.data.categories) {
        const posts = categories.get(c) || []
        posts.push(post)
        categories.set(c, posts)
      }
    }
  }

  return categories
}

export async function getPosts(isArchivePage = false) {
  const posts = await getCollection('posts')

  posts.sort((a, b) => {
    if (isArchivePage) {
      return dayjs(a.data.pubDate).isBefore(dayjs(b.data.pubDate)) ? 1 : -1
    }

    const aDate = a.data.modDate ? dayjs(a.data.modDate) : dayjs(a.data.pubDate)
    const bDate = b.data.modDate ? dayjs(b.data.modDate) : dayjs(b.data.pubDate)

    return aDate.isBefore(bDate) ? 1 : -1
  })

  if (import.meta.env.PROD) {
    return posts.filter(post => post.data.draft !== true)
  }

  return posts
}

export async function getFeedPosts() {
  const posts = await getPosts()

  posts.sort((a, b) => {
    if (a.data.pin && !b.data.pin)
      return -1
    if (!a.data.pin && b.data.pin)
      return 1
    return 0
  })

  return posts
}

export async function getResearch() {
  const notes = await getCollection('research')

  // Matrix order, not chronological: protocol, then version, then title.
  notes.sort((a, b) => {
    const p = a.data.protocol.localeCompare(b.data.protocol)
    if (p !== 0)
      return p
    const v = (a.data.version ?? '').localeCompare(b.data.version ?? '', undefined, { numeric: true })
    if (v !== 0)
      return v
    return a.data.title.localeCompare(b.data.title)
  })

  if (import.meta.env.PROD) {
    return notes.filter(note => note.data.draft !== true)
  }

  return notes
}

/** Group research notes by protocol, preserving the sort order above. */
export async function getResearchByProtocol() {
  const notes = await getResearch()
  const grouped = new Map<string, typeof notes>()

  for (const note of notes) {
    const list = grouped.get(note.data.protocol) || []
    list.push(note)
    grouped.set(note.data.protocol, list)
  }

  return grouped
}

/**
 * Protocols for the research index, grouped by sector in a fixed reading order
 * (what we study now first, what everything sits on last) rather than
 * alphabetically — the order is editorial, so it is stated here, not inferred.
 *
 * `status` in the YAML is a hand-set intent; `noteCount` is the fact. A
 * protocol with notes is always clickable regardless of what the YAML claims,
 * so the two cannot contradict each other on screen.
 */
const SECTOR_ORDER = ['dex', 'perps', 'lending', 'infra'] as const

export const SECTOR_LABEL: Record<string, string> = {
  dex: 'DEX / AMM',
  perps: 'Perpetuals',
  lending: 'Lending',
  infra: 'Infrastructure',
}

/** What kind of research a note is — displayed on the note header and index. */
export const CATEGORY_LABEL: Record<string, string> = {
  'mechanism-math': 'Mechanism math',
  'architecture': 'Architecture',
  'economics': 'Economics',
  'security': 'Security',
  'empirical': 'Empirical',
}

export async function getProtocolsBySector() {
  const protocols = await getCollection('protocols')
  const counts = await getResearchByProtocol()

  const decorated = protocols.map(p => ({
    ...p,
    noteCount: counts.get(p.id)?.length ?? 0,
  }))

  const grouped = new Map<string, typeof decorated>()
  for (const sector of SECTOR_ORDER) {
    const inSector = decorated
      .filter(p => p.data.sector === sector)
      // Ones with research first, then the roadmap, each alphabetical.
      .sort((a, b) => (b.noteCount - a.noteCount) || a.data.name.localeCompare(b.data.name))

    if (inSector.length > 0)
      grouped.set(sector, inSector)
  }

  return grouped
}

/** One protocol by id, or undefined. Used by the protocol detail page. */
export async function getProtocol(id: string) {
  const protocols = await getCollection('protocols')
  return protocols.find(p => p.id === id)
}

const parser = new MarkdownIt()
export function getPostDescription(post: Post) {
  if (post.data.description) {
    return post.data.description
  }

  const html = parser.render(post.body || '')
  const sanitized = sanitizeHtml(html, { allowedTags: [] })
  return sanitized.slice(0, 400)
}

export function formatDate(date: Date, format: string = 'YYYY-MM-DD') {
  // Frontmatter dates like "2026-08-04" are parsed as UTC midnight; formatting
  // them in local time shifts the day. Shift back so the displayed date matches
  // the date written in frontmatter.
  return dayjs(new Date(date.getTime() + date.getTimezoneOffset() * 60000)).format(format)
}
