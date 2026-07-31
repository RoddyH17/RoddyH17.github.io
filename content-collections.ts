import { defineCollection, defineConfig } from "@content-collections/core";
import { compileMDX } from "@content-collections/mdx";
import remarkGfm from "remark-gfm";
import { z } from "zod";
import { remarkCodeMeta } from "./src/lib/remark-code-meta";

const posts = defineCollection({
    name: "posts",
    directory: "content",
    include: "**/*.mdx",
    schema: z.object({
        title: z.string(),
        publishedAt: z.string(),
        updatedAt: z.string().optional(),
        author: z.string().optional(),
        summary: z.string(),
        image: z.string().optional(),
        // 分类默认由目录决定 (content/<类别>/xxx.mdx);根目录文件可用此字段指定
        category: z.string().optional(),
        // 草稿:true 时不出现在列表页,也不生成页面
        draft: z.boolean().default(false),
        content: z.string(),
    }),
    transform: async (document, context) => {
        const mdx = await compileMDX(context, document, {
            remarkPlugins: [remarkGfm, remarkCodeMeta],
        });
        // content/rust_learn/day-1.mdx → category "rust_learn"
        const parts = document._meta.path.split("/");
        const category =
            parts.length > 1 ? parts[0] : (document.category ?? "misc");
        return {
        ...document,
            category,
            mdx,
        };
    },
});

export default defineConfig({
    collections: [posts],
});

