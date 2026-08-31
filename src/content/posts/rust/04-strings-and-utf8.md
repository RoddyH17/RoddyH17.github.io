---
title: "04 · 字符串与 UTF-8 编码"
pubDate: "2026-08-07"
author: "Roddy"
description: "一句话:Rust 里没有「字符串」这一种东西,有的是三种归属不同的字节视图。而 UTF-8 让「第 n 个字符」这个直觉失去意义。"
categories: ['rust']
series: 'rust'
order: 4
module: "复合数据与编码"
layer: 'generated'
draft: false
---

# 04 · 字符串与 UTF-8 编码

> 一句话:Rust 里没有「字符串」这一种东西,有的是**三种归属不同的字节视图**。而 UTF-8 让「第 n 个字符」这个直觉失去意义。

## 三种字符串类型

|          | `&'static str`   | `String`           | `&str`(借来的)          |
| -------- | ---------------- | ------------------ | ----------------------- |
| 来源     | 字面量 `"hello"` | `String::from(..)` | `&s[..]` / `s.as_str()` |
| 数据在哪 | 可执行文件只读区 | 堆                 | 指向上面任意一种        |
| 栈上结构 | ptr + len        | ptr + len + cap    | ptr + len               |
| 拥有数据 | 否               | 是                 | 否                      |
| 能否增长 | 否               | 是                 | 否                      |

`String` 的定义本质上是:

```rust
pub struct String { vec: Vec<u8> }
```

它拥有并管理一串 `u8`,并**额外保证这些字节一定是合法 UTF-8**。这条保证是 `String` 与 `Vec<u8>` 唯一的区别——任意字节数组不一定是合法文字:

```rust
let random: [u8; 3] = [255, 0, 128];   // 合法字节,非法 UTF-8
```

## 字节、字符与「第 n 个」

```rust
let s = String::from("你");
println!("{:?}", s.as_bytes());   // [228, 189, 160] —— UTF-8 编码 E4 BD A0
```

一个中文字符占 3 字节,ASCII 占 1 字节,emoji 可能占 4 字节。于是:

```rust
let s = String::from("你好");
// 字节下标: 0    1    2    3    4    5
// 字节内容: E4   BD   A0   E5   A5   BD
//           └─── 你 ───┘  └─── 好 ───┘

&s[0..3]    // "你" ✓
&s[0..2]    // panic! 切断了 UTF-8 编码
s.len()     // 6 —— 字节数,不是字符数
s.chars().count()   // 2 —— 这才是字符数
```

Rust **根本不提供** `s[0]`:因为它无法在「第 0 个字节」和「第 0 个字符」之间给出一个不撒谎的答案。

而 `char` 是另一回事——它是一个 Unicode 标量值,**固定 4 字节**:

```rust
std::mem::size_of::<char>()   // 4
```

所以 `char` 和「字符串里的一个字符」大小不一致:前者是解码后的定长表示,后者是编码中的 1–4 字节。

> **抽象断裂点｜「第 n 个字符」是一个不存在的操作**
> `s[0]` 在 C、Python、JS 里都能写,但三种语言给的东西不一样:C 给字节,Python 3 给码点,JS 给 UTF-16 码元(所以 emoji 的 `.length` 是 2)。**它们不是对同一个操作的不同实现,而是三种语言各自选了一层抽象并假装那就是「字符」。**
> Rust 的选择是拒绝提供这个操作,强迫你说清楚要哪一层:`.bytes()` / `.chars()` / `.grapheme_clusters()`(需要外部 crate)。代价是写中文处理时更啰嗦,收益是不会写出在英文测试通过、上线遇到用户名就崩的代码。
> 再往下还有一层:即使是 `char`(码点)也不等于人眼看到的「一个字」——`é` 可以是一个码点,也可以是 `e` + 组合重音两个码点;家庭 emoji 是好几个码点用零宽连接符粘起来的。**「一个字符」这个日常概念在形式层面根本没有唯一所指。**
> 这是本学期最干净的一个例子,说明**日常直觉里浑然一体的东西,形式化之后会分裂成一个层级栈,而每一层都能自称是「那个」东西。** 同型的分裂在 **Lecture 1 - Axiomatizing Democratic Choice** 里叫「什么算一次偏好」,在 **Lecture 1 - Observation, Cognition, and Social Evolution** 里叫「什么算一次文化传递」。

## String ↔ &str

```rust
fn say_hello(s: &str) { println!("hello, {s}"); }

let s = String::from("hello world");
say_hello(&s);          // &String → &str,deref coercion 自动发生
say_hello(&s[..]);      // 显式切片,必须落在 UTF-8 边界
say_hello(s.as_str());  // 直接返回自身的 &str
say_hello("literal");   // 字面量本身就是 &str

let back: String = "hello".to_string();   // 反向要在堆上重新分配,更贵
```

**函数参数一律写 `&str`,不要写 `&String`。** 签名写 `&str` 之后,同一个函数同时接受 `String`、切片和字面量;写 `&String` 则把字面量挡在外面。这是 deref coercion 存在的主要理由。

## 拼接

```rust
let s1 = String::from("hello");
let s2 = String::from(" world");
let r = s1 + &s2;        // s1 被 move 走,之后不能再用;第二个参数必须是 &str

let s3 = format!("{}, {}", r, s2);   // 不拿走任何一方的所有权
```

`+` 用的是 `impl Add<&str> for String`——它**接管**左边的 `String` 并在原有 buffer 上追加,所以不需要重新分配,代价是左边的所有权。`format!` 什么都不拿,代价是新分配一块。

> 常见笔误:`format!("{}, {}, s1, s2")` 是错的,变量必须作为参数传进去,不能写在字面量里。
