---
title: "09 · Option 与 Result 的引入与消去规则"
pubDate: "2026-08-12"
author: "Roddy"
description: "一句话:在类型论里,每个类型都由两组规则定义——引入规则(怎么造出它)和消去规则(怎么用掉它)。Option<T> 的引入规则是 Some / None,消去规则就是 match。"
categories: ['rust']
series: 'rust'
order: 9
module: "标准库与工程组织"
draft: false
---

# 09 · Option 与 Result 的引入与消去规则

> 一句话:在类型论里,每个类型都由两组规则定义——**引入规则**(怎么造出它)和**消去规则**(怎么用掉它)。`Option<T>` 的引入规则是 `Some` / `None`,消去规则就是 `match`。

## 引入与消去

```rust
enum Option<T> { Some(T), None }     // 标准库里就这两行
```

```rust
let some_number = Some(5);
let no_number: Option<i32> = None;   // None 必须标类型:光看 None 无从知道 T 是什么
```

`match` 是它唯一的正门:

```rust
fn plus_one(x: Option<i32>) -> Option<i32> {
    match x {
        Some(i) => Some(i + 1),
        None => None,          // 注意这不是「跳过」,是「返回 None」—— 空也是一种结果
    }
}
```

> **抽象断裂点｜这是 Gentzen 的自然演绎,不是一个编程比喻**
> 「引入规则 / 消去规则」是 Gentzen 1934 年为**逻辑联结词**给出的定义方式。合取的引入规则是「有 A 有 B 就有 A∧B」,消去规则是「有 A∧B 就能取出 A」。析取的引入是「有 A 就有 A∨B」,消去是「若 A 能推出 C 且 B 能推出 C,则 A∨B 能推出 C」——**这最后一条,逐字就是 `match`**。
> Curry–Howard 对应把这件事说死了:类型即命题,程序即证明,`enum` 即析取,`struct` 即合取,`match` 即析取消去。所以 `Option<T>` 不是一个「聪明的库设计」,它是 `T ∨ 1` 这个命题的证明项类型。
> 更值得记的是 Prawitz 与 Dummett 的 **harmony(和谐)** 条件:引入规则和消去规则必须匹配——消去规则不能让你取出比引入规则放进去的更多的东西,否则整个系统会不一致。翻译成 API 设计的语言就是:**一个类型的构造方式和使用方式必须是对偶的,能造出来多少种情况,使用时就必须应付多少种情况。** 穷尽性检查就是编译器在替你验证 harmony。
> 短线上你只要会写 `match`;长线上这里有一条很硬的线索:**好的 API 不是「方法多」,而是构造与消费成对出现且没有缝隙。** 反过来,凡是「能造出来但没人负责处理」的状态,就是 bug 的产地。
>
> 再往前推一步就更彻底:**Böhm–Berarducci 编码**告诉你,任何代数数据类型都同构于一个关于结果类型的多态函数类型——也就是说,`Option<T>` 和它的 `match` 是同一个东西的两种写法,数据可以完全消解成它的消去方式。

## unwrap:省掉 match 的代价

```rust
let p = s.pop().unwrap();                    // 有值取值,没有值 panic
let p = s.pop().expect("字符串不该是空的");   // 同上,但 panic 信息是你写的
```

`unwrap` / `expect` 是**断言「None 不可能发生」**从而离开 Option。断错了程序就死——`expect` 至少死得有句人话。

## 两类错误:可恢复与不可恢复

|          | 类型           | 能被 match 吗      |
| -------- | -------------- | ------------------ |
| 可恢复   | `Result<T, E>` | 能——它是一个**值** |
| 不可恢复 | `panic!`       | 不能——它是**终止** |

`RUST_BACKTRACE=1 cargo run` 可以看到完整调用栈。

越界即 panic 是一个安全设计:buffer overflow 是经典攻击面,所以 `v[99]` 直接终止,而不是读到隔壁的内存。想不 panic 就走 `v.get(99) -> Option` 这条路。

> **抽象断裂点｜「可恢复」不是错误的性质,是调用方的判断**
> 同一件事——文件不存在——在配置加载器里是致命的,在缓存查找里是正常的。**没有任何客观标准能把错误分成两堆**,划界的是「此刻的调用方能不能继续工作」。
> 所以 `Result` 与 `panic!` 的分野不是本体论的,是**责任分配**的:`Result` 说「我不知道你能不能恢复,你来决定」,`panic!` 说「我替你决定了,不能」。库作者用 `panic!` 就是在替所有未来的调用方做判断——这也是为什么「库里不要 panic」是一条社区规范,而不是一条技术规则。
> 长线上的问法:**在任何系统里,「什么算异常」都不是被发现的而是被规定的,并且规定者往往不承担后果。** 医疗、法律、风控里的阈值划定是同一个结构。

## 把错误做成类型

```rust
enum MathError { DivisionByZero, NegativeSquareRoot }

match div(1.0, 0.0) {
    Ok(v) => println!("得到 {v}"),
    Err(MathError::DivisionByZero) => println!("除零"),
    Err(MathError::NegativeSquareRoot) => println!("负数开根"),
}
```

换成 `Result<f64, String>` 就做不到上面这种分支——**字符串没法被穷尽匹配**。错误做成 enum,调用方才能精确认出是哪种失败;做成字符串,错误就只能被打印,不能被处理。

## `map`:只改一半

```rust
match num.parse::<i32>().map(|i| i * 2) {
    Ok(n) => println!("{n}"),
    Err(..) => println!("解析失败"),
}
```

`map` 只作用在成功的那一侧,`Err` 原样穿过去。这是 functor 的样子:改内容,不改结构。

组合子谱系:

```rust
option.map(|n| n + 1)          // 有值就变换,仍在 Option 内
option.and_then(|v| f(v))      // 类似 map,但闭包返回 Option(避免嵌套)
option.or_else(|| Some(1))     // None 时给一个兜底
option.unwrap() / .expect(..)  // 离开 Option
```

`map` / `and_then` 让你**留在**容器里,`unwrap` / `expect` 是**离开**它。日常代码里绝大多数 `match` 都可以换成前者。

## `?`:传播而不是处理

```rust
fn div_then_sqrt(a: f64, b: f64) -> Result<f64, MathError> {
    let q = div(a, b)?;       // Err 直接 return 出去
    sqrt(q)
}
```

三次调用可以走三条不同的路径,函数体里却一个 `match` 都没有。

`?` 只能写在返回 `Result`(或 `Option`)的函数里——它要 `return`,就得知道返回什么。`main` 也可以返回 `Result`,这时 `Err` 会变成非零退出码:

```rust
fn main() -> Result<(), Box<dyn std::error::Error>> { Ok(()) }
```

(那个 `Box<dyn Error>` 的含义见 **dyn 与 trait object**。)

## Option ↔ Result:一次不对称的换算

```rust
opt.ok_or("error")     // Option → Result:补上 Option 从来没有的「原因」
res.ok()               // Result → Option:把原因丢掉,因为调用方只问「有没有」
res.err()              // 只留错误那一侧
```

**不对称正是重点**:一个方向需要额外参数(信息要从外面补进来),另一个方向会丢失信息。转换发生在你**跨越抽象层**的时候——底层知道为什么失败,上层可能只关心有没有。

## 泛型的四层职责

| 层       | 决定什么           |
| -------- | ------------------ |
| 泛型 `T` | 里面可以装什么类型 |
| `enum`   | 值可能有哪些形态   |
| `match`  | 当前值属于哪种形态 |
| 函数     | 输入如何转换为输出 |

`Option<T>` 之所以强,是因为它**同时用满了前三层**:`T` 管内容,`Some`/`None` 管形态,`match` 管分派。`Result<T, E>` 是同一个模子,只是把 `None` 换成了「带原因的 None」。

```rust
let a: Option<i32> = Some(1);
let b: Option<String> = Some("x".to_string());
// 同一个 enum 的两次单态化 —— 这是 T 在干活,见 **trait 语法** 里 monomorphization 那一节
```
