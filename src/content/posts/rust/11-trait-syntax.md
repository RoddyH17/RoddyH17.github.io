---
title: "11 · trait 语法"
pubDate: "2026-08-24"
author: "Roddy"
description: "trait = 一组方法签名 + 可选的默认实现。"
categories: ['rust']
series: 'rust'
order: 11
module: "抽象与内存表示进阶"
concept: "Trait"
layer: 'generated'
draft: false
---

# 11 · trait 语法

trait = **一组方法签名 + 可选的默认实现**。

## 完整声明语法

```rust
trait Animal {
    const LEGS: u32;              // 关联常量
    type Food: Debug;             // 关联类型(可带约束)

    fn name(&self) -> String;     // 必须实现(只有签名)
    fn eat(&self, f: Self::Food); // Self::Food 引用关联类型

    fn greet(&self) -> String {   // 默认方法,impl 里可省略
        format!("I am {} with {} legs", self.name(), Self::LEGS)
    }
}
```

## 实现

```rust
struct Cow;
impl Animal for Cow {
    const LEGS: u32 = 4;
    type Food = Grass;
    fn name(&self) -> String { "cow".into() }
    fn eat(&self, f: Grass) { println!("cow eats {:?}", f); }
    // greet 用默认的
}

struct Dog { tag: u8 }
impl Animal for Dog {
    const LEGS: u32 = 4;
    type Food = Meat;
    fn name(&self) -> String { format!("dog#{}", self.tag) }
    fn eat(&self, f: Meat) { println!("dog eats {:?}", f); }
    fn greet(&self) -> String { "woof".into() }   // 覆盖默认
}
```

## receiver 的四种形态

| 写法              | 含义                                   |
| ----------------- | -------------------------------------- |
| `fn f(&self)`     | 借用                                   |
| `fn f(&mut self)` | 可变借用                               |
| `fn f(self)`      | 消耗所有权                             |
| `fn f()`          | 关联函数,无 receiver(如 `Self::new()`) |

## supertrait

用冒号,表示「实现 Pet 前必须先实现 Animal」:

```rust
trait Pet: Animal {
    fn owner(&self) -> String;
}
```

## 约束的四种写法

```rust
fn f1<S: Shape>(s: &S) -> f64 { s.area() }        // 泛型参数上写
fn f2<S>(s: &S) -> f64 where S: Shape { ... }     // where 从句,复杂约束更清晰
fn f3(s: &impl Shape) -> f64 { ... }              // impl Trait 语法糖
fn f4(s: &dyn Shape) -> f64 { ... }               // ← 唯一一个动态分发
```

f1 / f2 / f3 完全等价,都是**单态化**(monomorphization)。f4 见 **dyn 与 trait object**。

## blanket impl

给所有满足某约束的类型统一实现:

```rust
impl<T: Shape> Describe for T {
    fn describe(&self) -> String { format!("<{}>", self.label()) }
}
// 现在 Circle、Square 自动都有 .describe()
```

标准库里 `impl<T: Display> ToString for T` 就是这么来的。

> **抽象断裂点｜impl 是全局资源**
> blanket impl 之所以成立,是因为 Rust 强制 **coherence**:任何 (trait, type) 对在整个程序里最多只能有一个 impl。这让 `.describe()` 在任何地方都指同一个东西,代价是 **orphan rule**——你不能给别人的类型实现别人的 trait,只能套一层 newtype。
> 注意这里的命名空间结构:类型和函数是**模块私有**的,可以重名;而 impl 是**全局**的,一个 crate 写下一个 impl,整个依赖图都要接受它。Rust 的模块系统里,唯一没有命名空间的东西就是 impl。
> 这是典型的「为了让局部推理成立,必须先引入一个全局不变式」。代价由谁承担?由生态里最后一个想扩展的人承担(newtype 样板)。同型的取舍在 **Lecture 1 - Axiomatizing Democratic Choice** 里叫 anonymity——为了让规则可证明,必须先规定某些差异不存在。

## 泛型 ≠ 参数化多态

⚠️ 重要事实:Rust 的泛型走 **monomorphization**,不是类型擦除。

`List<i32>` 和 `List<String>` 在代码生成后是**两个完全无关的类型**,各有布局、各有一份 `push` 的机器码。

后果:

- Rust 的 `∀` 在操作语义上**不是参数化的**(不满足 Reynolds parametricity 的表示无关性)
- 函数体行为依赖 `size_of::<T>()`、`align_of::<T>()`、`T` 的 drop glue
- 所以才需要 `?Sized` 这样的显式 bound
- 所以才需要 `dyn` 作为另一条路

> **抽象断裂点｜Rust 的 ∀ 不是 Reynolds 的 ∀**
> Reynolds 的抽象定理(1983)与 Wadler 的 _Theorems for Free!_(1989)说:在真正参数化的多态里,函数的类型**本身**就蕴含一批定理。`forall a. [a] -> [a]` 只能重排/删除/复制元素,不可能凭空造出元素、也不可能按元素内容做判断——因为它对 `a` 一无所知。类型免费送你一条自然性定理。
> 单态化取消了这个「一无所知」。Rust 的 `fn f<T>` 在代码生成后知道 `size_of::<T>()`、`align_of::<T>()`、`T` 的 drop glue,还能通过特化在不同 `T` 上走不同分支。**于是 Rust 的泛型是一个语法上的承诺,而不是一条语义定理。**
> 长线上要记的是这个区别的一般形式:_「我不知道你是谁」_ 与 _「我承诺不利用我知道的关于你的事」_ 是两种根本不同的保证。前者是结构性的(无知即保证),后者是规范性的(自律即保证)。密码学里这是信息论安全 vs 计算安全;制度设计里这是无知之幕 vs 利益冲突申报。**Haskell 走前一条,Rust 走后一条,两者的可靠性来源完全不同。**
