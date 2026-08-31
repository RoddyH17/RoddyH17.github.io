---
title: "05 · enum 与和类型"
pubDate: "2026-08-10"
author: "Roddy"
description: "一句话:C / TS 的 enum 是整数的别名,Rust 的 enum 是和类型——每个变体可以带自己的载荷。正因为如此,Option 和 Result 只是普通的库类型,而不是语言特性。"
categories: ['rust']
series: 'rust'
order: 5
module: "代数数据类型"
draft: false
---

# 05 · enum 与和类型

> 一句话:C / TS 的 enum 是**整数的别名**,Rust 的 enum 是**和类型**——每个变体可以带自己的载荷。正因为如此,`Option` 和 `Result` 只是普通的库类型,而不是语言特性。

## struct 是 AND,enum 是 OR

|          | 表达                                | 描述的是               |
| -------- | ----------------------------------- | ---------------------- |
| `struct` | **同时拥有**这些东西(积类型,AND)    | 一个对象由什么组成     |
| `enum`   | **只能是**这些可能性之一(和类型,OR) | 一个值可能处于哪种情况 |

```rust
enum OrderStatus {
    Pending,
    Filled { execution_price: f64, quantity: f64 },
    Canceled { reason: String },
}
```

一个订单恰好处于其中一种状态,每种情况携带的数据还不一样。这里根本没有布尔值可以测——问题不是「成交了吗」,而是「到底是哪一种,以及它带了什么」。

> **抽象断裂点｜代数数据类型的「代数」不是修辞**
> 类型的数量真的可以做算术:`|A × B| = |A| · |B|`(struct 是乘法),`|A + B| = |A| + |B|`(enum 是加法)。`Option<T>` 的基数是 `|T| + 1`,`Result<T, E>` 是 `|T| + |E|`,`bool` 就是 `1 + 1`,空 enum 是 `0`,单元 struct 是 `1`。
> 这套算术不是巧合。它来自范畴论里的积与余积——`struct` 是积对象(带两个投影 `.0` `.1`),`enum` 是余积对象(带两个注入 `Some` / `None`),而 `match` 正是余积的**泛性质**:给出每一支怎么处理,就唯一确定了整体怎么处理。
> 短线上你只需要会写 `enum`;长线上要记住的是:**「一个东西可能是这几种情况之一」这件事有一个精确的数学身份,而不只是一种编程写法。** 同一个结构在 **Lecture 1 - Relations and Countability** 里是集合的不交并,在逻辑里是析取,在数据库里是多态关联表——三处的困难点(怎么保证穷尽、怎么保证互斥)完全一样。

## 变体的三种形态

```rust
#[derive(Debug)]
enum Pets {
    Cat(String),                        // 元组变体
    Dog { names: String, ages: usize }, // 结构体变体
    Bird,                               // 单元变体
}
```

三种可以混在同一个 enum 里。

**陷阱:元组变体的裸路径是构造函数,不是值。**

```rust
let cat = Pets::Cat;   // 编译通过!但 cat 的类型是 fn(String) -> Pets
let cat = Pets::Cat("Tom".to_string());   // 这才是一只猫
```

只有单元变体(`Pets::Bird`)的裸路径本身就是值,因为它没有需要补的参数。这条在写 `.map(Pets::Cat)` 这类代码时反过来变成好事——构造器可以当函数传。

## 方法 vs 关联函数

差别只在**有没有 `self`**:

```rust
impl Pets {
    fn speak(&self) { }            // 方法:属于值,用 . 调用
    fn log(name: String) { }       // 关联函数:属于类型,用 :: 调用
}

dog.speak();                       // 值查找
Pets::log("alen".to_string());     // 命名空间查找
```

`::` 是命名空间查找,`.` 是值查找。Rust 里的「构造函数」(`String::from`、`Vec::new`)其实只是约定俗成的关联函数——这就是为什么写 `::new()` 而不是 `.new()`。`impl` 挂行为时并不关心类型是 struct 还是 enum,见 **struct、impl 与 self 的四种形态**。

## `#[derive(..)]` 是编译期代码生成

`derive` 是一个**过程宏**:编译时,编译器把类型定义的语法树(TokenStream)交给宏,宏返回一段新代码拼回源码。

```rust
#[derive(Debug, Clone, PartialEq)]
struct Point { x: i32, y: i32 }
// 等价于手写了三个 impl 块
```

纯编译期,**零运行时开销**,生成的代码和手写的完全一样。所以 `{:?}` 需要 `Debug`、`==` 需要 `PartialEq`——不是「默认就有」,而是「有一行就能要来」。

## 内存布局:tagged union

内存 = 判别标签(discriminant tag) + 最大变体的载荷 + 对齐填充。

| enum                           | size      | 原因                                  |
| ------------------------------ | --------- | ------------------------------------- |
| `enum A { a, b, c }`           | 1         | 只有 tag,三种情况一个字节装得下       |
| `enum One { A = 255 }`         | **0**     | 只有一个变体 → ZST,即便显式写了判别式 |
| `enum Never {}`                | 0         | 根本不存在任何值                      |
| `enum Mixed { A(u8), B(u32) }` | 8,align 4 | **不是 5** —— `u32` 强制对齐产生填充  |

```
Mixed 的布局
偏移:  0        1  2  3        4  5  6  7
      [ tag ] [ 3 字节填充 ] [    u32     ]
```

零字节那一条值得多想:只有一个变体的无载荷 enum 是 **ZST**,把判别式钉死成 `255` 也不改变这一点。原因很直白——这个类型只有一个可能的值,「值是什么」不携带任何信息,读出来只能是 `A`,所以不用存。

## niche optimization:标签有时是免费的

```rust
enum Big { A(String), B }
size_of::<Big>()            // 24 —— 恰好等于 size_of::<String>()
size_of::<Option<&i32>>()   // 8  —— 恰好等于 size_of::<&i32>()
```

看起来没地方放 tag,却都成立。这是 **niche optimization**:当载荷存在一个不可能出现的位模式时(`String` 里的指针永远非空),编译器就用那个位模式当标签。`Option<&T>` 同理——`None` **就是**空指针。

> **抽象断裂点｜安全没有换性能,换的是「谁被允许不检查」**
> 这一条把空指针那条线闭合了:`Option<&T>` 逐字节就是一个可空指针,和 C 会写出来的布局一模一样。唯一的区别是**编译器现在不允许你不检查就解引用**。
> 所以 Rust 在这里并没有拿运行时开销换安全——它换的是「你必须写出那次检查」。Tony Hoare 把空指针叫作自己的 billion-dollar mistake,而这个错误的修复方案在内存层面**什么都没改**,只改了类型层面。
> 长线上的问法:**有多少「历史遗留的危险设计」其实只需要一层类型包装就能修好,而不需要改动底层表示?** 反过来,有多少危险设计的根在表示本身,包装解决不了?这两类的比例决定了一门新语言能带来多大改进。
> niche 的另一面见 **Box 与 DST**:类型的不变式越强,可用的 niche 越多,编码就越省。
