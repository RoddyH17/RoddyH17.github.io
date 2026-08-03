import type { UserConfig } from '~/types'

export const userConfig: Partial<UserConfig> = {
  site: {
    title: 'Roddy 的学习志',
    subtitle: 'Learning in public',
    author: 'Roddy',
    description:
      'Daily learning log — Rust from a C++ perspective, crypto data, quant, and more.',
    website: 'https://roddyh17.github.io/',
    pageSize: 10,
    socialLinks: [
      {
        name: 'github',
        href: 'https://github.com/RoddyH17',
      },
      {
        name: 'rss',
        href: '/atom.xml',
      },
    ],
    footer: [
      '© %year <a target="_blank" href="%website">%author</a>',
      'Theme <a target="_blank" href="https://github.com/Moeyua/astro-theme-typography">Typography</a> by <a target="_blank" href="https://moeyua.com">Moeyua</a>',
    ],
  },
  seo: {
    twitter: '',
  },
  latex: {
    katex: true,
  },
}
