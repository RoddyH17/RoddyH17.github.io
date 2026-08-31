---
title: "14 · dyn 与 trait object"
pubDate: "2026-08-24"
author: "Roddy"
description: "泛型是 ∀,dyn 是 ∃。"
categories: ['rust']
series: 'rust'
order: 14
module: "抽象与内存表示进阶"
draft: false
---

# 14 · dyn 与 trait object

## 一句话

**泛型是 ∀,`dyn` 是 ∃。**

```rust
fn f<S: Shape>(s: &S)   // ∀S. Shape(S) ⟹ ...   调用方选类型
fn g(s: &dyn Shape)     // ∃S. Shape(S) ∧ ...   被调方选类型并隐藏它
```

不是类比,是字面上的实现关系。Mitchell & Plotkin,_Abstract Types Have Existential Type_(TOPLAS 1988):抽象数据类型 = 存在类型,而存在类型的标准实现就是「**隐藏的值 + 一张操作表**」的二元组。Rust 的 trait object 一字不差就是这个。

## dyn 是一个类型

`dyn Shape` 表示「某个实现了 Shape 的类型,但不告诉你是哪个」。它是 DST(见 **Box 与 DST**),永远要放在指针后面:

```rust
&dyn Shape        // 借用
&mut dyn Shape    // 可变借用
Box<dyn Shape>    // 拥有 + 堆分配
Rc<dyn Shape>     // 共享所有权
Arc<dyn Shape>    // 跨线程共享
```

> `dyn` 关键字是 2018 edition 引入的。以前直接写 `Box<Shape>`,跟泛型参数视觉上分不清。现在 `dyn` 强制显式标出「这里有一次虚调用」。

## 运行时表示

```
&dyn Shape  =  [ 数据指针 | vtable 指针 ]      16 字节

vtable(编译期生成,static,每个具体类型一份):
  ┌──────────────────┐
  │ drop_in_place    │  ← 类型被擦了,析构函数要随身带
  │ size             │  ← 类型被擦了,大小要随身带
  │ align            │
  │ area()           │  ← trait 方法
  │ label()          │
  └──────────────────┘
```

`drop` / `size` / `align` 出现在 vtable 里,正是因为具体类型擦除后这些信息没别的来源。

**擦除不免费——它把静态信息转成了运行时数据。** 这条直接呼应 **trait 语法** 里「单态化泛型依赖 T 的内在信息」那一点。

## dyn 能做而泛型做不到的:异构容器

```rust
let shapes: Vec<Box<dyn Shape>> = vec![
    Box::new(Circle { r: 1.0 }),
    Box::new(Square { s: 3.0 }),   // 不同类型,同一个 Vec
    Box::new(Circle { r: 0.5 }),
];
let total: f64 = shapes.iter().map(|s| s.area()).sum();
```

每个元素都是 16 字节,异构性被封在指针背后。写成 `Vec<S>` 做不到——单态化后 `S` 已固定成一个具体类型。

`Box::new(Circle{..})` → `Box<dyn Shape>` 是**自动的 unsize coercion**,只要目标类型标注了。有时要手动帮编译器:

```rust
let v = vec![Box::new(Circle{r:1.0}) as Box<dyn Shape>, Box::new(Square{s:2.0})];
```

## 语法细节

**① 关联类型必须写死**(否则 vtable 布局不确定):

```rust
let it: Box<dyn Iterator<Item = u32>> = Box::new((1..4).map(|x| x * 10));
// let bad: Box<dyn Iterator> = ...;   ✗ 缺 Item
```

**② 只能有一个非 auto trait,auto trait 可以叠加**:

```rust
Box<dyn Shape + Send + Sync>   // ✓ Send/Sync 无方法,不进 vtable
Box<dyn Shape + Debug>         // ✗ 两个 vtable 塞不进一个指针
```

想要多 trait 只能自己合并:`trait ShapeDebug: Shape + Debug {}`

**③ 生命周期界**:

```rust
Box<dyn Shape>        // 隐式 = Box<dyn Shape + 'static>
Box<dyn Shape + 'a>   // 允许装借用了 'a 数据的类型
&'a dyn Shape         // 隐式 = &'a (dyn Shape + 'a)
```

**④ 闭包也是 trait**,所以闭包的 dyn 形态极常见:

```rust
let ops: Vec<(&str, Box<dyn Fn(i32) -> i32>)> = vec![
    ("double", Box::new(|x| x * 2)),
    ("square", Box::new(|x| x * x)),
];
// 每个闭包都是不同的匿名类型,只有 dyn 能装进一个 Vec
```

**⑤ 错误处理里最常见的用法**:

```rust
Result<T, Box<dyn std::error::Error>>   // "某种错误,具体是啥调用方不用管"
```

## dyn compatibility(旧称 object safety)

```rust
trait Bad {
    fn clone_me(&self) -> Self;   // ✗ Self 大小未知,调用方接不住返回值
    fn generic<T>(&self, t: T);   // ✗ vtable 有限,不能给所有 T 预留槽位
    fn make() -> Self;            // ✗ 没有 self,无从查 vtable
}
```

规则不用背,从「具体类型已被擦除」直接推:

> **`Self` 只能出现在 receiver 位置**(那里有真实指针),不能出现在返回值或参数位置。

要返回 Self 就改成返回 `Box<dyn Trait>` —— 重新包一层,宽度就已知了。

有关联类型的 trait 要固定住才能 dyn 化:

```rust
fn cata_dyn(alg: &dyn ExprAlgebra<Carrier = i64>, e: &Expr) -> i64 { ... }  // ✓
```

## 五种多态形态全景

```rust
fn a<S: Shape>(s: &S)                    // ∀,单态化,零开销,调用方决定
fn b(s: &impl Shape)                     // 同上,语法糖
fn c(s: &dyn Shape)                      // ∃,vtable 间接调用,支持异构
fn d() -> impl Shape { Circle{r:1.} }    // 返回位置:类型隐藏但唯一,无 vtable
fn e() -> Box<dyn Shape> { ... }         // 返回位置:类型擦除,各分支可不同
```

`d` 是容易忽略的中间态:**类型系统层面**对调用方是存在量化的,但**代码生成层面**是完全确定的单一类型,没有 vtable。所以 `d` 的所有 return 分支必须是同一个类型。

## 泛型 vs dyn 决策表

|          | 泛型 `<T: Trait>` | `dyn Trait`          |
| -------- | ----------------- | -------------------- |
| 分发     | 静态,编译期确定   | 动态,vtable 间接调用 |
| 代码体积 | 每个 T 一份(膨胀) | 一份                 |
| 内联优化 | 可以              | 基本不行             |
| 异构容器 | 不行              | 可以                 |
| 指针宽度 | 8                 | 16                   |

**选择规则:类型编译期能确定 → 泛型;要在一个容器里放不同类型、或运行时才决定 → `dyn`。**

## 表达式问题(Expression Problem)

`enum` + `match` 与 `dyn Trait` 是同一问题的**对偶解**(Reynolds 1975;Wadler 命名)。

|              | `enum` + `match`             | `dyn Trait`                  |
| ------------ | ---------------------------- | ---------------------------- |
| 类型论       | 闭和(closed sum),μ 类型      | 开和(open sum),∃ 类型        |
| 加**新操作** | 易:写个新函数                | 难:改 trait,所有 impl 都要改 |
| 加**新变体** | 难:改 enum,所有 match 都要改 | 易:新 struct + impl,别处不动 |
| 穷尽性检查   | 有                           | 无(世界是开放的)             |

数据的变体是行,操作是列:`enum` 按行封闭、按列开放;`dyn` 按列封闭、按行开放。

- 写编译器 → 几乎总选 `enum`(AST 节点固定,不断加新 pass)
- 写插件 / 驱动 / 序列化后端 → 几乎总选 `dyn`(接口固定,实现无限)

> Java 只给右列,ML 只给左列,**Rust 两列都给**,代价是写下类型那一刻就必须决定。这和它在所有权、生命周期、`Sized` 上做的是同一套哲学:把编译器原本要替你猜的东西,变成你必须写下来的东西。
