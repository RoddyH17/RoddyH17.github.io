---
title: "02 · 借用、引用与 NLL"
pubDate: "2026-08-06"
author: "Roddy"
description: "一句话:读可以并发,写必须独占。 Rust 把这条读写锁的心智模型从运行时搬到了编译期,因此运行时零开销。"
categories: ['rust']
series: 'rust'
order: 2
module: "基础语法与内存"
layer: 'generated'
draft: false
---

# 02 · 借用、引用与 NLL

> 一句话:**读可以并发,写必须独占。** Rust 把这条读写锁的心智模型从运行时搬到了编译期,因此运行时零开销。

## 引用不是指针

引用是一个可以跟随的地址,但比指针多一条保证:**在引用存在的整个期间,它一定指向一个该类型的有效值**。这条保证不是运行时检查出来的,是编译器拒绝掉所有可能违反它的程序换来的。

```rust
fn calculate_length(s: &String) -> usize { s.len() }

let s1 = String::from("hello");
let len = calculate_length(&s1);   // 借用,不转移所有权
println!("{s1} 的长度是 {len}");   // s1 还在
```

创建引用这个动作叫 **borrowing**:你可以借,用完要还,期间东西不归你。

## 两条规则

> 1. 在任意时刻,要么有**一个**可变引用,要么有**任意多个**不可变引用——不能同时。
> 2. 引用必须始终有效。

第一条的理由是对称的:只读的人不影响彼此,所以可以并发;写的人会让别人手里的读作废,所以必须独占。

```rust
let mut s = String::from("hello");
let r1 = &s;      // ok
let r2 = &s;      // ok
// let r3 = &mut s;   // ✗ 与 r1/r2 的使用区间重叠
println!("{r1} {r2}");
```

> **抽象断裂点｜同一条不变式,三种执行位置**
> 「共享 + 可变 = 危险」这条规律在工程里到处都是,区别只在**谁来执行、什么时候执行**:
>
> - 运行时执行:`RwLock`、`RefCell`——违反了就阻塞或 panic
> - 编译期执行:Rust 的借用检查器——违反了就编译不过
> - 取消前提:OCaml / Haskell 砍掉 mutation,共享就自动安全(见 **Lecture 1 - What is a Functional Language**)
>
> 三条路线砍的是同一个连词的不同部分。值得记的是:**Rust 并没有发明这条规则,它只是把一个大家本来就在运行时遵守的纪律,提前到了编译期,并且强制执行。** `RefCell` 的存在恰好证明了这一点——当静态检查太保守时,你可以把同一条规则退回运行时执行,代价是可能 panic。

## Mutable Reference

```rust
fn change(s: &mut String) { s.push_str(", world"); }

let mut s = String::from("hello");
change(&mut s);
```

要拿 `&mut`,被借的绑定本身必须是 `mut`。这也是为什么 **struct、impl 与 self 的四种形态** 里「`mut` 修饰的是绑定,不是字段」——`&mut` 给出的是对**整个值**的独占访问,可变性的粒度不可能细过你交出去的那个引用。

## NLL:借用活到最后一次使用,不是活到大括号

```rust
let mut s = String::from("hello, ");

let r1 = &mut s;
r1.push_str("world");    // r1 最后一次被使用 → 生命周期到此结束

let r2 = &mut s;         // ✓ 两个 &mut 的使用区间不重叠
r2.push_str("!");
```

但只要在 `let r2` 之后再用一次 `r1`(哪怕只是 `println!("{r1}")`),两段区间立刻重叠:`cannot borrow s as mutable more than once at a time`。

这叫 **NLL(Non-Lexical Lifetimes)**,2018 edition 引入。之前借用活到词法作用域结束,很多显然安全的代码写不出来。

> **抽象断裂点｜语言的能力边界由实现定义,不由规范定义**
> NLL 之前和之后,Rust 的**语法没变、类型系统的规范没变**,但能写出来的程序集合变大了。**查找算法** 里那段 `while let Some(node) = cur { cur = &mut node.left; }` 就是 NLL 之后才合法的。
> 于是「Rust 能不能写 X」这个问题的答案取决于编译器版本。再往前看,Polonius(下一代借用检查器)还会再放宽一批。**这意味着借用检查器不是在判定「这段程序是否安全」,而是在判定「我当前能否证明它安全」——被拒绝的程序里,一部分是真的错,一部分只是暂时证不出来。**
> 这个区别在别处也成立:类型检查、静态分析、形式验证都是「可证明的安全」而不是「安全」的近似,而近似的精度会随实现演进。判定不可判定问题的工具,永远只能给出保守的一侧。

## 悬垂引用:编译期就被拒绝

```rust
fn dangle() -> &String {         // ✗ missing lifetime specifier
    let s = String::from("hello");
    &s                            // s 在函数结束时被 drop
}
```

C++ 里这是运行时才炸的经典坑;Rust 在编译期直接说:这个返回类型里含有一个借来的值,但没有任何东西可以借给它。

解法不是想办法延长 `s` 的寿命,而是**换一种归属**:

```rust
fn no_dangle() -> String {
    let s = String::from("hello");
    s                             // 所有权移交调用方,没有东西会在这里被释放
}
```

## 循环的三种形式就是三种借用

这是日常写代码最常撞的一组:

| 写法              | 展开成          | 每次拿到 | 循环后原变量                         |
| ----------------- | --------------- | -------- | ------------------------------------ |
| `for e in &v`     | `v.iter()`      | `&T`     | 可用                                 |
| `for e in &mut v` | `v.iter_mut()`  | `&mut T` | 可用,且已被修改                      |
| `for e in v`      | `v.into_iter()` | `T`      | `Vec`:**消耗**;数组:因 `Copy` 而保留 |

```rust
let mut v = vec![1, 2, 3];
for e in &mut v { if *e == 1 { *e = 5; } }   // 要 * 解引用才能写
println!("{v:?}");                            // [5, 2, 3],v 还在
```

`for e in &v` 和 `for e in v.iter()` 完全等价,前者只是语法糖。

> 数组在 Rust 1.53 之前 `for e in arr` 拿到的是引用,1.53 之后才改成按值。读老代码时会遇到这个差异。
