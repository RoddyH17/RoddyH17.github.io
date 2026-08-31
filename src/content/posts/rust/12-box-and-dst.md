---
title: "12 · Box 与 DST"
pubDate: "2026-08-24"
author: "Roddy"
description: "判据只有一条:编译期能不能算出它占几个字节。"
categories: ['rust']
series: 'rust'
order: 12
module: "抽象与内存表示进阶"
draft: false
---

# 12 · Box 与 DST

## 一、Sized 与 DST 的分界

判据只有一条:**编译期能不能算出它占几个字节**。

```rust
size_of::<i32>()      // 4    Sized
size_of::<[i32; 3]>() // 12   Sized,长度写在类型里
```

**DST(Dynamically Sized Type)** = 编译期算不出大小。Rust 里只有四种:

| DST                          | 缺什么信息     |
| ---------------------------- | -------------- |
| `[T]`(切片,没有长度)         | 元素个数       |
| `str`                        | 字节数         |
| `dyn Trait`                  | 具体是哪个类型 |
| 最后一个字段是 DST 的 struct | 同上           |

核心限制:**DST 不能直接作为值存在**。

```rust
let x: [i32];       // ✗ 栈帧要分配多少字节?
let z: dyn Shape;   // ✗
fn f(a: dyn Shape)  // ✗ 参数按值传,同样不行
```

## 二、胖指针(fat pointer)

DST 只能放在指针后面,而指向 DST 的指针**多带一个字**,把缺失信息补回来:

```
&i32        →  [ ptr ]                  8 字节
&[i32]      →  [ ptr | len ]           16 字节
&str        →  [ ptr | 字节数 ]         16 字节
&dyn Shape  →  [ ptr | vtable 指针 ]    16 字节
```

实测(已验证):

```rust
size_of::<&i32>()       // 8
size_of::<&[i32]>()     // 16
size_of::<&str>()       // 16
size_of::<&dyn Shape>() // 16

size_of_val("héllo")    // 6   é 占两字节,运行时才知道
size_of_val(&[1,2,3,4]) // 16
```

> **抽象断裂点｜信息不会消失,只会换位置**
> 瘦指针 8 字节,胖指针 16 字节。多出来的那 8 字节不是开销,是**被搬家的编译期信息**:`[T]` 缺的长度、`dyn Trait` 缺的类型,原本应该刻在类型里、由编译器在编译期消耗掉;现在它被写成运行时的一个字,随指针一起走。
> 把这条当成一条守恒律记住:**一个类型系统能省下的运行时数据量,等于它在编译期已经确定下来的信息量。** `[i32; 3]` 把长度写进类型 → 指针 8 字节;`[i32]` 不写 → 指针 16 字节。同一件事在 **dyn 与 trait object** 里表现为 vtable,在 **递归数据结构** 里表现为「大小方程无解就把递归位固定成 8 字节」。三处是一个动作。

## 三、`?Sized`

泛型参数**默认隐式带 `Sized`**。`fn f<T>(x: &T)` 编译器读作 `fn f<T: Sized>(x: &T)`。

```rust
fn f<T>(x: &T) {}          // T 必须 Sized
fn g<T: ?Sized>(x: &T) {}  // T 可以是 [u8] / str / dyn Trait

g::<str>;  // ✓
f::<str>;  // ✗
```

`?Sized` 是 Rust 里**唯一的「放宽约束」语法**(`?` = 这条约束可选)。
标准库例子:`fn size_of_val<T: ?Sized>(val: &T) -> usize`

> **抽象断裂点｜默认值的方向性**
> `fn f<T>` 被读作 `fn f<T: Sized>`。也就是说 Rust 的泛型**默认封闭**,`?Sized` 是唯一一条「申请例外」的语法。
> 这不是技术必然,方向完全可以反过来:一门语言可以默认 `?Sized`,要求你显式写 `T: Sized`。Rust 选现在这个方向,是因为绝大多数泛型代码要按值移动 `T`。代价是:**默认值决定了哪一类代码是「正常的」,哪一类需要为自己解释。** 一条约束一旦成为默认,它就从「一条规则」退成了「背景」,而背景是不被审视的。
> 这个结构在制度里到处都是——opt-in 与 opt-out 的器官捐献率差异是最著名的经验例子。也见 **Lecture 1 - Axiomatizing Democratic Choice**:投票规则同样是在决定「哪些信息默认进入结果」。

## 四、Box 的真实定义

```rust
pub struct Box<T: ?Sized, A: Allocator = Global>(Unique<T>, A);
```

`T: ?Sized` 就是 Box 的关键权限:**它可以装 DST**。

```rust
let a: Box<str>       = "hello".into();
let b: Box<[i32]>     = vec![1,2,3].into_boxed_slice();
let c: Box<dyn Shape> = Box::new(Circle { r: 1.0 });
```

⚠️ **Box 的宽度取决于 T 是不是 DST**:

- `Box<i32>` = 8(瘦指针)
- `Box<[i32]>` = `Box<dyn Shape>` = 16(胖指针)

## 五、niche 优化

Box 保证非空指针,所以 `None` 可以复用 `0` 这个不可能的位模式:

```rust
size_of::<Box<T>>()         == size_of::<Option<Box<T>>>()
```

这条性质是 **递归数据结构** 里链表能高效表示的前提。

## 六、带 DST 尾巴的 struct

```rust
struct Wrapper<T: ?Sized> { id: u32, data: T }

let w: Box<Wrapper<[u8]>> = Box::new(Wrapper { id: 7, data: [1u8,2,3,4,5] });
//     ^ Box<Wrapper<[u8;5]>> 自动 unsize 强转成 Box<Wrapper<[u8]>>

w.data.len()      // 5,长度存在胖指针里
size_of_val(&*w)  // 12 = 4(id) + 5(data) + 3(padding)
```

只有**最后一个字段**能是 DST。
