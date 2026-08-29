# Hax Code Patterns

Reusable patterns for writing Hax-compatible Rust code.

## Data Structure Patterns

### Bounded Buffer

Fixed-capacity buffer with tracked length:

```rust
#[derive(Clone, Copy)]
pub struct Buffer<const N: usize> {
    data: [u8; N],
    len: usize,
}

impl<const N: usize> Buffer<N> {
    pub fn new() -> Self {
        Buffer { data: [0u8; N], len: 0 }
    }
    
    pub fn len(&self) -> usize {
        self.len
    }
    
    pub fn is_empty(&self) -> bool {
        self.len == 0
    }
    
    pub fn is_full(&self) -> bool {
        self.len >= N
    }
    
    #[hax::requires(!self.is_full())]
    pub fn push(&mut self, byte: u8) {
        self.data[self.len] = byte;
        self.len = self.len.wrapping_add(1);
    }
    
    #[hax::requires(!self.is_empty())]
    pub fn pop(&mut self) -> u8 {
        self.len = self.len.wrapping_sub(1);
        self.data[self.len]
    }
    
    #[hax::requires(index < self.len)]
    pub fn get(&self, index: usize) -> u8 {
        self.data[index]
    }
    
    #[hax::requires(index < self.len)]
    pub fn set(&mut self, index: usize, value: u8) {
        self.data[index] = value;
    }
    
    pub fn clear(&mut self) {
        self.len = 0;
    }
    
    pub fn as_slice(&self) -> &[u8; N] {
        &self.data
    }
}
```

### Index-Based Linked Structure

Use indices instead of pointers for linked data:

```rust
const MAX_NODES: usize = 256;

#[derive(Clone, Copy, Default)]
pub struct Node {
    value: u32,
    next: Option<usize>,
    prev: Option<usize>,
}

#[derive(Clone, Copy)]
pub struct LinkedList {
    nodes: [Node; MAX_NODES],
    head: Option<usize>,
    tail: Option<usize>,
    free: usize,
}

impl LinkedList {
    pub fn new() -> Self {
        LinkedList {
            nodes: [Node::default(); MAX_NODES],
            head: None,
            tail: None,
            free: 0,
        }
    }
    
    #[hax::requires(self.free < MAX_NODES)]
    pub fn push_back(&mut self, value: u32) {
        let idx = self.free;
        self.free = self.free.wrapping_add(1);
        
        self.nodes[idx] = Node {
            value,
            next: None,
            prev: self.tail,
        };
        
        if let Some(tail_idx) = self.tail {
            self.nodes[tail_idx].next = Some(idx);
        }
        
        self.tail = Some(idx);
        
        if self.head.is_none() {
            self.head = Some(idx);
        }
    }
    
    pub fn iter(&self) -> LinkedListIter {
        LinkedListIter {
            list: self,
            current: self.head,
        }
    }
}

pub struct LinkedListIter<'a> {
    list: &'a LinkedList,
    current: Option<usize>,
}

impl<'a> LinkedListIter<'a> {
    pub fn next(&mut self) -> Option<u32> {
        match self.current {
            Some(idx) => {
                let node = &self.list.nodes[idx];
                self.current = node.next;
                Some(node.value)
            }
            None => None,
        }
    }
}
```

### Fixed-Size Map (Linear Search)

When you need key-value storage with known bounds:

```rust
const MAX_ENTRIES: usize = 64;

#[derive(Clone, Copy)]
pub struct Entry<K: Copy + PartialEq, V: Copy> {
    key: K,
    value: V,
    occupied: bool,
}

impl<K: Copy + PartialEq + Default, V: Copy + Default> Default for Entry<K, V> {
    fn default() -> Self {
        Entry {
            key: K::default(),
            value: V::default(),
            occupied: false,
        }
    }
}

#[derive(Clone, Copy)]
pub struct FixedMap<K: Copy + PartialEq + Default, V: Copy + Default> {
    entries: [Entry<K, V>; MAX_ENTRIES],
    len: usize,
}

impl<K: Copy + PartialEq + Default, V: Copy + Default> FixedMap<K, V> {
    pub fn new() -> Self {
        FixedMap {
            entries: [Entry::default(); MAX_ENTRIES],
            len: 0,
        }
    }
    
    pub fn get(&self, key: &K) -> Option<V> {
        for i in 0..self.len {
            if self.entries[i].occupied && self.entries[i].key == *key {
                return Some(self.entries[i].value);
            }
        }
        None
    }
    
    #[hax::requires(self.len < MAX_ENTRIES || self.get(key).is_some())]
    pub fn insert(&mut self, key: K, value: V) {
        // Check for existing key
        for i in 0..self.len {
            if self.entries[i].occupied && self.entries[i].key == key {
                self.entries[i].value = value;
                return;
            }
        }
        
        // Insert new entry
        self.entries[self.len] = Entry {
            key,
            value,
            occupied: true,
        };
        self.len = self.len.wrapping_add(1);
    }
    
    pub fn contains(&self, key: &K) -> bool {
        self.get(key).is_some()
    }
}
```

## Cryptographic Patterns

### Constant-Time Operations

Prevent timing side channels:

```rust
/// Constant-time byte comparison
pub fn ct_eq(a: &[u8; 32], b: &[u8; 32]) -> bool {
    let mut acc = 0u8;
    for i in 0..32 {
        acc |= a[i] ^ b[i];
    }
    acc == 0
}

/// Constant-time conditional select: returns a if choice == 1, b if choice == 0
#[hax::requires(choice == 0 || choice == 1)]
pub fn ct_select(a: u32, b: u32, choice: u8) -> u32 {
    let mask = 0u32.wrapping_sub(choice as u32);
    (a & mask) | (b & !mask)
}

/// Constant-time conditional swap
#[hax::requires(choice == 0 || choice == 1)]
pub fn ct_swap(a: &mut u32, b: &mut u32, choice: u8) {
    let mask = 0u32.wrapping_sub(choice as u32);
    let t = mask & (*a ^ *b);
    *a ^= t;
    *b ^= t;
}

/// Constant-time is_zero check
pub fn ct_is_zero(x: u32) -> u8 {
    let z = x | x.wrapping_neg();
    ((z >> 31) ^ 1) as u8
}

/// Constant-time less-than comparison
pub fn ct_lt(a: u32, b: u32) -> u8 {
    ((a.wrapping_sub(b)) >> 31) as u8
}
```

### Block Cipher Structure

Template for block cipher implementations:

```rust
const BLOCK_SIZE: usize = 16;
const KEY_SIZE: usize = 32;
const ROUNDS: usize = 10;

#[derive(Clone, Copy)]
pub struct Block([u8; BLOCK_SIZE]);

#[derive(Clone, Copy)]
pub struct Key([u8; KEY_SIZE]);

#[derive(Clone, Copy)]
pub struct RoundKeys([Block; ROUNDS + 1]);

impl Block {
    pub fn new() -> Self {
        Block([0u8; BLOCK_SIZE])
    }
    
    pub fn from_bytes(bytes: &[u8; BLOCK_SIZE]) -> Self {
        Block(*bytes)
    }
    
    pub fn xor(&mut self, other: &Block) {
        for i in 0..BLOCK_SIZE {
            self.0[i] ^= other.0[i];
        }
    }
    
    pub fn to_bytes(&self) -> [u8; BLOCK_SIZE] {
        self.0
    }
}

pub fn key_schedule(key: &Key) -> RoundKeys {
    let mut round_keys = [Block::new(); ROUNDS + 1];
    
    // First round key is just the key (simplified)
    for i in 0..BLOCK_SIZE {
        round_keys[0].0[i] = key.0[i];
    }
    
    // Derive subsequent round keys
    for r in 1..=ROUNDS {
        for i in 0..BLOCK_SIZE {
            round_keys[r].0[i] = round_keys[r - 1].0[i]
                .wrapping_add(r as u8)
                .rotate_left(3);
        }
    }
    
    RoundKeys(round_keys)
}

pub fn encrypt_block(block: &mut Block, round_keys: &RoundKeys) {
    for r in 0..ROUNDS {
        block.xor(&round_keys.0[r]);
        // Apply round function (substitution, permutation, etc.)
        apply_round(block);
    }
    block.xor(&round_keys.0[ROUNDS]);
}

fn apply_round(block: &mut Block) {
    // Example round function
    for i in 0..BLOCK_SIZE {
        block.0[i] = sbox(block.0[i]);
    }
    // Permutation
    let tmp = block.0;
    for i in 0..BLOCK_SIZE {
        block.0[i] = tmp[(i.wrapping_mul(5).wrapping_add(3)) % BLOCK_SIZE];
    }
}

fn sbox(x: u8) -> u8 {
    // Simple substitution (replace with actual S-box)
    x.wrapping_mul(7).wrapping_add(11).rotate_left(3)
}
```

### Hash Function Structure

Template for hash function implementations:

```rust
const HASH_BLOCK_SIZE: usize = 64;
const HASH_OUTPUT_SIZE: usize = 32;
const HASH_STATE_SIZE: usize = 8;

#[derive(Clone, Copy)]
pub struct HashState {
    state: [u32; HASH_STATE_SIZE],
    buffer: [u8; HASH_BLOCK_SIZE],
    buffer_len: usize,
    total_len: u64,
}

impl HashState {
    pub fn new() -> Self {
        HashState {
            state: [
                0x6a09e667, 0xbb67ae85, 0x3c6ef372, 0xa54ff53a,
                0x510e527f, 0x9b05688c, 0x1f83d9ab, 0x5be0cd19,
            ],
            buffer: [0u8; HASH_BLOCK_SIZE],
            buffer_len: 0,
            total_len: 0,
        }
    }
    
    pub fn update(&mut self, data: &[u8; 64], data_len: usize) {
        for i in 0..data_len {
            if self.buffer_len == HASH_BLOCK_SIZE {
                self.compress();
                self.buffer_len = 0;
            }
            self.buffer[self.buffer_len] = data[i];
            self.buffer_len = self.buffer_len.wrapping_add(1);
            self.total_len = self.total_len.wrapping_add(1);
        }
    }
    
    pub fn finalize(&mut self) -> [u8; HASH_OUTPUT_SIZE] {
        // Padding
        self.buffer[self.buffer_len] = 0x80;
        self.buffer_len = self.buffer_len.wrapping_add(1);
        
        // If not enough space for length, compress and start new block
        if self.buffer_len > HASH_BLOCK_SIZE - 8 {
            while self.buffer_len < HASH_BLOCK_SIZE {
                self.buffer[self.buffer_len] = 0;
                self.buffer_len = self.buffer_len.wrapping_add(1);
            }
            self.compress();
            self.buffer_len = 0;
        }
        
        // Pad to length field position
        while self.buffer_len < HASH_BLOCK_SIZE - 8 {
            self.buffer[self.buffer_len] = 0;
            self.buffer_len = self.buffer_len.wrapping_add(1);
        }
        
        // Append length in bits
        let bit_len = self.total_len.wrapping_mul(8);
        let len_bytes = bit_len.to_be_bytes();
        for i in 0..8 {
            self.buffer[HASH_BLOCK_SIZE - 8 + i] = len_bytes[i];
        }
        
        self.compress();
        
        // Convert state to bytes
        let mut output = [0u8; HASH_OUTPUT_SIZE];
        for i in 0..HASH_STATE_SIZE {
            let bytes = self.state[i].to_be_bytes();
            for j in 0..4 {
                output[i * 4 + j] = bytes[j];
            }
        }
        output
    }
    
    fn compress(&mut self) {
        // Compression function (simplified)
        let mut w = [0u32; 64];
        
        // Message schedule
        for i in 0..16 {
            w[i] = u32::from_be_bytes([
                self.buffer[i * 4],
                self.buffer[i * 4 + 1],
                self.buffer[i * 4 + 2],
                self.buffer[i * 4 + 3],
            ]);
        }
        
        for i in 16..64 {
            let s0 = w[i - 15].rotate_right(7) 
                   ^ w[i - 15].rotate_right(18) 
                   ^ (w[i - 15] >> 3);
            let s1 = w[i - 2].rotate_right(17) 
                   ^ w[i - 2].rotate_right(19) 
                   ^ (w[i - 2] >> 10);
            w[i] = w[i - 16]
                .wrapping_add(s0)
                .wrapping_add(w[i - 7])
                .wrapping_add(s1);
        }
        
        // Working variables
        let mut h = self.state;
        
        // Compression rounds (simplified)
        for i in 0..64 {
            let s1 = h[4].rotate_right(6) 
                   ^ h[4].rotate_right(11) 
                   ^ h[4].rotate_right(25);
            let ch = (h[4] & h[5]) ^ ((!h[4]) & h[6]);
            let temp1 = h[7]
                .wrapping_add(s1)
                .wrapping_add(ch)
                .wrapping_add(w[i]);
            let s0 = h[0].rotate_right(2) 
                   ^ h[0].rotate_right(13) 
                   ^ h[0].rotate_right(22);
            let maj = (h[0] & h[1]) ^ (h[0] & h[2]) ^ (h[1] & h[2]);
            let temp2 = s0.wrapping_add(maj);
            
            h[7] = h[6];
            h[6] = h[5];
            h[5] = h[4];
            h[4] = h[3].wrapping_add(temp1);
            h[3] = h[2];
            h[2] = h[1];
            h[1] = h[0];
            h[0] = temp1.wrapping_add(temp2);
        }
        
        // Update state
        for i in 0..HASH_STATE_SIZE {
            self.state[i] = self.state[i].wrapping_add(h[i]);
        }
    }
}
```

## State Machine Pattern

For protocol implementations:

```rust
#[derive(Clone, Copy, PartialEq, Eq)]
pub enum ProtocolState {
    Init,
    WaitingForHello,
    WaitingForKey,
    Established,
    Closed,
    Error,
}

#[derive(Clone, Copy)]
pub struct Protocol {
    state: ProtocolState,
    session_key: [u8; 32],
    sequence: u32,
}

#[derive(Clone, Copy)]
pub enum Message {
    Hello { version: u8 },
    KeyExchange { public_key: [u8; 32] },
    Data { payload: [u8; 64], len: usize },
    Close,
}

#[derive(Clone, Copy)]
pub enum ProtocolError {
    InvalidState,
    InvalidMessage,
    CryptoError,
}

impl Protocol {
    pub fn new() -> Self {
        Protocol {
            state: ProtocolState::Init,
            session_key: [0u8; 32],
            sequence: 0,
        }
    }
    
    pub fn state(&self) -> ProtocolState {
        self.state
    }
    
    pub fn process(&mut self, msg: Message) -> Result<Option<Message>, ProtocolError> {
        match (self.state, msg) {
            (ProtocolState::Init, Message::Hello { version }) => {
                if version == 1 {
                    self.state = ProtocolState::WaitingForKey;
                    Ok(Some(Message::Hello { version: 1 }))
                } else {
                    self.state = ProtocolState::Error;
                    Err(ProtocolError::InvalidMessage)
                }
            }
            
            (ProtocolState::WaitingForKey, Message::KeyExchange { public_key }) => {
                // Derive session key (simplified)
                for i in 0..32 {
                    self.session_key[i] = public_key[i] ^ 0x5A;
                }
                self.state = ProtocolState::Established;
                Ok(Some(Message::KeyExchange { 
                    public_key: [0x42u8; 32] 
                }))
            }
            
            (ProtocolState::Established, Message::Data { payload, len }) => {
                // Process data
                self.sequence = self.sequence.wrapping_add(1);
                Ok(None)
            }
            
            (ProtocolState::Established, Message::Close) => {
                self.state = ProtocolState::Closed;
                Ok(Some(Message::Close))
            }
            
            _ => {
                self.state = ProtocolState::Error;
                Err(ProtocolError::InvalidState)
            }
        }
    }
}
```

## Specification Patterns

### Pre/Post Conditions

```rust
use hax_lib as hax;

/// Binary search with full specification
#[hax::requires(arr.windows(2).all(|w| w[0] <= w[1]))]  // Array is sorted
#[hax::ensures(|result| match result {
    Some(i) => i < N && arr[i] == target,
    None => arr.iter().all(|&x| x != target)
})]
pub fn binary_search<const N: usize>(
    arr: &[u32; N], 
    target: u32
) -> Option<usize> {
    if N == 0 {
        return None;
    }
    
    let mut low = 0usize;
    let mut high = N;
    
    while low < high {
        let mid = low.wrapping_add((high.wrapping_sub(low)) / 2);
        
        if arr[mid] == target {
            return Some(mid);
        } else if arr[mid] < target {
            low = mid.wrapping_add(1);
        } else {
            high = mid;
        }
    }
    
    None
}

/// Safe division with specification
#[hax::requires(divisor != 0)]
#[hax::ensures(|result| result * divisor <= dividend)]
pub fn safe_div(dividend: u32, divisor: u32) -> u32 {
    dividend / divisor
}

/// Memory copy with overlap check
#[hax::requires(
    src_start + len <= N && 
    dst_start + len <= N &&
    (src_start >= dst_start + len || dst_start >= src_start + len)
)]
pub fn copy_within<const N: usize>(
    arr: &mut [u8; N],
    src_start: usize,
    dst_start: usize,
    len: usize,
) {
    for i in 0..len {
        arr[dst_start + i] = arr[src_start + i];
    }
}
```

### Loop Invariants

```rust
use hax_lib as hax;

/// Sum with loop invariant
pub fn sum_array<const N: usize>(arr: &[u32; N]) -> u32 {
    let mut sum = 0u32;

    for i in 0..N {
        hax_lib::loop_invariant!(|i: usize| {
            i <= N &&
            sum == arr[0..i].iter().fold(0u32, |a, &b| a.wrapping_add(b))
        });
        sum = sum.wrapping_add(arr[i]);
    }

    sum
}

/// Maximum with invariant
pub fn find_max<const N: usize>(arr: &[u32; N]) -> u32 
where
    [(); N]: ,  // N > 0 requirement
{
    let mut max = arr[0];

    for i in 1..N {
        hax_lib::loop_invariant!(|i: usize| {
            i <= N &&
            arr[0..i].iter().all(|&x| x <= max) &&
            arr[0..i].iter().any(|&x| x == max)
        });
        if arr[i] > max {
            max = arr[i];
        }
    }

    max
}
```

The invariant is a function-like macro on the first line of the loop body,
taking the loop variable as its argument; other loop-carried variables are
referenced from the enclosing scope.
