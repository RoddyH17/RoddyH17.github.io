import { Icons } from "@/components/icons";
import { HomeIcon, NotebookIcon } from "lucide-react";
import { Typescript } from "@/components/ui/svgs/typescript";
import { Python } from "@/components/ui/svgs/python";
import { Golang } from "@/components/ui/svgs/golang";
import { Csharp } from "@/components/ui/svgs/csharp";
import { NextjsIconDark } from "@/components/ui/svgs/nextjsIconDark";

export const DATA = {
  name: "Roddy Huang",
  initials: "RH",
  url: "https://roddyh17.github.io",
  location: "Ithaca, NY",
  locationLink: "https://www.google.com/maps/place/ithaca",
  description:
    "Cornell math major learning Rust in public. Daily notes, code, and reflections from a C++ perspective.",
  summary:
    "This is my learning log — one day, one folder, one post. The current series is Rust: I come from a C++ / Python / quant background, and every post reflects on what Rust does differently from C++: ownership vs manual memory management, cargo vs CMake, traits vs templates. All code lives in [RoddyH17/rust_learn](https://github.com/RoddyH17/rust_learn) — each `dayN/` folder is a runnable crate, each blog post is a plain MDX file anyone (including future me) can edit.",
  avatarUrl: "",
  skills: [
    { name: "Rust", icon: undefined },
    { name: "C++", icon: Csharp },
    { name: "Python", icon: Python },
    { name: "Typescript", icon: Typescript },
    { name: "Go", icon: Golang },
    { name: "Next.js", icon: NextjsIconDark },
  ],
  navbar: [
    { href: "/", icon: HomeIcon, label: "Home" },
    { href: "/blog", icon: NotebookIcon, label: "Blog" },
  ],
  contact: {
    email: "zh89@cornell.edu",
    tel: "",
    social: {
      GitHub: {
        name: "GitHub",
        url: "https://github.com/RoddyH17",
        icon: Icons.github,
        navbar: true,
      },
      email: {
        name: "Send Email",
        url: "mailto:zh89@cornell.edu",
        icon: Icons.email,
        navbar: false,
      },
    },
  },

  work: [],

  education: [
    {
      school: "Cornell University",
      href: "https://www.cornell.edu",
      degree: "B.A. Mathematics, minor in Operations Research (ORIE)",
      logoUrl: "",
      start: "2022",
      end: "2026",
    },
  ],

  projects: [
    {
      title: "rust_learn",
      href: "https://github.com/RoddyH17/rust_learn",
      dates: "July 2026 - Present",
      active: true,
      description:
        "This site. A daily Rust learning pipeline: each `dayN/` folder is a runnable cargo crate, each lesson ends with a blog post comparing Rust and C++. Deployed to GitHub Pages on every push.",
      technologies: ["Rust", "Cargo", "Next.js", "MDX", "GitHub Actions"],
      links: [
        {
          type: "Source",
          href: "https://github.com/RoddyH17/rust_learn",
          icon: <Icons.github className="size-3" />,
        },
      ],
      image: "",
      video: "",
    },
    {
      title: "ml-hft",
      href: "https://github.com/RoddyH17/ml-hft",
      dates: "2026",
      active: true,
      description:
        "LOB microstructure signal pipeline: Numba JIT feature engineering (50× speedup) + XGBoost walk-forward validation for high-frequency signals.",
      technologies: ["Python", "Numba", "XGBoost"],
      links: [
        {
          type: "Source",
          href: "https://github.com/RoddyH17/ml-hft",
          icon: <Icons.github className="size-3" />,
        },
      ],
      image: "",
      video: "",
    },
  ],

  hackathons: [],
} as const;
