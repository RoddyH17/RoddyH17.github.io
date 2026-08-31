---
title: "08 · Vec 与 HashMap 的实际用法"
pubDate: "2026-08-11"
author: "Roddy"
description: "一句话:两个容器,同一条访问规则——Vec::get 和 HashMap::get 都返回 Option,都逼你 match。「下标越界」和「查无此键」在类型上是同一件事。"
categories: ['rust']
series: 'rust'
order: 8
module: "标准库与工程组织"
draft: false
---

# 08 · Vec 与 HashMap 的实际用法

> 一句话:两个容器,同一条访问规则——`Vec::get` 和 `HashMap::get` 都返回 `Option`,都逼你 `match`。**「下标越界」和「查无此键」在类型上是同一件事。**

> 这一篇记的是标准库容器**怎么用**;它们内部怎么实现(拉链法、sift_up/down、负载因子)见 **基础数据结构手写实现**。

## 创建

```rust
let empty: Vec<i32> = Vec::new();   // 用 new 必须自己写类型 —— 一个元素都没有,无从推断
let v = vec![1, 2, 3, 4, 5];        // 用 vec! 宏就不用写
```

`push` 改变 Vec 本身,所以绑定得是 `mut`。

## 访问:索引 vs get

写法差别不重要,**越界时的差别才重要**:

```rust
let third: &i32 = &v[2];      // 直接索引:越界当场 panic,程序结束
match v.get(2) {              // get 返回 Option:没有就是 None,不会崩
    Some(n) => println!("{n}"),
    None => println!("没有这个下标"),
}
```

HashMap 一模一样:

```rust
match scores.get("green") {
    Some(s) => println!("{s}"),
    None => println!("没有 green 这个队"),
}
```

> **抽象断裂点｜两种「找不到」被统一成了同一个类型**
> 数组越界和字典缺键在直觉上是两件事:一个是「你算错了」,一个是「本来就可能没有」。C 里前者是未定义行为,后者要靠约定的哨兵值;Python 里前者是 `IndexError`,后者是 `KeyError`——两个不同的异常类。
> Rust 把它们都做成 `Option`,于是在类型层面**它们是同一件事**:一次可能没有结果的查找。这次统一的收益是调用方只需要学一套处理方式;代价是**两种失败的语义差别被抹掉了**——「下标 100 越界」通常意味着你的逻辑错了,「key 不存在」通常是正常业务分支,但 `None` 不区分。
> 这是取商的又一个实例(见 **渐进分析**):合并两个概念换来统一的接口,同时失去了区分它们的能力。判断这次合并划不划算的标准是:**丢掉的那个区别,后面还需不需要?** 这里通常不需要,所以是好交易;但要注意,当你确实需要区分「不该发生的缺失」和「正常的缺失」时,`Option` 本身不会提醒你。
> 索引 `v[i]` 保留下来的意义正在这里:它是一句断言——「我保证这个下标合法」,越界就该死。**同一个操作提供两种 API,其实是在让调用方声明自己的意图。**

## 遍历与修改

```rust
for i in &v { }                    // 借用
for i in &mut v { *i += 10; }      // 可变借用,要 * 解引用才能赋值
for i in v { }                     // 移动进循环,循环结束 v 就没了
```

三种形式的完整对照见 **借用、引用与 NLL**。HashMap 同样要写 `&`,而且**遍历顺序不保证**——每次运行都可能不一样,不要依赖它(这是抗 HashDoS 的随机化种子导致的,不是实现疏忽)。

## 用 enum 让一个 Vec 装多种类型

Vec 要求所有元素同一个类型。想混着装,就用一个 enum 把它们包成同一个类型:

```rust
enum SpreadsheetCell { Int(i32), Float(f64), Text(String) }

let row: Vec<SpreadsheetCell> = vec![
    SpreadsheetCell::Int(3),
    SpreadsheetCell::Float(10.12),
    SpreadsheetCell::Text(String::from("hello")),
];
```

类型统一了,取出来时再用 `match` 分派回去。

> 这是异构容器的**封闭解**:变体集合写死在 enum 里,加新类型要改定义。开放解是 `Vec<Box<dyn Trait>>`。两者是表达式问题的对偶,完整讨论见 **dyn 与 trait object**。

## capacity 不是 len

```rust
let mut v: Vec<i32> = Vec::with_capacity(10);
v.len()        // 0  —— 真正放了几个
v.capacity()   // 10 —— 已经要来的位置
```

容量不够时**成倍增长**:`with_capacity(3)` push 到第 4 个,capacity 变成 6。每次扩容都要重新分配 + 搬家,所以事先知道规模就 `with_capacity`。

这也是 **基础数据结构手写实现** 里「HashMap 的 O(1) 是摊还的」那条的来源:单次 push 可能是 O(n),但成倍增长让**平均**每次仍是 O(1)。

## HashMap:insert 拿走所有权

```rust
map.insert(field_name, field_value);
// println!("{field_name}");   // ✗ error[E0382] borrow of moved value
```

`insert` 收的是**值**不是引用。想两边都留着就先 `clone()`。

同一个 key 再 insert 就是覆盖——旧值没丢,而是从返回的 `Option` 里还给你:

```rust
let old = scores.insert(String::from("blue"), 25);   // Some(10)
```

> 这是 `mem::replace` 的同一个手法(见 **递归数据结构** 的 `take()`):**不销毁,交换。** 仿射类型没有「凭空复制」,只有「换出来」。

## entry API:合并两个 map 时最容易写错的地方

```rust
// 循环 insert:后来的盖掉先来的
for (k, v) in &map2 { merged.insert(*k, *v); }        // b 变成 3

// entry().or_insert():先来的不动,缺的才补
for (k, v) in &map2 { kept.entry(*k).or_insert(*v); } // b 保住 2,只补进来一个 c
```

**陷阱**:

```rust
kept.entry("d");   // 编译通过、没有警告、什么都不会发生
```

`entry()` 只是把「这个位置」交给你,不接 `or_insert` 就等于没动过。

> **抽象断裂点｜一个既无效果也无警告的调用**
> `entry("d")` 是一次纯粹的无操作:它不改变任何状态,不返回被使用的值,也不触发 `must_use` 警告。整个 Rust 生态对「静默失败」极为敏感——`Result` 必须处理、`#[must_use]` 到处都是、穷尽性检查是硬错误——而这里出现了一条缝。
> 缝的来源是:`Entry` 本身是一个**合法且有用的中间值**(你可能要 `match` 它、可能要 `and_modify`),所以不能一律标 `must_use`;但它作为语句被丢弃时又确实什么都没做。类型系统区分不了「这个中间值被合理地用于别处」和「它被扔了」。
> 和 **模式匹配全谱** 里守卫可达性只是警告一样,这又是**强保证系统的一条窄缝**:越是在别处保护周全,人在这类缝上越不设防。值得养成的习惯是,记住每个系统的保证边界清单,而不是笼统地相信它。
