---
title: "15 · 基础数据结构手写实现"
pubDate: "2026-08-24"
author: "Roddy"
description: "完整可运行代码见 ~/rust_learn/ 对应 day 目录。本篇只记 Rust 特有的那几个点。"
categories: ['rust']
series: 'rust'
order: 15
module: "综合应用"
draft: false
---

# 15 · 基础数据结构手写实现

> 完整可运行代码见 `~/rust_learn/` 对应 day 目录。本篇只记 **Rust 特有的那几个点**。

## Stack

底层直接用 `Vec`(尾部 push/pop 摊还 O(1))。

```rust
pub struct Stack<T> { items: Vec<T> }

impl<T> Stack<T> {
    pub fn push(&mut self, item: T) { self.items.push(item); }
    pub fn pop(&mut self) -> Option<T> { self.items.pop() }
    pub fn peek(&self) -> Option<&T> { self.items.last() }
}
```

**签名的差别就是语义**:

- `pop` → `Option<T>`,**所有权转移**出来
- `peek` → `Option<&T>`,只**借用**

C++ 里这是 `pop()` + `top()` 两个函数的事,Rust 用返回类型说清楚了。

> **抽象断裂点｜签名即语义**
> `pop -> Option<T>` 与 `peek -> Option<&T>` 的差别不在实现里,在**类型里**。C++ 必须把「改状态」和「读值」拆成两个函数,再在文档里解释为什么 `pop()` 不返回值(异常安全);Rust 用返回类型一次说完。
> 这是一次**从文档到类型的迁移**:原本靠人读注释、靠约定维持的东西,被搬进了编译器能检查的位置。整门 Rust 课都可以按这个迁移量来读——生命周期是把「这个引用什么时候失效」从注释搬进类型,`Send`/`Sync` 是把「这个对象能不能跨线程」从口头承诺搬进类型。
> 反过来的问题同样重要:**还有多少东西留在注释里?** 下一节二分查找的「数组已排序」就是一个,它没有任何类型承载。见 **查找算法**。

> ⚠️ 命名冲突:数据结构的 stack/heap ≠ 内存区域的栈/堆。栈是调用帧、编译期定长;堆是运行时分配,`Box`/`Vec` 用的那块。

## MinHeap(二叉堆)

数组隐式表示完全二叉树,不需要任何指针:

```
索引:  0    1    2    3    4    5
      [1]  [3]  [2]  [5]  [9]  [8]

parent(i) = (i-1)/2    left(i) = 2i+1    right(i) = 2i+2
```

```rust
pub fn push(&mut self, item: T) {
    self.data.push(item);
    let last = self.data.len() - 1;
    self.sift_up(last);              // O(log n) 上浮
}

pub fn pop(&mut self) -> Option<T> {
    if self.data.is_empty() { return None; }
    let last = self.data.len() - 1;
    self.data.swap(0, last);         // 堆顶与末尾换位
    let top = self.data.pop();       // 弹末尾 = O(1)
    if !self.data.is_empty() { self.sift_down(0); }
    top
}
```

两个要点:

1. **`swap` 再 `pop`**:直接 `remove(0)` 是 O(n)(要挪整个数组)
2. **`Vec::swap` 不需要 `T: Clone`** —— 内部是位交换,符合所有权的仿射性

`heapify`(从 `n/2-1` 倒着 sift_down)建堆是 **O(n)**,比逐个 push 的 O(n log n) 快。

## LinkedList

见 **递归数据结构** —— `Option<Box<Node<T>>>` 的形状、`take()` 手法、手写 `Drop`。

## HashMap(拉链法)

```rust
pub struct MyHashMap<K, V> {
    buckets: Vec<Vec<(K, V)>>,   // 每个桶是一条链
    len: usize,
}
```

**哈希**:

```rust
fn hash_to(key: &K, n_buckets: usize) -> usize {
    let mut hasher = DefaultHasher::new();   // SipHash 1-3
    key.hash(&mut hasher);
    (hasher.finish() as usize) % n_buckets
}
```

**插入**——先查同 key 覆盖,`mem::replace` 拿回旧值(跟 `take` 同一个函数,只是填的不是 `None`):

```rust
for (k, v) in self.buckets[idx].iter_mut() {
    if *k == key { return Some(std::mem::replace(v, value)); }
}
self.buckets[idx].push((key, value));
```

**扩容**——负载因子 > 0.75 就翻倍 + 全量 rehash。这是 O(1) 的**前提**:桶数与元素数同阶增长,平均链长才是常数。

> 实测:100 个元素 → 256 个桶,最长链只有 3。

> **抽象断裂点｜O(1) 是一句有前提的承诺**
> HashMap 的 O(1) 依赖三件事:负载因子被维持在常数、哈希把 key 打散得足够均匀、`Hash` 与 `Eq` 的实现互相一致(相等的 key 必须哈希相同)。前两条是运行时策略,第三条是**用户可以违反的契约**——类型系统能强制你提供 `Hash` 和 `Eq`,不能强制它们一致。违反了不会 UB,只会让 HashMap 悄悄行为错乱。
> 于是同一张复杂度表里,`O(1) 平均` 和 BST 的 `O(log n)` **认识论地位并不相同**:后者是结构定理,前者是概率陈述加一组隐藏前提。表格把它们排在同一列,抹平了这个差别——这正是 **渐进分析** 里「取商」的代价在具体数据结构上的显形。
> 顺带一条选型时真正该问的问题:不是「哪个更快」,而是**「哪个的前提在我的场景里更容易被违反」**。

**约束 `K: Hash + Eq` 不是装饰**:

- 没有 `Hash` → 算不出桶号
- 没有 `Eq` → 无法在链上比较

所以 `f64` 不能直接当 key(`NaN != NaN`,只有 `PartialEq`)。

## 复杂度速查

| 操作     | Stack | MinHeap    | LinkedList | HashMap       | 有序数组 | BST           |
| -------- | ----- | ---------- | ---------- | ------------- | -------- | ------------- |
| 插入     | O(1)* | O(log n)   | O(1) 头部  | O(1) 平均     | O(n)     | O(log n) 平均 |
| 删除     | O(1)  | O(log n)   | O(1) 头部  | O(1) 平均     | O(n)     | O(log n) 平均 |
| 查找     | O(n)  | O(n)       | O(n)       | **O(1) 平均** | O(log n) | O(log n) 平均 |
| 取最小   | O(n)  | **O(1)**   | O(n)       | O(n)          | O(1)     | O(log n)      |
| 有序遍历 | —     | O(n log n) | —          | **不支持**    | O(n)     | O(n)          |

\* 摊还

**选型**:按 key 找 → HashMap;反复取最值 → Heap;要有序 → BST / 有序数组;只要 LIFO → Stack。

HashMap 查找最快,但**完全放弃了顺序**,这是它唯一的真实代价。

## LinkedList 的性能真相

```
Vec<T>:   [e0][e1][e2][e3]        一次分配,连续,预取器友好
List<T>:  [e0|p]→[e1|p]→[e2|p]   n 次分配,每步一次 cache miss
```

标准库的 `LinkedList` 文档自己就在劝退。真正需要它的场景:

- 持有元素引用的同时做 O(1) 拼接/移除(侵入式链表,内核常见)
- 教学载体(`Vec` 隐藏了所有权,链表把它全暴露出来)
