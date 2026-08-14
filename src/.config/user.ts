import type { UserConfig } from '~/types'

export const userConfig: Partial<UserConfig> = {
  site: {
    title: 'Roddy\'s Wiki',
    author: 'Roddy',
    description:
      'Tech x Crypto Learning Roadmap — think, build, trade.',
    website: 'https://roddyh17.github.io/',
    pageSize: 10,
    navLinks: [
      { name: 'Posts', href: '/posts' },
      { name: 'Research', href: '/research' },
      { name: 'Archive', href: '/archive' },
      { name: 'About', href: '/about' },
    ],
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
  appearance: {
    locale: 'en-us',
    // Dune-inspired cosmic palette: desert sand by day, deep space + spice amber by night
    colorsLight: {
      primary: '#4a2f1d',
      background: '#f3e6d0',
    },
    colorsDark: {
      primary: '#e3b877',
      background: '#12101c',
    },
    fonts: {
      header:
        '"Marcellus","Noto Serif SC","Source Han Serif SC","Source Han Serif TC",serif',
      ui: '"Spectral","Noto Serif SC","Source Han Serif SC","Source Han Serif TC",Georgia,serif',
    },
  },
  seo: {
    twitter: '',
  },
  latex: {
    katex: true,
  },
}
