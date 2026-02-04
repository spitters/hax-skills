;; hax-lint.scm - Tree-sitter queries for Hax-compatible Rust validation
;;
;; Usage: Run these queries against tree-sitter-rust parsed AST
;; All captures are violations that must be fixed for Hax extraction
;;
;; Severity levels:
;;   @error   - Will definitely fail Hax extraction
;;   @warning - Likely to fail or cause issues
;;
;; Reference: https://hax.rs (Hax documentation)
;;
;; NOTE: This is a conservative subset tested against tree-sitter-rust 0.21+

;; ============================================================================
;; UNSAFE CODE (Critical - Hax requires safe Rust only)
;; ============================================================================

;; unsafe blocks: unsafe { ... }
(unsafe_block) @error.unsafe_block

;; Note: unsafe functions/traits/impls are harder to match with tree-sitter
;; The unsafe_block pattern catches most cases

;; ============================================================================
;; RAW POINTERS (Not extractable to functional languages)
;; ============================================================================

;; *const T and *mut T
(pointer_type) @error.raw_pointer

;; ============================================================================
;; TRAIT OBJECTS / DYNAMIC DISPATCH (No runtime polymorphism)
;; ============================================================================

;; dyn Trait (dynamic_type in tree-sitter-rust)
(dynamic_type) @error.dyn_trait

;; ============================================================================
;; HEAP ALLOCATION (Hax targets no_std, stack-only allocation)
;; ============================================================================

;; Vec<T>
((type_identifier) @error.heap_vec
  (#eq? @error.heap_vec "Vec"))

;; Box<T>
((type_identifier) @error.heap_box
  (#eq? @error.heap_box "Box"))

;; String
((type_identifier) @error.heap_string
  (#eq? @error.heap_string "String"))

;; Rc<T>
((type_identifier) @error.heap_rc
  (#eq? @error.heap_rc "Rc"))

;; Arc<T>
((type_identifier) @error.heap_arc
  (#eq? @error.heap_arc "Arc"))

;; HashMap
((type_identifier) @error.heap_hashmap
  (#eq? @error.heap_hashmap "HashMap"))

;; HashSet
((type_identifier) @error.heap_hashset
  (#eq? @error.heap_hashset "HashSet"))

;; ============================================================================
;; UNBOUNDED LOOPS (All iteration must be bounded for extraction)
;; ============================================================================

;; loop { ... } - infinite loops
(loop_expression) @error.unbounded_loop

;; while condition { ... } - potentially unbounded
(while_expression) @error.while_loop

;; ============================================================================
;; ASYNC / AWAIT (Not extractable)
;; ============================================================================

;; await expressions: foo.await
(await_expression) @error.await_expr

;; Note: async functions are detected via function_modifiers containing "async"
;; but tree-sitter pattern matching for literals in function_modifiers is tricky

;; ============================================================================
;; INTERIOR MUTABILITY (Breaks functional extraction)
;; ============================================================================

;; Cell<T>
((type_identifier) @error.interior_cell
  (#eq? @error.interior_cell "Cell"))

;; RefCell<T>
((type_identifier) @error.interior_refcell
  (#eq? @error.interior_refcell "RefCell"))

;; Mutex<T>
((type_identifier) @error.interior_mutex
  (#eq? @error.interior_mutex "Mutex"))

;; RwLock<T>
((type_identifier) @error.interior_rwlock
  (#eq? @error.interior_rwlock "RwLock"))

;; ============================================================================
;; GLOBAL / STATIC MUTABLE STATE
;; ============================================================================

;; static mut - mutable statics
(static_item
  (mutable_specifier) @error.static_mut)

;; ============================================================================
;; UNION TYPES (Require unsafe to access)
;; ============================================================================

(union_item) @error.union

;; ============================================================================
;; FFI / EXTERN (Cannot extract foreign interfaces)
;; ============================================================================

;; extern blocks (foreign_mod_item in tree-sitter-rust)
(foreign_mod_item) @error.extern_block

;; ============================================================================
;; PANICKING / UNWINDING (Must be total functions)
;; ============================================================================

;; panic! macro
((macro_invocation
  macro: (identifier) @warning.panic)
  (#eq? @warning.panic "panic"))

;; todo! macro
((macro_invocation
  macro: (identifier) @warning.todo)
  (#eq? @warning.todo "todo"))

;; unimplemented! macro
((macro_invocation
  macro: (identifier) @warning.unimplemented)
  (#eq? @warning.unimplemented "unimplemented"))

;; unreachable! macro
((macro_invocation
  macro: (identifier) @warning.unreachable)
  (#eq? @warning.unreachable "unreachable"))

;; .unwrap() calls
((call_expression
  function: (field_expression
    field: (field_identifier) @warning.unwrap))
  (#eq? @warning.unwrap "unwrap"))

;; .expect() calls
((call_expression
  function: (field_expression
    field: (field_identifier) @warning.expect))
  (#eq? @warning.expect "expect"))

;; ============================================================================
;; I/O OPERATIONS (Pure functions cannot do I/O)
;; ============================================================================

;; println!, print!, eprintln!, eprint!
((macro_invocation
  macro: (identifier) @warning.println)
  (#eq? @warning.println "println"))

((macro_invocation
  macro: (identifier) @warning.print)
  (#eq? @warning.print "print"))

;; dbg! macro
((macro_invocation
  macro: (identifier) @warning.dbg)
  (#eq? @warning.dbg "dbg"))

;; ============================================================================
;; ALLOCATION FUNCTIONS
;; ============================================================================

;; vec! macro
((macro_invocation
  macro: (identifier) @error.vec_macro)
  (#eq? @error.vec_macro "vec"))

;; format! macro (allocates String)
((macro_invocation
  macro: (identifier) @error.format_macro)
  (#eq? @error.format_macro "format"))

;; ============================================================================
;; FLOATING POINT (Often excluded for cryptographic code)
;; ============================================================================

;; f32 type
((primitive_type) @warning.float_f32
  (#eq? @warning.float_f32 "f32"))

;; f64 type
((primitive_type) @warning.float_f64
  (#eq? @warning.float_f64 "f64"))

;; ============================================================================
;; THREADING (Single-threaded extraction only)
;; ============================================================================

;; Atomic types
((type_identifier) @error.atomic
  (#match? @error.atomic "^Atomic"))
