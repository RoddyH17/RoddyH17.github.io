"use client";

import BlurFade from "@/components/magicui/blur-fade";
import Link from "next/link";
import { ChevronRight } from "lucide-react";
import { useState } from "react";

const BLUR_FADE_DELAY = 0.04;

export type BlogListPost = {
  slug: string;
  title: string;
  publishedAt: string;
  category: string;
};

export default function BlogList({ posts }: { posts: BlogListPost[] }) {
  const categories = Array.from(new Set(posts.map((p) => p.category)));
  const [active, setActive] = useState<string>("all");

  const filtered =
    active === "all" ? posts : posts.filter((p) => p.category === active);

  return (
    <>
      {categories.length > 1 && (
        <BlurFade delay={BLUR_FADE_DELAY * 2}>
          <div className="flex flex-wrap gap-2 mb-8">
            {["all", ...categories].map((cat) => (
              <button
                key={cat}
                onClick={() => setActive(cat)}
                className={`h-7 px-3 text-xs font-medium rounded-lg border transition-colors cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring ${
                  active === cat
                    ? "bg-primary text-background border-primary"
                    : "bg-background text-muted-foreground border-border hover:bg-accent/50"
                }`}
              >
                {cat}
              </button>
            ))}
          </div>
        </BlurFade>
      )}

      {filtered.length > 0 ? (
        <div className="flex flex-col gap-5">
          {filtered.map((post, id) => (
            <BlurFade delay={BLUR_FADE_DELAY * 3 + id * 0.05} key={post.slug}>
              <Link
                className="flex items-start gap-x-2 group cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
                href={`/blog/${post.slug}`}
              >
                <span className="text-xs font-mono tabular-nums font-medium mt-[5px]">
                  {String(filtered.length - id).padStart(2, "0")}.
                </span>
                <div className="flex flex-col gap-y-2 flex-1">
                  <p className="tracking-tight text-lg font-medium">
                    <span className="group-hover:text-foreground transition-colors">
                      {post.title}
                      <ChevronRight
                        className="ml-1 inline-block size-4 stroke-3 text-muted-foreground opacity-0 -translate-x-2 transition-all duration-200 group-hover:opacity-100 group-hover:translate-x-0"
                        aria-hidden
                      />
                    </span>
                  </p>
                  <p className="text-xs text-muted-foreground">
                    {post.publishedAt}
                    <span className="ml-2 border border-border rounded-md px-1.5 py-0.5">
                      {post.category}
                    </span>
                  </p>
                </div>
              </Link>
            </BlurFade>
          ))}
        </div>
      ) : (
        <div className="flex flex-col items-center justify-center py-12 px-4 border border-border rounded-xl">
          <p className="text-muted-foreground text-center">
            No blog posts yet. Check back soon!
          </p>
        </div>
      )}
    </>
  );
}
