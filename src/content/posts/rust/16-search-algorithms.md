---
title: "16 · 查找算法"
pubDate: "2026-08-24"
author: "Roddy"
description: "前提条件(已排序)不在类型里,只能靠约定。"
categories: ['rust']
series: 'rust'
order: 16
module: "综合应用"
layer: 'generated'
draft: false
---

# 16 · 查找算法

## 二分查找

前提条件(已排序)**不在类型里**,只能靠约定。

> **抽象断裂点｜不变式的看守人是谁**
> 二分查找的正确性完全依赖「数组已排序」,而这个前提在 Rust 里没有任何承载者:类型是 `&[T]`,和未排序的切片一模一样。看守人是程序员的记忆。
> 这和 **基础数据结构手写实现** 里「签名即语义」正好构成对照:Rust 把大量约定搬进了类型,但**顺序性这类「关于值的性质」搬不进去**——类型系统管的是形状,不是内容。要管内容就得升级到依赖类型(把 `Sorted<T>` 做成只能由排序函数构造的 newtype,是穷人版的做法)。
> 值得长期记住的分界线:**类型能表达「这是什么」,很难表达「这满足什么」。** 每次你在注释里写下一个前提条件,就是在标记这条分界线的一个具体位置。

```rust
pub fn binary_search<T: Ord>(arr: &[T], target: &T) -> Option<usize> {
    let (mut lo, mut hi) = (0usize, arr.len());
    while lo < hi {
        let mid = lo + (hi - lo) / 2;    // 不写 (lo+hi)/2,防溢出
        match arr[mid].cmp(target) {
            Ordering::Equal   => return Some(mid),
            Ordering::Less    => lo = mid + 1,
            Ordering::Greater => hi = mid,
        }
    }
    None
}
```

**半开区间 `[lo, hi)` + `lo < hi`** 是最不容易写错边界的写法。

实战里 `lower_bound`(第一个 ≥ target 的位置)比 `binary_search` 更通用——它总有返回值,能直接做插入点、区间计数:

```rust
pub fn lower_bound<T: Ord>(arr: &[T], target: &T) -> usize {
    let (mut lo, mut hi) = (0usize, arr.len());
    while lo < hi {
        let mid = lo + (hi - lo) / 2;
        if arr[mid] < *target { lo = mid + 1; } else { hi = mid; }
    }
    lo
}
```

## BST 插入:`&mut` 在树上走

```rust
pub fn insert(&mut self, key: i32) {
    let mut cur = &mut self.root;
    while let Some(node) = cur {
        if key < node.key      { cur = &mut node.left; }
        else if key > node.key { cur = &mut node.right; }
        else                   { return; }
    }
    *cur = Some(Box::new(BstNode { key, left: None, right: None }));
}
```

⚠️ 这段能编译过不太显然:`cur` 是 `&mut Option<Box<BstNode>>`,每轮循环把它重新指向子节点,借用检查器要确认旧借用已失效。**NLL 之后才允许这么写。**

## 图上的三个查找 = 同一个骨架,只换容器

> **这是最值得记的一点。**

```
待访问集合用 Stack   → DFS        深度优先,判可达
待访问集合用 Queue   → BFS        边数最短路
待访问集合用 MinHeap → Dijkstra   带权最短路
```

> **抽象断裂点｜算法的身份在哪里**
> DFS、BFS、Dijkstra 有各自的名字、发明者和历史。但在这里它们是**同一段代码**,唯一差别是 frontier 用什么容器。如果算法可以这样被同一个骨架吸收,「三个算法」这个说法指的到底是三个对象,还是一个对象的三次参数化?
> 推下去会碰到一个更一般的现象:**很多学科的「概念清单」其实是同一结构在不同参数下的切片,只因为历史发现顺序不同而被分别命名。** 优先队列的比较函数取 $0$ / $1$ / $w$ 就得到三种搜索,A\* 只是把优先级换成 $d+h$。同理,**Lecture 1 - Axiomatizing Democratic Choice** 里 plurality / Borda / STV 也可以看成同一台「偏好压缩机」在不同信息保留策略下的实例。
> 这不是说命名是错的——名字保留了发现顺序和适用直觉,骨架不提供这些。但知道骨架之后,**记忆的单位应该从「三个算法」变成「一个骨架 + 三条排序策略」**。这既是短线复习效率的直接来源,也是长线上识别学科结构的入口。

```rust
// DFS
let mut stack = Stack::new();
stack.push(start);
while let Some(u) = stack.pop() { ... }

// BFS
q.push_back(start);
while let Some(u) = q.pop_front() { ... }

// Dijkstra —— 元组 (距离, 节点) 按字典序天然排好
heap.push((0u64, start));
while let Some((d, u)) = heap.pop() {
    if d > dist[u] { continue; }   // 过期条目直接跳过
    for &(v, w) in &adj[u] {
        let nd = d + w;
        if nd < dist[v] { dist[v] = nd; heap.push((nd, v)); }
    }
}
```

💡 Dijkstra 用自己写的 `MinHeap` 反而比标准库省事:`std::collections::BinaryHeap` 是**大顶堆**,用它得包一层 `Reverse(...)`。
