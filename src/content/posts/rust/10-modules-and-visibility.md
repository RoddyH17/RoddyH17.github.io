---
title: "10 · 模块、可见性与 workspace"
pubDate: "2026-08-13"
author: "Roddy"
description: "一句话:模块把代码切开,pub 决定切口开多大。默认全部私有——这是 Rust 的立场:不主动公开的东西,就是实现细节。"
categories: ['rust']
series: 'rust'
order: 10
module: "标准库与工程组织"
draft: false
---

# 10 · 模块、可见性与 workspace

> 一句话:模块把代码切开,`pub` 决定切口开多大。**默认全部私有**——这是 Rust 的立场:不主动公开的东西,就是实现细节。

## 三个层级各是什么单位

|             | 是什么的单位       | 由谁定义                               |
| ----------- | ------------------ | -------------------------------------- |
| **Package** | cargo 管理的单位   | 一个 `Cargo.toml`                      |
| **Crate**   | **编译**的单位     | 一个 binary crate 或一个 library crate |
| **Module**  | **命名空间**的单位 | `mod` 关键字                           |

每个 package 至少包含一个 crate。`cargo new --lib xxx` 建一个 lib package。

关键区别:**模块不产生新文件,也不产生新编译单元**,它只划分命名空间。写在一个文件里和拆成多个文件,对编译器是一回事——文件拆分纯粹是给人看的。

## 默认私有

```rust
mod visibility {
    pub fn open() { }
    fn closed() { }        // 没有 pub,模块外面看不见
}

visibility::open();
// visibility::closed();   // error[E0603]: function `closed` is private
```

不写 `pub` 的东西不是「忘了写」,是**明确表示它是实现细节**。

> **抽象断裂点｜默认值就是立场**
> 「默认私有」和「默认公开」在技术上完全对称,选哪个纯粹是设计判断。Java 的包级默认可见、Python 的「全都公开,靠 `_` 前缀约定」、Go 的按首字母大小写——四种语言四种答案。
> 选择的后果不在语法上,在**演化上**:默认私有意味着「公开」是一次需要动手的决定,于是 API 表面积默认最小,后续可以自由重构内部;默认公开意味着任何一次内部改动都可能是 breaking change,因为你不知道谁在依赖什么。
> 这和 **Box 与 DST** 里 `?Sized` 的方向性是**同一条**:`Sized` 默认封闭、`?Sized` 是例外语法。两处都是「先关上,要开口自己申请」。而 Rust 在这两处的一致性说明这不是巧合,是一套贯穿的哲学——**把编译器原本要替你猜的东西变成你必须写下来的东西**(见 **trait 语法**)。
> 长线上的问法:**任何系统的默认值都在决定「谁需要为改变现状付出成本」。** opt-in 与 opt-out 的器官捐献率、隐私设置的默认勾选、法律里的推定条款——结构完全一样,而设计者往往没意识到自己在做一个分配决定。

## `pub` 的三种强度

```rust
pub fn everyone() { }            // 谁都能看
pub(crate) fn crate_only() { }   // 本 crate 内公开,别的 crate 看不到
pub(in crate::a) fn scoped() { } // 只在指定路径内公开
```

开口从大到小。`pub(crate)` 是写库时最常用的一个——「这是内部共享的,不是 API」。

## 路径:`::` 不是 `.`

```rust
crate::a::echo();   // 绝对路径:从 crate 根开始数
a::echo();          // 相对路径:从当前位置开始数
```

`.` 是**值查找**(方法调用、字段访问),`::` 是**命名空间查找**。`a.echo()` 是错的——`a` 是一个模块,不是一个值。这条和 **enum 与和类型** 里方法 vs 关联函数是同一条规则的两次出现。

`self::` 是当前模块,`super::` 是父模块:

```rust
mod b {
    use super::echo;      // 往上一层取名字
    fn echo_b() { self::helper(); }   // self:: 只是让「这是本模块的」更醒目
}
```

## `use` 拉的是名字,不是代码

```rust
use a::b::log;
log();                       // 不用再写 a::b::log()
```

`use` 把长路径的最后一截拉到当前作用域。**没有任何运行时开销,只是省了打字**——它不 include、不复制、不影响编译产物。

重名时用 `as` 改名,花括号合并只是省写:

```rust
use a::{b::log as log2, log as log_a};   // 等价于分开写两行
```

> **抽象断裂点｜`as` 的两个身份**
> `as` 在 `use` 里是**重命名**,在表达式里是**类型转换**:
>
> ```rust
> use a::log as log_a;              // 重命名
> let y = x as usize;               // 类型转换
> ```
>
> 同一个关键字,两件毫无关系的事。这不是 Rust 独有的毛病——`static` 在 C 里有三个含义,`&` 在 C++ 里有三个,`*` 在 Rust 里有两个(解引用、裸指针)。
> 关键字复用的理由通常是「关键字是稀缺资源,加新词会破坏向后兼容(所有把它当标识符的旧代码都会挂)」。也就是说:**语言的词汇表是一次性预算,早期花掉的额度决定了后期的表达空间。** 于是成熟语言的语法总是越来越像考古地层。
> 这条和 **struct、impl 与 self 的四种形态** 里 `mut self` vs `&mut self` 是同一类问题的两个方向:一个是同形不同义(复用),一个是形近义远(相似)。两者都让**语法距离与语义距离脱钩**,而人的直觉恰恰依赖这个耦合。

## 比 private 更小的开口

函数里也能定义函数和模块:

```rust
fn main() {
    fn add(a: usize, b: usize) -> usize { a + b }   // 作用域只有 main
    println!("{}", add(1, 2));
}
```

这是「最小可见性」的极端形态——连模块都不用建,直接把辅助函数关在函数里。

## workspace:切 crate 之间

模块管一个 crate **内部**的切分,workspace 管多个 crate **之间**的切分:

```toml
# 根 Cargo.toml
[workspace]
members = [
  "crates/core",
  "crates/engine"
]

# crates/engine/Cargo.toml
[dependencies]
core = { path = "../core" }
```

前者靠 `pub` 控制开口,后者靠 `Cargo.toml` 的 `dependencies` 控制**谁能依赖谁**。两者是同一件事在两个尺度上的实现:**依赖关系的显式化**。workspace 还有一个实际好处——共享 `target/` 和 lockfile,编译更快。
