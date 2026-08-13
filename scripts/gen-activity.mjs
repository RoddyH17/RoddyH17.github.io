#!/usr/bin/env node
// Generates src/data/activity.json — the push side of the Toxicity heatmap.
//
// Why this exists: the heatmap used to light a cell only when a post's `pubDate`
// fell on that day, which is a record of *publishing*, not of *working*. A day
// spent pushing commits with nothing published stayed dark, and a backdated
// pubDate lit the wrong cell (Day 7 was written on 08-12 but dated 08-11, so it
// merged into a cell that already held Day 5.5 and Day 6 while 08-12 stayed
// blank). This script supplies the missing half: which days actually saw commits.
//
// ---------------------------------------------------------------------------
// Day boundaries
// ---------------------------------------------------------------------------
// We take the date straight off `%cI` (strict ISO committer date) rather than
// converting anything. Git records the committer's UTC offset in the commit, so
// `2026-08-12T22:55:15-04:00` already carries the calendar date as it was *where
// the commit was made* — 08-12, a late evening in New York.
//
// Converting to UTC instead would push every evening commit onto the next day's
// cell, which is precisely the kind of off-by-one that makes a heatmap quietly
// lie. Reading the local date also follows travel automatically, with no
// hardcoded timezone to go stale.
//
// ---------------------------------------------------------------------------
// Output is gitignored on purpose
// ---------------------------------------------------------------------------
// It is derived data, regenerated on every `npm run build`. Committing it would
// mean a file that is dirty after every local build and stale in every PR.
// LearningPulse.astro treats a missing file as "no commit data" and falls back
// to publish-only behaviour, so a build that skips this script still works.

import { execFileSync } from 'node:child_process'
import { existsSync, mkdirSync, writeFileSync } from 'node:fs'
import { homedir } from 'node:os'
import { dirname, join, resolve } from 'node:path'
import process from 'node:process'
import { fileURLToPath } from 'node:url'

const repoRoot = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const OUT = join(repoRoot, 'src', 'data', 'activity.json')

// Only the window the heatmap can actually draw (12 weeks) plus slack, so the
// file stays small and the git log call stays cheap.
const SINCE = '1.year.ago'

// Where each tracked repo lives. CI checks rust_learn out into the workspace;
// locally it sits next to the blog in $HOME. First existing path wins, and a
// repo that is nowhere to be found is skipped rather than failing the build —
// a missing sibling checkout must not be able to break the site.
const REPOS = [
  { name: 'blog', candidates: [repoRoot] },
  {
    name: 'rust_learn',
    candidates: [
      process.env.RUST_LEARN_PATH,
      join(repoRoot, '.rust_learn'),
      join(homedir(), 'rust_learn'),
    ].filter(Boolean),
  },
]

function git(cwd, args) {
  return execFileSync('git', args, { cwd, encoding: 'utf8', stdio: ['ignore', 'pipe', 'pipe'] })
}

/** @type {Record<string, Record<string, number>>} */
const days = {}
const report = []

for (const repo of REPOS) {
  const path = repo.candidates.find(c => existsSync(join(c, '.git')))
  if (!path) {
    report.push(`  ${repo.name.padEnd(11)} — not found, skipped`)
    continue
  }

  // A shallow clone silently yields almost no history, which would look exactly
  // like "you did not work" instead of like a broken checkout. Say so loudly:
  // this is the failure mode the whole feature is meant to avoid.
  let shallow = false
  try {
    shallow = git(path, ['rev-parse', '--is-shallow-repository']).trim() === 'true'
  }
  catch {
    /* old git without the flag — assume full */
  }

  let lines = []
  try {
    lines = git(path, ['log', `--since=${SINCE}`, '--pretty=format:%cI'])
      .split('\n')
      .filter(Boolean)
  }
  catch (err) {
    report.push(`  ${repo.name.padEnd(11)} — git log failed, skipped (${err.message.trim()})`)
    continue
  }

  for (const iso of lines) {
    const day = iso.slice(0, 10) // see "Day boundaries" above
    days[day] ??= {}
    days[day][repo.name] = (days[day][repo.name] ?? 0) + 1
  }

  report.push(
    `  ${repo.name.padEnd(11)} — ${lines.length} commits${
      shallow ? '  ⚠️  SHALLOW CLONE: history is truncated, heatmap will be wrong' : ''}`,
  )
}

mkdirSync(dirname(OUT), { recursive: true })
writeFileSync(
  OUT,
  `${JSON.stringify({ generatedAt: new Date().toISOString(), since: SINCE, days }, null, 2)}\n`,
)

console.log('activity.json:')
console.log(report.join('\n'))
console.log(`  → ${Object.keys(days).length} active days written to src/data/activity.json`)
