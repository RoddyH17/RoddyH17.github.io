import { file, glob } from 'astro/loaders'
import { defineCollection, z } from 'astro:content'

const posts = defineCollection({
  loader: glob({ pattern: '**/*.{md,mdx}', base: './src/content/posts' }),
  schema: ({ image }) =>
    z.object({
      title: z.string(),
      pubDate: z.coerce.date(),
      modDate: z.coerce.date().optional(),
      categories: z.array(z.string()),
      draft: z.boolean().default(false).optional(),
      description: z.string().optional(),
      customData: z.string().optional(),
      banner: image()
        .refine(img => Math.max(img.width, img.height) <= 4096, { message: 'Width and height of the banner must less than 4096 pixels' })
        .optional(),
      author: z.string().optional(),
      // Daily learning log tags, used only in aggregate by the sidebar widgets;
      // never displayed per-post (mood is private to the author).
      //   zen   = calm while learning/writing
      //   sorge = frustrated / agitated
      //   frage = an unresolved question kept nagging
      mood: z.array(z.enum(['zen', 'sorge', 'frage'])).optional(),
      commentsUrl: z.string().optional(),
      source: z.optional(z.object({ url: z.string(), title: z.string() })),
      enclosure: z.optional(z.object({ url: z.string(), length: z.number(), type: z.string() })),
      pin: z.boolean().default(false).optional(),
    }),
})

// Protocol research notes. Deliberately NOT a post category: posts are
// chronological and finished, research notes are a matrix of
// (protocol x version x mechanism) that gets revised for months.
// Everything a claim rests on is frontmatter, so provenance survives editing:
//   sources[]  — pinned code anchors (repo@commit:path#Lx-Ly)
//   deepwiki[] — the query trail: how the note was actually researched
const research = defineCollection({
  loader: glob({ pattern: '**/*.{md,mdx}', base: './src/content/research' }),
  schema: z.object({
    title: z.string(),
    // Identity in the research matrix.
    protocol: z.string(),
    version: z.string().optional(),
    topic: z.string(),
    // Which revision of THIS note — not of the protocol. `version` above is
    // Uniswap v2; `revision` is the 3rd time this note was rewritten. The two
    // move independently and the page labels them separately.
    revision: z.number().int().min(1).default(1),
    // What kind of research this is. Distinct from the protocol's sector:
    // sector says "Uniswap is a DEX", category says "this note is a math
    // derivation" rather than an economic or security analysis.
    category: z
      .enum(['mechanism-math', 'architecture', 'economics', 'security', 'empirical'])
      .default('mechanism-math'),
    // The one thing this note is for. Every note has a different one, and it
    // is the first thing a reader needs, so it is rendered above the body.
    goal: z.string().optional(),
    pubDate: z.coerce.date(),
    modDate: z.coerce.date().optional(),
    description: z.string().optional(),
    draft: z.boolean().default(false).optional(),
    // Maturity, so an unfinished note reads as unfinished instead of as fact.
    //   exploring = still reading, claims unverified
    //   working   = derivation done, executable check not green yet
    //   stable    = derivation verified against source and a passing test
    status: z.enum(['exploring', 'working', 'stable']).default('exploring'),
    confidence: z.number().min(0).max(5).default(0),
    // Reusable mechanism cards this note derives from or contributes to.
    mechanisms: z.array(z.string()).default([]),
    // Pinned code provenance. A commit makes the claim reproducible; without
    // one, upstream moves and the note silently becomes wrong.
    sources: z
      .array(
        z.object({
          repo: z.string(),
          commit: z.string().optional(),
          path: z.string().optional(),
          lines: z.string().optional(),
          note: z.string().optional(),
        }),
      )
      .default([]),
    // DeepWiki query trail — the retrieval step, kept so a conclusion can be
    // traced back to the question that produced it (and re-asked later).
    deepwiki: z
      .array(
        z.object({
          repo: z.string(),
          question: z.string(),
          url: z.string(),
          date: z.string().optional(),
        }),
      )
      .default([]),
    // Carried into the next session; the seed of the next note.
    open: z.array(z.string()).default([]),
  }),
})

// The protocol a research note is about. A note only carries `protocol: "uniswap"`,
// a bare string with nowhere to hang a logo, a stated goal, or a token — this
// collection is that entity. Hand-edited YAML, one entry per protocol.
const protocols = defineCollection({
  loader: file('./src/data/protocols.yaml'),
  schema: z.object({
    name: z.string(),
    // Card grouping on /research, and the axis along which this section grows
    // beyond DEX mechanics.
    sector: z.enum(['dex', 'lending', 'perps', 'infra']),
    chains: z.array(z.string()).default([]),
    // planned = on the roadmap with no notes yet. Rendered greyed and
    // unclickable, so an empty slot reads as a to-do rather than a dead link.
    status: z.enum(['active', 'planned']).default('planned'),
    logo: z.string(),
    // One sentence naming the core mechanism, not the ambition. Used verbatim
    // on the card and as the lead on the protocol page — written once so the
    // two cannot drift apart.
    mechanism: z.string(),
    // CoinGecko id, priced at view time via DefiLlama's keyless API. Optional:
    // no token, or an id we have not verified, must not break the page.
    token: z.object({ symbol: z.string(), id: z.string() }).optional(),
    links: z
      .object({
        site: z.string().optional(),
        github: z.string().optional(),
        deepwiki: z.string().optional(),
      })
      .default({}),
  }),
})

const spec = defineCollection({
  loader: glob({ pattern: '**/*.{md,mdx}', base: './src/content/spec' }),
})

export const collections = {
  posts,
  protocols,
  research,
  spec,
}
