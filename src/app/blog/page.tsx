import BlurFade from "@/components/magicui/blur-fade";
import BlogList from "@/components/blog-list";
import { allPosts } from "content-collections";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Blog",
  description: "Daily learning notes. Current series: Rust, from a C++ perspective.",
  openGraph: {
    title: "Blog",
    description: "Daily learning notes. Current series: Rust, from a C++ perspective.",
  },
  twitter: {
    card: "summary_large_image",
    title: "Blog",
    description: "Daily learning notes. Current series: Rust, from a C++ perspective.",
  },
};

const BLUR_FADE_DELAY = 0.04;

export default function BlogPage() {
  const posts = [...allPosts]
    .filter((post) => !post.draft)
    .sort((a, b) => (new Date(a.publishedAt) > new Date(b.publishedAt) ? -1 : 1))
    .map((post) => ({
      slug: post._meta.path.replace(/\.mdx$/, ""),
      title: post.title,
      publishedAt: post.publishedAt,
      category: post.category,
    }));

  return (
    <section id="blog">
      <BlurFade delay={BLUR_FADE_DELAY}>
        <h1 className="text-2xl font-semibold tracking-tight mb-2">Blog <span className="ml-1 bg-card border border-border rounded-md px-2 py-1 text-muted-foreground text-sm">{posts.length} posts</span></h1>
        <p className="text-sm text-muted-foreground mb-8">
          One post a day. Current series: learning Rust, compared against C++.
        </p>
      </BlurFade>
      <BlogList posts={posts} />
    </section>
  );
}
