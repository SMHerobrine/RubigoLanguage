# RubigoLanguage
Rubigo is an experimental, Python-like, and heavily WIP, human-readable programming language that transpiles to ordinary Rust. It keeps Rust's static types, native compiler, performance, and ecosystem while replacing much of the punctuation-heavy surface syntax with words and explicit block endings.

```text
function greet(name: String):
    return String "Hello, {name}!"
end

function main():
    var change visits: Integer = 0
    visits = (visits + 1)
    print(greet("Ferris"), "Visit {visits}")
end
```

The transpiler produces:

```rust
fn greet(name: String) -> String {
    return format!("Hello, {name}!");
}

fn main() {
    let mut visits: i64 = 0;
    visits = (visits + 1);
    println!("{} {}", greet(String::from("Ferris")), format!("Visit {visits}"));
}
```

## Try it

Rubigo requires Python 3.10 or newer. Running or type-checking generated programs also requires a Rust installation with `rustc` on `PATH`.

```powershell
python -m rubigo transpile examples/hello.rb
python -m rubigo check examples/hello.rb
python -m rubigo run examples/hello.rb
```

To install the `rubigo` command in a virtual environment:

```powershell
python -m pip install -e .
rubigo run examples/fizzbuzz.rb
```

## Language guide

### Functions and types

```text
public function add(left: Integer, right: Integer):
    return Integer left + right
end
```

A typed return has the form `return Type expression`. It both returns the value and determines the Rust return type of the function. Every typed return in a function must agree.

The initial built-in type names map directly to Rust:

| Rubigo | Rust |
| --- | --- |
| `Int` | `i64` |
| `Integer` | `i64` |
| `Float` | `f64` |
| `Decimal` | `f64` |
| `Boolean` | `bool` |
| `String` | `String` |
| `Character` | `char` |
| `Nothing` | `()` |
| `List(T)` | `Vec<T>` |
| `Optional(T)` | `Option<T>` |
| `Result(T, E)` | `Result<T, E>` |

Unknown type names are preserved, allowing types defined in Rust escape statements to be used from Rubigo.

### Variables and output

```text
var name: String = "Ada"
var change score = 10
score = (score + 5)
print("Hello, {name}. Score:", score)
```

`var` bindings cannot be reassigned unless marked `change`. A type annotation is optional when Rust can infer it. Strings containing simple `{name}` placeholders become Rust `format!` expressions. Write `\{name\}` when the braces should appear literally.

An inferred binding may also use a colon as its value separator. Compound assignments use the familiar `+=`, `-=`, `*=`, `/=`, and `%=` spellings:

```text
var number: random.int(1, 10)
var change attempts: Int = 0
attempts += 1
```

### Input

`input` reads one line from standard input and returns it as a `String`. Pass a prompt or call it without arguments:

```text
function main():
    var name: String = input("What is your name? ")
    print("Hello, {name}!")
end
```

```text
var command: String = input()
```

When assigned to an `Int`, `Integer`, `Float`, or `Decimal` variable, `input` parses the line as that numeric type.

The generated Rust flushes the prompt before waiting, reads from `stdin`, and removes the trailing `\n` or `\r\n`. See [the Rubigo input example](examples/input.rb) and [its Rust translation](examples/input.rs).

### Control flow

```text
if score >= 90:
    print("excellent")
else if score >= 60:
    print("passed")
else:
    print("try again")
end

while score < 100:
    score = (score + 1)
end

for item in [1, 2, 3]:
    print(item)
end

for number from 0 to 10:       # 0..10; the end is excluded
    print(number)
end

for number from 1 through 10:  # 1..=10; the end is included
    print(number)
end
```

`otherwise` and `otherwise if` remain readable aliases for `else` and `else if`. The keywords `and`, `or`, and `not` generate Rust's `&&`, `||`, and `!`. `break`, `continue`, and `return` work as expected.

`elif` is another alias for `else if`. Indented control-flow blocks may omit their own `end` when a dedent closes them; the containing function still ends with `end`.

### Expressions and Rust interoperability

Function calls, method calls, field access, indexing, lists, arithmetic, comparisons, and boolean expressions use familiar notation. Two small built-ins make common ownership operations readable:

- `length(value)` becomes `value.len()`.
- `clone(value)` becomes `value.clone()`.
- `random.int(low, high)` returns an integer between the inclusive bounds.

An escape statement can insert one line of Rust when the readable syntax does not expose a feature yet:

```text
rust "use std::collections::HashMap;"

function main():
    rust "let mut scores: HashMap<String, i64> = HashMap::new();"
    rust "scores.insert(String::from(\"Ada\"), 10);"
    rust "let scores_len = scores.len();"
    print("There are {scores_len} entries")
end
```

Raw Rust is intentionally explicit: Rubigo is a front end for Rust, not a separate runtime.

## Current scope

This is a working language seed, not yet a full Rust replacement. The MVP includes source locations and readable diagnostics, but Rust currently performs name resolution, ownership checking, and final type checking. Near-term language work should add records/enums, pattern matching, references and borrowing syntax, modules, and Rubigo-aware mapping of `rustc` diagnostics back to `.rb` lines.

Run the test suite with:

```powershell
python -m unittest discover -s tests -v
```
