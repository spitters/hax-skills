// Test file with intentional Hax violations
// Run hax-lint.scm against this to verify queries work

#![allow(dead_code, unused_variables)]

// ============================================================================
// UNSAFE CODE - should all be @error
// ============================================================================

unsafe fn unsafe_function() {}

unsafe trait UnsafeTrait {}

unsafe impl UnsafeTrait for () {}

fn uses_unsafe_block() {
    unsafe {
        let x = 42;
    }
}

// ============================================================================
// RAW POINTERS - should be @error
// ============================================================================

fn raw_pointers(p: *const u8, q: *mut i32) {
    let ptr: *const f64 = std::ptr::null();
}

// ============================================================================
// TRAIT OBJECTS - should be @error
// ============================================================================

trait MyTrait {}

fn takes_dyn(x: &dyn MyTrait) {}
fn takes_boxed_dyn(x: Box<dyn MyTrait>) {}

// ============================================================================
// HEAP ALLOCATION - should be @error
// ============================================================================

fn heap_types() {
    let v: Vec<u8> = Vec::new();
    let v2 = Vec::with_capacity(10);
    let v3 = vec![1, 2, 3];

    let b: Box<u32> = Box::new(42);

    let s: String = String::new();
    let s2 = String::from("hello");
    let s3 = format!("formatted {}", 42);

    let rc: std::rc::Rc<u32> = todo!();
    let arc: std::sync::Arc<u32> = todo!();

    let map: std::collections::HashMap<u32, u32> = todo!();
    let set: std::collections::HashSet<u32> = todo!();
    let btree: std::collections::BTreeMap<u32, u32> = todo!();
}

// ============================================================================
// UNBOUNDED LOOPS - should be @error
// ============================================================================

fn unbounded_loops() {
    loop {
        break;
    }

    let mut x = 0;
    while x < 10 {
        x += 1;
    }

    let mut opt = Some(1);
    while let Some(v) = opt {
        opt = None;
    }
}

// Bounded for loop - should NOT be flagged
fn bounded_loop() {
    for i in 0..100 {
        let _ = i;
    }
}

// ============================================================================
// ASYNC/AWAIT - should be @error
// ============================================================================

async fn async_function() {}

fn uses_async() {
    let _ = async {
        42
    };
}

// ============================================================================
// FLOATING POINT - should be @warning
// ============================================================================

fn floating_point(x: f32, y: f64) -> f64 {
    let z = 3.14159;
    x as f64 + y + z
}

// ============================================================================
// INTERIOR MUTABILITY - should be @error
// ============================================================================

use std::cell::{Cell, RefCell};

fn interior_mutability() {
    let c: Cell<u32> = Cell::new(0);
    let rc: RefCell<u32> = RefCell::new(0);
}

// ============================================================================
// GLOBAL MUTABLE STATE - should be @error
// ============================================================================

static mut GLOBAL_COUNTER: u32 = 0;

// ============================================================================
// INLINE ASSEMBLY - should be @error
// ============================================================================

fn uses_asm() {
    // unsafe { asm!("nop"); }  // Would need unsafe block
}

// ============================================================================
// UNION - should be @error
// ============================================================================

union MyUnion {
    i: i32,
    f: f32,
}

// ============================================================================
// FFI - should be @error
// ============================================================================

extern "C" {
    fn external_function();
}

#[no_mangle]
pub extern "C" fn exported_function() {}

// ============================================================================
// PANICKING - should be @warning
// ============================================================================

fn panicking_code() {
    panic!("oh no");
    todo!();
    unimplemented!();
    unreachable!();

    let opt: Option<u32> = None;
    let _ = opt.unwrap();
    let _ = opt.expect("failed");
}

// ============================================================================
// I/O - should be @warning
// ============================================================================

fn io_operations() {
    println!("hello");
    print!("world");
    eprintln!("error");
    dbg!(42);
}

// ============================================================================
// THREADING - should be @error
// ============================================================================

fn threading() {
    let atomic: std::sync::atomic::AtomicU32 = todo!();
}

// ============================================================================
// ARITHMETIC - should be @warning
// ============================================================================

fn arithmetic(a: u32, b: u32) -> u32 {
    let div = a / b;      // potential panic
    let rem = a % b;      // potential panic
    let arr = [1, 2, 3];
    arr[0]                // potential panic
}

// ============================================================================
// VALID HAX CODE - should NOT be flagged (except indexing warning)
// ============================================================================

const ARRAY_SIZE: usize = 256;

#[derive(Clone, Copy)]
struct ValidStruct {
    data: [u8; ARRAY_SIZE],
    len: usize,
}

impl ValidStruct {
    const fn new() -> Self {
        Self {
            data: [0u8; ARRAY_SIZE],
            len: 0,
        }
    }

    fn wrapping_add(&self, other: &Self) -> Self {
        let mut result = Self::new();
        for i in 0..ARRAY_SIZE {
            result.data[i] = self.data[i].wrapping_add(other.data[i]);
        }
        result
    }
}

fn valid_bounded_iteration(arr: &[u8; 32]) -> u8 {
    let mut sum = 0u8;
    for i in 0..32 {
        sum = sum.wrapping_add(arr[i]);
    }
    sum
}
