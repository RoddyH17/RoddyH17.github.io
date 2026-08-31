---
title: "13 · 递归数据结构"
pubDate: "2026-08-24"
author: "Roddy"
description: "设 s = size_of::<Expr>(),编译器要解:"
categories: ['rust']
series: 'rust'
order: 13
module: "抽象与内存表示进阶"
layer: 'generated'
draft: false
---

# 13 · 递归数据结构

## 问题:大小方程无解

```rust
enum Expr {
    Lit(i64),
    Add(Expr, Expr),   // ✗ error[E0072]: recursive type has infinite size
}
```

设 `s = size_of::<Expr>()`,编译器要解:

$$s = \max(8,\ s + s) + \text{tag} = \infty$$

ℕ 上无解。

## 解法:Box 把递归位固定成常数

```rust
enum Expr {
    Lit(i64),
    Add(Box<Expr>, Box<Expr>),
    Neg(Box<Expr>),
}
```

$$s = \max(8,\ 8+8) + \text{tag} = 16 + 8 = 24$$

```rust
size_of::<Expr>()  // 24 ✓
```

**关键点:`Box` 只加在递归出现的位置**,`Lit(i64)` 不需要装箱。

> **抽象断裂点｜Box 是一个不动点算子**
> `s = s + s + tag` 在 ℕ 上无解,加了 `Box` 之后变成 `s = 8 + 8 + tag`,方程突然可解。这里发生的不是「变小了」,而是**递归被截断成了一次间接**:类型层面的 $\mu X.\,\mathbb{Z}+X\times X+X$ 是无穷展开的,`Box` 给它配了一对 fold/unfold——写 `Box::new` 是 fold,deref coercion 是 unfold。
> 这正是不动点在别处的做法:不求出无穷对象本身,而是给出一个**有限的、可反复展开的表示**。同一个动作在 **Box 与 DST** 里是「把缺失的静态信息压成常数」,在 Y 组合子里是「把递归函数写成非递归函数的不动点」,在惰性求值里是「无穷列表用一个 thunk 表示」。
> 短线上你只需要记住「递归 enum 要装箱」;长线上值得记住的是:**指针是「延迟」的物化。** 凡是需要把无穷或未知推后处理的地方,最后都会长出某种形式的指针。

## 使用:deref 强转让 Box 变透明

```rust
let e = Expr::Neg(Box::new(Expr::Add(
    Box::new(Expr::Lit(2)),
    Box::new(Expr::Lit(3)),
)));

fn eval(e: &Expr) -> i64 {
    match e {
        Expr::Lit(n)    => *n,                  // n: &i64
        Expr::Add(l, r) => eval(l) + eval(r),   // l: &Box<Expr> 自动 deref 成 &Expr
        Expr::Neg(x)    => -eval(x),
    }
}
// eval(&e) == -5
```

`eval(l)` 能直接传是因为 **deref coercion**:`&Box<Expr>` → `&Expr` 自动发生。

## 链表:Option<Box<T>> 的形状

```rust
pub struct LinkedList<T> { head: Option<Box<Node<T>>>, len: usize }
struct Node<T> { elem: T, next: Option<Box<Node<T>>> }
```

- `Box` → 让递归类型有确定大小
- `Option` → 提供 `None` 作为链尾
- niche 优化 → 两者加起来还是 8 字节,不多花一个字节(见 **Box 与 DST**)

## 坑一:必须用 `take()`

```rust
pub fn push_front(&mut self, elem: T) {
    self.head = Some(Box::new(Node {
        elem,
        next: self.head.take(),   // 取走旧 head,原地留下 None
    }));
}
```

不能写 `next: self.head` —— 那是从 `&mut self` 后面把值搬走,会让 `self` 处于**部分未初始化**状态。

`take()`(= `mem::replace(&mut x, None)`)做的是**交换**不是复制:同一瞬间取走旧值、填入 `None`,不变式全程成立。

> 这是所有权仿射性的直接后果:没有 `Δ: A → A ⊗ A`,只有交换。
> C 里的 `new->next = head` 在 Rust 里**必须**写成这个形式。

反转链表也是同一手法:

```rust
pub fn reverse(&mut self) {
    let mut prev = None;
    let mut cur = self.head.take();
    while let Some(mut node) = cur {
        cur = node.next.take();   // 先摘下 next
        node.next = prev;         // 再改指向
        prev = Some(node);
    }
    self.head = prev;
}
```

## 坑二:必须手写 Drop

默认析构是**递归**的,十万节点会爆栈:

```rust
impl<T> Drop for LinkedList<T> {
    fn drop(&mut self) {
        let mut cur = self.head.take();
        while let Some(mut node) = cur { cur = node.next.take(); }
    }
}
```

> 类型层面的 μ 是无穷深的,栈是有限的。

> **抽象断裂点｜形式的无穷与执行的有限**
> 默认 `Drop` 是递归的,十万节点会爆栈——爆的是**调用栈**,不是那条链表。类型层面的 μ 没有深度限制,运行它的机器有。
> 这条裂缝不是 Rust 的缺陷,它是所有「形式对象 / 物理执行」二元结构的常驻居民:ℕ 上的归纳法不受限,for 循环受限于时间;图灵机的纸带是无穷的,你的内存不是;**渐进分析** 里 $n\to\infty$ 的极限在任何真实系统上都不存在。
> 手写 `Drop` 把递归改成迭代,做的正是**把深度从栈搬到堆**——又一次「信息换位置」。注意它和上面 `Box` 那一节是**反向**的同一个动作:`Box` 把无穷展开压进一次间接,手写 `Drop` 把一次间接重新摊平成循环。

## 为什么 Rust 里链表「难写」

所有权关系是一棵**森林**:每个值恰好一个所有者。单链表恰好是退化的树,所以能写。但:

- 双向链表 ✗(每个节点被两个指针指向)
- 图 ✗
- 带父指针的树 ✗

不是做不到,而是**强迫你显式选择别名语义**:

| 方案                 | 代价                                        |
| -------------------- | ------------------------------------------- |
| `Rc<RefCell<T>>`     | 运行时引用计数 + 运行时借用检查,环会泄漏    |
| `Weak<T>` 打破环     | 需人工判定哪条边非拥有                      |
| arena + `usize` 索引 | 失去指针类型安全,**但把指针图物化成了数据** |
| `unsafe` + 裸指针    | 不变式退回人脑                              |
