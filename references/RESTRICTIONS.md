# Hax Restrictions Reference

Complete reference for Rust features supported by Hax.

## Type System Support

### Primitive Types

| Type | Support | Notes |
|------|---------|-------|
| `bool` | ✅ Full | |
| `u8`, `u16`, `u32`, `u64`, `u128` | ✅ Full | |
| `i8`, `i16`, `i32`, `i64`, `i128` | ✅ Full | |
| `usize`, `isize` | ✅ Full | Extracted as bounded integers |
| `f32`, `f64` | ⚠️ Limited | Backend-dependent support |
| `char` | ✅ Full | |
| `()` | ✅ Full | Unit type |
| `!` | ❌ No | Never type not supported |

### Compound Types

| Type | Support | Notes |
|------|---------|-------|
| `[T; N]` | ✅ Full | Fixed-size arrays |
| `(T1, T2, ...)` | ✅ Full | Tuples up to reasonable size |
| `&T` | ✅ Full | Immutable references |
| `&mut T` | ⚠️ Limited | Must follow strict borrowing |
| `*const T`, `*mut T` | ❌ No | Raw pointers not supported |
| `fn(T) -> U` | ⚠️ Limited | Function pointers limited |
| `&[T]` | ⚠️ Limited | Slices need bounds proofs |
| `&str` | ⚠️ Limited | String slices need care |

### Standard Library Types

| Type | Support | Alternative |
|------|---------|-------------|
| `Vec<T>` | ❌ No | Use `[T; N]` |
| `String` | ❌ No | Use `[u8; N]` or `&str` |
| `Box<T>` | ❌ No | Use stack allocation |
| `Rc<T>`, `Arc<T>` | ❌ No | Redesign ownership |
| `Cell<T>`, `RefCell<T>` | ❌ No | Avoid interior mutability |
| `Mutex<T>`, `RwLock<T>` | ❌ No | Single-threaded extraction |
| `HashMap<K, V>` | ❌ No | Use arrays with linear search |
| `HashSet<T>` | ❌ No | Use sorted arrays |
| `Option<T>` | ✅ Full | Define your own or use core |
| `Result<T, E>` | ✅ Full | Define your own or use core |

## Language Features

### Supported

```rust
// Structs with named fields
struct Point { x: u32, y: u32 }

// Tuple structs
struct Pair(u32, u32);

// Unit structs
struct Marker;

// Enums with variants
enum Message {
    Quit,
    Move { x: i32, y: i32 },
    Write(String),
}

// Generic types
struct Container<T> { value: T }

// Const generics
struct Array<const N: usize> { data: [u8; N] }

// Where clauses
fn process<T>(x: T) -> T where T: Clone { x }

// Associated types in traits
trait Iterator {
    type Item;
    fn next(&mut self) -> Option<Self::Item>;
}

// Default trait implementations
trait Greet {
    fn greet(&self) -> &str { "Hello" }
}

// Derive macros (some)
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
struct Data { value: u32 }
```

### Not Supported

```rust
// ❌ Trait objects
fn process(x: &dyn Display) { }
fn boxed() -> Box<dyn Trait> { }

// ❌ impl Trait in return position (limited)
fn make_iter() -> impl Iterator<Item = u32> { }

// ❌ Existential types
type Foo = impl Trait;

// ❌ Higher-ranked trait bounds (limited)
fn call<F>(f: F) where F: for<'a> Fn(&'a u32) { }

// ❌ Specialization
impl<T> Trait for T { }
impl Trait for u32 { }  // More specific

// ❌ Negative trait bounds
impl<T> Trait for T where T: !Copy { }

// ❌ Auto traits
auto trait MyAuto { }
```

## Control Flow

### Supported Patterns

```rust
// If/else
fn abs(x: i32) -> i32 {
    if x >= 0 { x } else { -x }
}

// Match expressions
fn describe(x: Option<u32>) -> &'static str {
    match x {
        Some(0) => "zero",
        Some(n) if n > 100 => "large",
        Some(_) => "normal",
        None => "nothing",
    }
}

// For loops with ranges
for i in 0..10 { }
for i in 0..=10 { }  // inclusive
for i in (0..10).rev() { }  // reverse

// For loops with arrays
for element in arr.iter() { }
for (i, element) in arr.iter().enumerate() { }

// While loops
while condition { }

// Loop with break
loop {
    if done { break result; }
}

// Early return
fn find(arr: &[u8; 32], target: u8) -> Option<usize> {
    for i in 0..32 {
        if arr[i] == target {
            return Some(i);
        }
    }
    None
}

// Let-else (Rust 1.65+)
let Some(x) = opt else { return None; };
```

### Limited/Unsupported Patterns

```rust
// ⚠️ Unbounded while (needs invariant)
while some_condition() { }  // May need #[hax::loop_invariant]

// ❌ Iterator chains (complex ones)
arr.iter().filter(|x| **x > 0).map(|x| x * 2).collect()

// ❌ Recursion without termination
fn recurse(n: u32) -> u32 {
    recurse(n + 1)  // No termination proof
}

// ⚠️ Complex closures
let f = |x| x + captured_var;  // Simple OK
let f = move |x| { /* complex */ };  // May fail

// ❌ Async/await
async fn fetch() { }
let fut = async { };
future.await;

// ❌ Generators/coroutines
fn* generator() { yield 1; }

// ❌ Try blocks
let result = try { may_fail()? };
```

## Memory and Ownership

### Supported Patterns

```rust
// Stack allocation
let arr: [u8; 1024] = [0u8; 1024];

// Simple borrowing
fn read(data: &[u8; 32]) -> u8 { data[0] }
fn write(data: &mut [u8; 32]) { data[0] = 1; }

// Move semantics
fn take(data: [u8; 32]) -> [u8; 32] { data }

// Copy types
#[derive(Clone, Copy)]
struct Small { a: u32, b: u32 }

// Reborrowing
fn process(x: &mut u32) {
    helper(&mut *x);  // Reborrow OK
}
```

### Restricted Patterns

```rust
// ❌ Heap allocation
let boxed = Box::new(value);
let vec = Vec::new();
let string = String::from("hello");

// ❌ Reference counting
let rc = Rc::new(value);
let arc = Arc::new(value);

// ⚠️ Complex lifetimes
struct RefHolder<'a, 'b> {
    a: &'a u32,
    b: &'b u32,
}

// ❌ Self-referential structs
struct SelfRef {
    data: String,
    ptr: &str,  // Points to data
}

// ❌ Interior mutability
let cell = Cell::new(0);
let refcell = RefCell::new(vec![]);
```

## Arithmetic and Operations

### Safe Patterns (Required)

```rust
// Wrapping arithmetic (never panics)
a.wrapping_add(b)
a.wrapping_sub(b)
a.wrapping_mul(b)
a.wrapping_div(b)  // Still panics on zero!
a.wrapping_rem(b)
a.wrapping_neg()
a.wrapping_shl(n)
a.wrapping_shr(n)

// Checked arithmetic (returns Option)
a.checked_add(b)  // None on overflow
a.checked_div(b)  // None on zero

// Saturating arithmetic
a.saturating_add(b)  // Clamps at MAX/MIN
a.saturating_sub(b)

// Overflowing arithmetic (returns tuple)
let (result, overflowed) = a.overflowing_add(b);

// Bitwise operations
a & b    // AND
a | b    // OR
a ^ b    // XOR
!a       // NOT
a << n   // Left shift
a >> n   // Right shift

// Rotate operations
a.rotate_left(n)
a.rotate_right(n)

// Byte operations
a.to_be_bytes()
a.to_le_bytes()
u32::from_be_bytes(arr)
u32::from_le_bytes(arr)
a.swap_bytes()
a.reverse_bits()
```

### Potentially Panicking (Avoid)

```rust
// ❌ Standard arithmetic (may panic in debug)
a + b
a - b
a * b

// ❌ Division (panics on zero)
a / b
a % b

// ❌ Indexing (panics out of bounds)
arr[i]

// ❌ Unwrap (panics on None/Err)
opt.unwrap()
result.unwrap()

// ❌ Expect (panics with message)
opt.expect("should exist")
```

## Module and Visibility

### Supported

```rust
// Module declarations
mod inner {
    pub fn public() { }
    fn private() { }
}

// Use statements
use crate::module::Type;
use super::parent_fn;

// Re-exports
pub use inner::public;

// Visibility modifiers
pub fn public() { }
pub(crate) fn crate_visible() { }
pub(super) fn parent_visible() { }
fn private() { }
```

### Not Supported

```rust
// ❌ External crates (most)
use rand::Rng;
use serde::{Serialize, Deserialize};

// ❌ Macros (procedural)
#[derive(Serialize)]  // External derive macros

// ⚠️ Build scripts
// build.rs - may not extract
```

## Attributes and Macros

### Hax-Specific Attributes

```rust
use hax_lib as hax;

#[hax::requires(precondition)]      // Precondition
#[hax::ensures(|r| postcondition)]  // Postcondition
#[hax::loop_invariant(|vars| inv)]  // Loop invariant
#[hax::opaque]                       // Hide from extraction
#[hax::exclude]                      // Exclude from extraction
#[hax::refinement_type(predicate)]  // Refinement type
```

### Supported Standard Attributes

```rust
#[derive(Clone, Copy, Debug, PartialEq, Eq, Default)]
#[allow(unused)]
#[cfg(feature = "hax")]
#[cfg_attr(feature = "hax", ...)]
#[inline]
#[must_use]
#[repr(C)]
#[repr(transparent)]
```

### Limited Macro Support

```rust
// ✅ Simple macros
println!();  // For debugging only
assert!();   // Extracted as assumptions
debug_assert!();

// ⚠️ Format macros
format!();   // May not extract
panic!();    // Becomes unreachable

// ❌ Complex procedural macros
#[tokio::main]
#[serde(rename_all = "camelCase")]
```

## Best Practices Summary

1. **Use fixed-size arrays** instead of Vec/String
2. **Use wrapping arithmetic** for all math operations
3. **Prove array bounds** with preconditions or loop structure
4. **Avoid heap allocation** - stack-allocate everything
5. **Keep functions pure** - minimize side effects
6. **Add specifications** - requires/ensures for verification
7. **Test with `cargo hax check`** before full extraction
8. **Use const generics** for flexible array sizes
9. **Derive Clone/Copy** where possible
10. **Avoid complex lifetimes** - keep borrowing simple
