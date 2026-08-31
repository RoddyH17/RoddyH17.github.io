---
title: "07 · struct、impl 与 self 的四种形态"
pubDate: "2026-08-11"
author: "Roddy"
description: "一句话:Rust 没有 class,也没有继承。OO 里绑在一个关键字里的三件事在这里是三个独立特性——struct 是数据,impl 挂行为,trait 是跨无关类型的共享行为。"
categories: ['rust']
series: 'rust'
order: 7
module: "标准库与工程组织"
draft: false
---

# 07 · struct、impl 与 self 的四种形态

> 一句话:Rust 没有 class,也没有继承。OO 里绑在一个关键字里的三件事在这里是三个独立特性——**struct 是数据**,**`impl` 挂行为**,**trait 是跨无关类型的共享行为**。

> **抽象断裂点｜被拆开的三合一**
> `class` 这个关键字在 Java / C++ / Python 里同时做四件事:定义数据布局、定义方法、定义子类型关系、定义命名空间。这四件事被绑在一起,是 1960 年代 Simula 的历史选择,不是逻辑必然。
> Rust 把它们拆成:`struct`/`enum`(布局)、`impl`(方法与命名空间)、`trait`(共享行为与约束)、而**子类型关系直接删掉**。拆开之后能做一些原来做不到的事——比如给你没写的类型加行为(见 **trait 语法** 的 blanket impl),或者给同一个类型写多个互不相干的 `impl` 块。
> 拆分的代价也很实在:原本一个关键字能说清的意图,现在要写三处;而「这个类型到底有哪些方法」不再能从定义处读出来,要在整个 crate 里找 `impl`。
> 长线上的问法:**一个把 N 件事捆在一起的抽象,和 N 个可自由组合的抽象,分界线在哪?** 捆绑降低认知负担、保证一致性;解耦提高表达力、允许后加。这条张力在模块系统、权限模型、组织设计里是同一条。

## struct 只是数据

每个字段都必须初始化,**没有默认赋值**。

```rust
struct User { active: bool, username: String, email: String, sign_in_count: u64 }

let user1 = User { email, username, active: true, sign_in_count: 1 };
//                 ↑ 字段初始化简洁语法:局部变量与字段同名时可省 field: field
```

三种形态:

```rust
struct Point(i32, i32, i32);   // 元组结构体:类型值得有名字,字段不需要
struct AlwaysEqual;            // 单元结构体:不关心数据,只关心行为
```

元组结构体的价值在于**编译器现在会阻止你把一个颜色传给坐标**——裸的 `(i32, i32, i32)` 做不到。这就是 newtype 模式的起点。

## `mut` 修饰的是绑定,不是字段

```rust
let r3 = Rectangle { width: 1, height: 1 };
r3.width = 5;
// error[E0594]: cannot assign to `r3.width`, as `r3` is not declared as mutable
```

Rust **不能**对单个字段标记可写。这不是一个独立的设计决定,而是借用规则的推论:`&mut` 给出的是对**整个值**的独占访问,所以「可变」的粒度不可能细过你交出去的那个引用。见 **借用、引用与 NLL**。

## 更新语法 `..other` 是移动,不是拷贝

```rust
let user2 = User { email: String::from("another@example.com"), ..user1 };

println!("{}", user1.active);     // ✅ bool 是 Copy,还能读
println!("{}", user1.username);   // ❌ error[E0382]: borrow of moved value
```

`user1` 不是整体作废,而是**部分移动**:`Copy` 字段留下,`String` 字段走了。编译器就按字段粒度追踪。这是 **所有权与内存模型** 的移动语义作用在每个字段上。

## 存 `&str` 需要生命周期

```rust
struct User<'a> { username: &'a str, email: &'a str }
```

结构体不拥有那些字节,只是借用,所以它必须承诺**自己不会活得比被指向的数据久**,`'a` 就是这个承诺写下来。改存 `String` 就不需要——那时结构体拥有数据。

## `impl`:方法与关联函数

```rust
impl Rectangle {
    fn new(width: u32, height: u32) -> Rectangle { Rectangle { width, height } }  // 关联函数
    fn area(&self) -> u32 { self.width * self.height }                            // 方法
}
```

`new` 写成自由函数也能跑,放进 `impl` 是为了**组织和命名空间**——让它成为 `Rectangle::new`,而不是一个碰巧返回 Rectangle 的散函数。`impl` 挂行为时并不关心类型是 struct 还是 enum,规则和 **enum 与和类型** 里完全一样。

## 今天最大的坑:`mut self` 把实例吃掉了

```rust
fn set_width(mut self, new_width: u32) { self.width = new_width; }   // ❌

let rect2 = Rectangle { width: 20, height: 30 };
rect2.set_width(10);
// 之后再用 rect2: error[E0382] `rect2` moved due to this method call
```

能编译,但什么也没做,还把 `rect2` 销毁了。`mut self` 的意思是「拿走接收者的所有权,并允许我修改**我自己那份**」,方法结束时那份就被 drop 了。

| 接收者      | 含义                          |
| ----------- | ----------------------------- |
| `self`      | 消耗掉调用者                  |
| `&self`     | 只读                          |
| `&mut self` | 原地修改                      |
| `mut self`  | **长得像第三种,行为是第一种** |

> **抽象断裂点｜一个不报错的错误**
> `mut self` 这个坑的危险不在于它难懂,而在于**它编译通过、没有警告、方法体逻辑也完全正确**。错误在调用处才显形,而且报的是「值被移动了」,与你想改的那件事看起来毫无关系。
> 语法的相似度(`mut self` vs `&mut self` 只差一个 `&`)与语义的距离(消耗 vs 借用)在这里是反比的。这是**语法邻近性误导语义直觉**的一个标本——同类的还有 `&` 在类型位置(引用)与模式位置(解构)的双重身份、`as` 在 `use` 里(重命名)与表达式里(类型转换)的双重身份(见 **模块、可见性与 workspace**)。
> 值得记的判据:**当两个东西写起来只差一个符号,而语义差一个数量级时,错误就会以「远处的、看似无关的报错」形式出现。** 排查这类问题要往回看接收者、往回看所有权,而不是盯着报错那一行。

## Debug 可以 derive,Display 不行

```rust
#[derive(Debug)]
pub struct Rectangle { width: u32, height: u32 }

println!("{rect:?}");    // 单行
println!("{rect:#?}");   // 展开,一行一个字段
dbg!(&rect);             // 还会打印 file:line,并把值返回
```

但 `{}` 是另一个 trait,而且**故意没有 `#[derive(Display)]`**:一个类型该怎么呈现给**用户**,是宏替你做不了的判断。

```rust
impl std::fmt::Display for Rectangle {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        for _ in 0..self.height {
            writeln!(f, "{}", "#".repeat(self.width as usize))?;
        }
        Ok(())
    }
}
```

**Debug 是给我自己看的,Display 是给读输出的人看的**,两者很少是同一串字符。这个区分本身是一个规范性判断被写进了标准库:哪些事可以自动化,哪些事必须由人决定。

## Trait:共享行为,不是共享父类

```rust
trait Shape { fn area(&self) -> f64; }
impl Shape for Rectangle { /* ... */ }
impl Shape for Circle    { /* ... */ }
```

`Rectangle` 和 `Circle` 不共享数据、不共享父类、不共享内存布局,只共享「都能回答 `area()`」这一件事。

叫它「Rust 的 interface」入门够用,但少说了一点:**trait 可以为你没写的类型实现**。没有基类可以插进去,「这个类型算不算数」由一个独立的 `impl` 块回答,而不是由类型自己的定义回答。完整语法见 **trait 语法**。

**为什么写 `&impl Shape` 而不是两个具体参数**:

```rust
fn print_area(shape: &impl Shape) { println!("{}", shape.area()); }
```

写成 `print_area(r: &Rectangle, c: &Circle)` 是在回答错误的问题——它把「存在哪些类型」写死了。`&impl Shape` 说的是「任何能告诉我面积的东西」,类型集合保持开放。而且它运行时不花钱:静态分发,编译期单态化。要在运行时才决定类型才用 `&dyn Shape`,见 **dyn 与 trait object**。

## 编译器抓到的两个真 bug

**丢掉的 Result**:`write!(f, "{}\n", s);` 触发 `warning: unused Result that must be used`。写入是可能失败的,一个被忽略的警告意味着真实错误会静默消失。`writeln!(f, "{}", s)?;` 同时修好了它和手写的 `\n`。

**藏在转换背后的溢出**:

```rust
fn area(&self) -> f64 { (self.width * self.height) as f64 }        // ❌ 乘法先在 u32 里发生
fn area(&self) -> f64 { self.width as f64 * self.height as f64 }   // ✅ 先转再乘
```

100000 × 100000 会触发 `attempt to multiply with overflow`——**debug 下 panic,release 下静默给出错的数**。同一段代码在两种构建模式下行为不同,这本身值得警惕。

(另外圆面积里的 `3.14` 应该用 `std::f64::consts::PI`。)
