# Hax Program Repair

Guide for fixing Rust code that fails Hax type checking. This subskill takes proposed Hax code with errors and systematically repairs it.

## Repair Workflow

1. **Identify error category** from Hax output
2. **Apply targeted fix** from patterns below
3. **Verify fix** with `cargo hax check`
4. **Iterate** until all errors resolved

## Error Categories and Fixes

### Category 1: Unsupported Language Features

#### Error: "Unsupported: unsafe"

```rust
// ❌ BROKEN
fn read_bytes(ptr: *const u8, len: usize) -> Vec<u8> {
    unsafe {
        std::slice::from_raw_parts(ptr, len).to_vec()
    }
}

// ✅ FIXED - Use safe array passing
fn read_bytes(data: &[u8; 256], len: usize) -> [u8; 256] {
    let mut result = [0u8; 256];
    for i in 0..len.min(256) {
        result[i] = data[i];
    }
    result
}
```

#### Error: "Unsupported: dyn Trait"

```rust
// ❌ BROKEN
fn process(handler: &dyn Handler) {
    handler.handle();
}

// ✅ FIXED - Use generics
fn process<H: Handler>(handler: &H) {
    handler.handle();
}

// ✅ FIXED - Use enum dispatch
enum AnyHandler {
    TypeA(HandlerA),
    TypeB(HandlerB),
}

impl AnyHandler {
    fn handle(&self) {
        match self {
            AnyHandler::TypeA(h) => h.handle(),
            AnyHandler::TypeB(h) => h.handle(),
        }
    }
}
```

#### Error: "Unsupported: async"

```rust
// ❌ BROKEN
async fn fetch_data() -> Data {
    client.get(url).await
}

// ✅ FIXED - Use synchronous design
fn fetch_data(input: &Input) -> Data {
    // Pure computation, no IO
    compute_result(input)
}

// For actual IO, mark as opaque
#[hax::opaque]
fn fetch_data_external() -> Data {
    // Implementation hidden from verification
    unimplemented!()
}
```

### Category 2: Heap Allocation

#### Error: "Type not extractable: Vec"

```rust
// ❌ BROKEN
fn collect_items() -> Vec<u32> {
    let mut v = Vec::new();
    for i in 0..10 {
        v.push(i);
    }
    v
}

// ✅ FIXED - Use fixed-size array
fn collect_items() -> [u32; 10] {
    let mut arr = [0u32; 10];
    for i in 0..10 {
        arr[i] = i as u32;
    }
    arr
}

// ✅ FIXED - Use bounded buffer struct
struct BoundedVec<const N: usize> {
    data: [u32; N],
    len: usize,
}

impl<const N: usize> BoundedVec<N> {
    fn new() -> Self {
        BoundedVec { data: [0; N], len: 0 }
    }
    
    #[hax::requires(self.len < N)]
    fn push(&mut self, value: u32) {
        self.data[self.len] = value;
        self.len = self.len.wrapping_add(1);
    }
}
```

#### Error: "Type not extractable: String"

```rust
// ❌ BROKEN
fn make_message(name: &str) -> String {
    format!("Hello, {}!", name)
}

// ✅ FIXED - Use fixed-size byte array
fn make_message(name: &[u8; 32]) -> [u8; 64] {
    let mut result = [0u8; 64];
    let prefix = b"Hello, ";
    let suffix = b"!";
    
    // Copy prefix
    for i in 0..prefix.len() {
        result[i] = prefix[i];
    }
    
    // Copy name (find actual length)
    let mut name_len = 0;
    for i in 0..32 {
        if name[i] == 0 { break; }
        name_len = i + 1;
    }
    
    for i in 0..name_len {
        result[prefix.len() + i] = name[i];
    }
    
    // Copy suffix
    result[prefix.len() + name_len] = suffix[0];
    result
}
```

#### Error: "Type not extractable: Box"

```rust
// ❌ BROKEN
fn create_node(value: u32) -> Box<Node> {
    Box::new(Node { value, next: None })
}

// ✅ FIXED - Use arena/array-based structure
struct NodeArena<const N: usize> {
    nodes: [Node; N],
    next_free: usize,
}

#[derive(Clone, Copy, Default)]
struct Node {
    value: u32,
    next: Option<usize>,  // Index instead of pointer
}

impl<const N: usize> NodeArena<N> {
    fn new() -> Self {
        NodeArena {
            nodes: [Node::default(); N],
            next_free: 0,
        }
    }
    
    #[hax::requires(self.next_free < N)]
    fn alloc(&mut self, value: u32) -> usize {
        let idx = self.next_free;
        self.nodes[idx] = Node { value, next: None };
        self.next_free = self.next_free.wrapping_add(1);
        idx
    }
}
```

### Category 3: Potential Panics

#### Error: "Panic possible: index out of bounds"

```rust
// ❌ BROKEN
fn get_item(arr: &[u8; 32], index: usize) -> u8 {
    arr[index]
}

// ✅ FIXED - Add precondition
#[hax::requires(index < 32)]
fn get_item(arr: &[u8; 32], index: usize) -> u8 {
    arr[index]
}

// ✅ FIXED - Return Option
fn get_item_safe(arr: &[u8; 32], index: usize) -> Option<u8> {
    if index < 32 {
        Some(arr[index])
    } else {
        None
    }
}

// ✅ FIXED - Use get() method
fn get_item_checked(arr: &[u8; 32], index: usize) -> u8 {
    match arr.get(index) {
        Some(&v) => v,
        None => 0,  // Default value
    }
}
```

#### Error: "Panic possible: division by zero"

```rust
// ❌ BROKEN
fn divide(a: u32, b: u32) -> u32 {
    a / b
}

// ✅ FIXED - Add precondition
#[hax::requires(b != 0)]
fn divide(a: u32, b: u32) -> u32 {
    a / b
}

// ✅ FIXED - Return Option
fn divide_safe(a: u32, b: u32) -> Option<u32> {
    if b == 0 {
        None
    } else {
        Some(a / b)
    }
}

// ✅ FIXED - Use checked_div
fn divide_checked(a: u32, b: u32) -> Option<u32> {
    a.checked_div(b)
}
```

#### Error: "Panic possible: arithmetic overflow"

```rust
// ❌ BROKEN
fn add(a: u32, b: u32) -> u32 {
    a + b
}

// ✅ FIXED - Use wrapping
fn add_wrap(a: u32, b: u32) -> u32 {
    a.wrapping_add(b)
}

// ✅ FIXED - Use saturating
fn add_sat(a: u32, b: u32) -> u32 {
    a.saturating_add(b)
}

// ✅ FIXED - Use checked with handling
fn add_checked(a: u32, b: u32) -> Option<u32> {
    a.checked_add(b)
}

// ✅ FIXED - Precondition no overflow
#[hax::requires(a as u64 + b as u64 <= u32::MAX as u64)]
fn add_precond(a: u32, b: u32) -> u32 {
    a + b
}
```

### Category 4: Mutation Issues

#### Error: "Mutation not allowed in this context"

```rust
// ❌ BROKEN - Complex mutation pattern
fn update_both(a: &mut u32, b: &mut u32, arr: &mut [u32; 4]) {
    *a = arr[0];
    *b = arr[1];
    arr[0] = *b;
    arr[1] = *a;
}

// ✅ FIXED - Return new values instead
fn compute_updates(arr: &[u32; 4]) -> (u32, u32, [u32; 4]) {
    let a = arr[0];
    let b = arr[1];
    let mut new_arr = *arr;
    new_arr[0] = b;
    new_arr[1] = a;
    (a, b, new_arr)
}

// ✅ FIXED - Single mutable reference
fn swap_first_two(arr: &mut [u32; 4]) {
    let tmp = arr[0];
    arr[0] = arr[1];
    arr[1] = tmp;
}
```

#### Error: "Closure captures mutable state"

```rust
// ❌ BROKEN
fn accumulate(values: &[u32; 10]) -> u32 {
    let mut sum = 0u32;
    values.iter().for_each(|v| sum = sum.wrapping_add(*v));
    sum
}

// ✅ FIXED - Use for loop
fn accumulate(values: &[u32; 10]) -> u32 {
    let mut sum = 0u32;
    for i in 0..10 {
        sum = sum.wrapping_add(values[i]);
    }
    sum
}

// ✅ FIXED - Use fold pattern (if supported)
fn accumulate_fold(values: &[u32; 10]) -> u32 {
    let mut sum = 0u32;
    for v in values.iter() {
        sum = sum.wrapping_add(*v);
    }
    sum
}
```

### Category 5: Loop Issues

#### Error: "Unbounded loop"

```rust
// ❌ BROKEN - No clear bound
fn find_pattern(data: &[u8; 1024]) -> usize {
    let mut i = 0;
    while data[i] != 0xFF {
        i += 1;
    }
    i
}

// ✅ FIXED - Add explicit bound
fn find_pattern(data: &[u8; 1024]) -> usize {
    let mut i = 0usize;
    while i < 1024 && data[i] != 0xFF {
        i = i.wrapping_add(1);
    }
    i
}

// ✅ FIXED - Add loop invariant
fn find_pattern_inv(data: &[u8; 1024]) -> usize {
    let mut i = 0usize;
    #[hax::loop_invariant(|i| i <= 1024)]
    while i < 1024 {
        if data[i] == 0xFF {
            return i;
        }
        i = i.wrapping_add(1);
    }
    1024
}
```

#### Error: "Loop variable modification"

```rust
// ❌ BROKEN - Modifying loop variable
fn skip_zeros(data: &[u8; 32]) -> usize {
    for i in 0..32 {
        if data[i] != 0 {
            i += 5;  // Skip ahead - not allowed
        }
    }
    0
}

// ✅ FIXED - Use while loop
fn skip_zeros(data: &[u8; 32]) -> usize {
    let mut i = 0usize;
    while i < 32 {
        if data[i] != 0 {
            i = i.wrapping_add(5);
        } else {
            i = i.wrapping_add(1);
        }
    }
    0
}
```

### Category 6: Type Extraction Issues

#### Error: "Cannot extract type with lifetime"

```rust
// ❌ BROKEN
struct Parser<'a> {
    input: &'a str,
    position: usize,
}

// ✅ FIXED - Owned data with index
struct Parser {
    input: [u8; 1024],
    input_len: usize,
    position: usize,
}

impl Parser {
    fn new(data: &[u8; 1024], len: usize) -> Self {
        let mut input = [0u8; 1024];
        for i in 0..len.min(1024) {
            input[i] = data[i];
        }
        Parser { input, input_len: len, position: 0 }
    }
}
```

#### Error: "Generic bound not extractable"

```rust
// ❌ BROKEN - Complex bounds
fn process<T: Iterator<Item = u32> + Clone>(iter: T) { }

// ✅ FIXED - Concrete type
fn process(arr: &[u32; 32]) {
    for i in 0..32 {
        let _ = arr[i];
    }
}

// ✅ FIXED - Simpler bound
fn process<T: Clone + Copy>(value: T) -> T {
    value
}
```

## Systematic Repair Process

### Step 1: Run Hax Check

```bash
cargo hax check 2>&1 | tee hax-errors.log
```

### Step 2: Parse Errors

Look for these patterns in output:
- `Unsupported:` - Language feature not supported
- `Type not extractable:` - Type cannot be extracted
- `Panic possible:` - Operation may panic
- `Mutation:` - Mutation pattern issue
- `Loop:` - Loop termination/bound issue

### Step 3: Apply Fixes by Priority

1. **Unsupported features** - Replace with supported alternatives
2. **Type issues** - Convert to extractable types
3. **Panic sources** - Add preconditions or safe alternatives
4. **Mutation patterns** - Restructure to functional style
5. **Loop issues** - Add bounds and invariants

### Step 4: Verify Incrementally

```bash
# After each fix
cargo hax check

# Full extraction test
cargo hax into fstar
```

## Common Fix Patterns Summary

| Problem | Quick Fix |
|---------|-----------|
| `Vec<T>` | `[T; N]` with length tracking |
| `String` | `[u8; N]` with length tracking |
| `Box<T>` | Arena pattern with indices |
| `unsafe` | Redesign with safe Rust |
| `dyn Trait` | Generics or enum dispatch |
| `arr[i]` panic | Add `#[hax::requires(i < N)]` |
| `a / b` panic | Add `#[hax::requires(b != 0)]` |
| `a + b` overflow | Use `a.wrapping_add(b)` |
| Unbounded loop | Add loop bound check |
| Mutable closure | Convert to for loop |
| Complex lifetime | Use owned data with indices |

## Testing Repairs

After applying fixes, verify:

```bash
# 1. Rust compilation still works
cargo build

# 2. Tests still pass  
cargo test

# 3. Hax accepts the code
cargo hax check

# 4. Full extraction works
cargo hax into fstar
cargo hax into coq
```
