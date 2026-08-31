---
title: "06 · Match 模式匹配全谱"
pubDate: "2026-08-11"
author: "Roddy"
description: "一句话:match 真正的能力不是「代替 if-else」,而是按数据的结构分支。你描述你要找的形状,并给想取出来的部分起名字。"
categories: ['rust']
series: 'rust'
order: 6
module: "代数数据类型"
draft: false
---

# 06 · Match 模式匹配全谱

> 一句话:`match` 真正的能力不是「代替 if-else」,而是**按数据的结构分支**。你描述你要找的形状,并给想取出来的部分起名字。

## 穷尽性:编译器在替你数数

```rust
match pet {
    Pets::Cat => println!("is cat"),
    Pets::Dog => println!("is dog"),
    // 漏一个变体 = 编译错误,不是悄悄掉下去
}
```

这是 **enum 与和类型** 里余积泛性质的直接兑现:要定义一个从和类型出发的函数,**必须为每一支都给出说法**。

## 陷阱一:模式里的小写标识符是绑定,不是比较

```rust
let num = 1;
match num {
    o => {}    // ← 匹配一切,等于一个带名字的 _
    1 => {}    // warning: unreachable pattern
    _ => {}    // warning: unreachable pattern
}
```

编译器说得很直白:`o` _matches any value_,`1` — _no value can reach this_。

这也解释了为什么 `i32` 这种开放类型必须用 `_` 兜底:你不可能穷举 42 亿个分支。

同样的原因让下面这行报 _irrefutable `if let` pattern_:

```rust
if let cat = Pets::Cat { }     // ❌ cat 是绑定,恒真,if 成了摆设
if let Pets::Cat = pet { }     // ✅ 可证伪
```

`if let` 的意义正是「我只关心其中一种情况」,所以模式**必须有失败的可能**。

## 模式的形态

**字面量**:数字和 `&str` 都能直接匹配。

**`@` 绑定**:既检查模式,又把完整值绑到左边。在裸字面量上没什么用(你已经知道它是 42),配合**范围**才见价值——模式匹配的是一个集合,而你仍然想拿到具体那个值:

```rust
match x {
    n @ 1..=10 => println!("{n} 在 1 到 10 之间"),
    _ => {}
}
```

`@` 还能嵌套,绑定**整个变体**:

```rust
match Message::Number(8) {
    whole @ Message::Number(1..=10) => println!("{whole:?}"),   // whole 是整个 Message
    _ => {}
}
```

**结构体解构**:绑定和字面量可以混在同一个模式里。

```rust
match p {
    Point { x, y: 0 } => println!("on the x axis at {x}"),   // y: 0 是测试,x 是绑定
    Point { x: 0, y } => println!("on the y axis at {y}"),
    Point { x, y }    => println!("{x}, {y}"),
}
```

**守卫 guard**:当你关心的东西无法表达成一个形状时用它。

```rust
match x {
    n if n % 2 == 0 => println!("Even"),
    _ => println!("Odd"),
}
```

## 陷阱二:守卫分支的顺序(最危险的一条)

```rust
match &order.status {
    OrderStatus::Filled { execution_price, .. } => format!("成交 @ {execution_price}"),
    OrderStatus::Filled { execution_price, quantity } if *quantity >= 100.0 =>
        format!("大额成交 @ {execution_price}"),      // ← 永远不会触发
}
```

`match` 自上而下,第一个匹配上的赢。不带守卫的 `Filled` 已经把所有情况吃掉了。

```
warning: unreachable pattern
  `OrderStatus::Filled { .. }` matches all the relevant values
```

**是警告,不是错误。** 能编译、能运行,只是每一笔大额成交都被静默报成普通成交。

> **抽象断裂点｜穷尽性检查有一条它自己看不见的边界**
> 穷尽性是 Rust 最引以为傲的静态保证之一:漏一个变体是硬错误。但**分支之间的可达性**只是警告。
> 差别在哪?「所有变体都被覆盖」是一个关于**类型**的判断,编译器完全知道;「这条分支永远不会被走到」是一个关于**值和条件**的判断,一旦掺进守卫就变成了任意谓词的可满足性问题——不可判定。编译器只能在守卫不参与的情况下给出保守的警告。
> 于是产生了一个很难察觉的失败模式:**在一个以「不可能漏掉情况」著称的系统里,你仍然可以静默地漏掉情况。** 而且正因为周围的保证太强,人会放松警惕——这比在一个到处都要小心的语言里更危险。
> 长线上的问法:**一套强保证系统的真正风险,是否恰好集中在它保证不到的那条窄缝上?** 同型现象在 **基础数据结构手写实现** 里是「类型能强制你提供 `Hash`+`Eq`,不能强制它们一致」,在 **查找算法** 里是「已排序」无处安放。**记住保证的边界,比记住保证本身更重要。**
>
> 实践规则很简单:**守卫要放在更宽泛的分支上面。**

## `ref` / `ref mut`:在模式里借用而不是移动

匹配一个 `String` 会把它移走:

```rust
let x = String::from("Hello");
match x {
    var => println!("{var}"),    // x 被移进 var,之后不能再用
}
```

想借用:

```rust
match x {
    ref var => println!("{var}"),        // var 是 &String
}

let mut x = String::from("Hello");
match x {
    ref mut var => { *var = String::from("world"); }   // 真的写回去了
}
```

真正用得上的场景:你只有一个 `&mut`,却想改到 enum 变体**里面**的字段。直接解构会得到:

```
error[E0507]: cannot move out of `self.status.reason` as enum variant `Canceled`
              which is behind a mutable reference
```

> 注意这和 **struct、impl 与 self 的四种形态** 里 `..user1` 的部分移动**不是同一个错误**:那个是 `E0382`(用了已经移走的值),这个是 `E0507`(想从借用后面移出去)。修法也不同——不是 `clone`,而是在模式里借用。
> 现代 Rust 也可以写 `match &mut self.status { .. }`,**match ergonomics** 会自动把绑定变成可变引用。两种都对;`ref` 是在 match ergonomics 出现之前唯一的写法。

## `if let` / `while let`

只关心一种情况时,完整的 `match` 是多余的仪式。

```rust
if let Some(x) = opt { println!("{x}"); }

while let Some(x) = v.pop() { }     // 最该记住的搭配
```

`while let Some(x) = v.pop()` 好在:`pop` 返回 `Option`,集合空了循环自然结束,**不需要长度检查,也不需要索引**——把一个手工维护的不变式交给了类型。

## 穷尽性一路延伸到数据边界

serde 默认是 **externally tagged**:`Pending` 序列化成裸字符串 `"Pending"`,`Filled` 套一层 `{"Filled": {..}}`。

这正是 **enum 与和类型** 里内存布局中的**那个 tag**——在内存里它是一个字节,在 JSON 里它是一个 key。喂进 `"side":"Hold"` 会报 `unknown variant`:`match` 不许漏掉变体,serde 不许外部数据编造一个不存在的变体。同一条纪律从内存一直延伸到 IO 边界。

## match 的实际用武之地

处理错误、解析命令行参数、解析配置文件与数据包。共同点都是**拿到一坨结构未知的数据,按结构分支**。
