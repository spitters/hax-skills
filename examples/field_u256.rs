//! Standalone field arithmetic example for Hax extraction
//!
//! This demonstrates Hax-compatible code patterns for 256-bit field arithmetic.
//! No external dependencies except hax-lib.

#![cfg_attr(feature = "hax", feature(register_tool))]
#![cfg_attr(feature = "hax", register_tool(hax))]

use hax_lib as hax;

/// A 256-bit unsigned integer represented as 4 x 64-bit limbs in little-endian order.
/// This is a common representation for cryptographic field elements.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct U256 {
    pub limbs: [u64; 4],
}

impl U256 {
    /// Zero constant
    pub const ZERO: Self = Self { limbs: [0, 0, 0, 0] };

    /// One constant
    pub const ONE: Self = Self { limbs: [1, 0, 0, 0] };

    /// Create a new U256 from limbs (little-endian order)
    pub const fn from_limbs(limbs: [u64; 4]) -> Self {
        Self { limbs }
    }

    /// Create from a single u64 value
    pub const fn from_u64(value: u64) -> Self {
        Self { limbs: [value, 0, 0, 0] }
    }

    /// Check if zero
    pub fn is_zero(&self) -> bool {
        self.limbs[0] == 0 && self.limbs[1] == 0 && self.limbs[2] == 0 && self.limbs[3] == 0
    }

    /// Get a specific limb
    #[hax::requires(i < 4)]
    pub fn limb(&self, i: usize) -> u64 {
        self.limbs[i]
    }

    /// Set a specific limb
    #[hax::requires(i < 4)]
    pub fn set_limb(&mut self, i: usize, value: u64) {
        self.limbs[i] = value;
    }
}

// ============================================================================
// Addition with carry chain
// ============================================================================

/// Add two u64 values with carry in, returning (sum, carry_out)
#[inline]
fn adc(a: u64, b: u64, carry: u64) -> (u64, u64) {
    let sum = a.wrapping_add(b).wrapping_add(carry);
    // Carry occurred if sum < a, or if sum == a and we had a carry/b input
    let carry_out = if sum < a || (sum == a && (b != 0 || carry != 0)) {
        1
    } else {
        0
    };
    (sum, carry_out)
}

/// Add two U256 values, returning (result, carry)
pub fn add_with_carry(a: &U256, b: &U256) -> (U256, u64) {
    let mut result = U256::ZERO;
    let mut carry = 0u64;

    // Unrolled loop for 4 limbs
    let (s0, c0) = adc(a.limbs[0], b.limbs[0], carry);
    result.limbs[0] = s0;
    carry = c0;

    let (s1, c1) = adc(a.limbs[1], b.limbs[1], carry);
    result.limbs[1] = s1;
    carry = c1;

    let (s2, c2) = adc(a.limbs[2], b.limbs[2], carry);
    result.limbs[2] = s2;
    carry = c2;

    let (s3, c3) = adc(a.limbs[3], b.limbs[3], carry);
    result.limbs[3] = s3;
    carry = c3;

    (result, carry)
}

/// Wrapping addition (ignores overflow)
pub fn add(a: &U256, b: &U256) -> U256 {
    let (result, _carry) = add_with_carry(a, b);
    result
}

// ============================================================================
// Subtraction with borrow chain
// ============================================================================

/// Subtract b from a with borrow in, returning (difference, borrow_out)
#[inline]
fn sbb(a: u64, b: u64, borrow: u64) -> (u64, u64) {
    let diff = a.wrapping_sub(b).wrapping_sub(borrow);
    // Borrow occurred if a < b + borrow
    let borrow_out = if a < b || (a == b && borrow != 0) { 1 } else { 0 };
    (diff, borrow_out)
}

/// Subtract b from a, returning (result, borrow)
pub fn sub_with_borrow(a: &U256, b: &U256) -> (U256, u64) {
    let mut result = U256::ZERO;
    let mut borrow = 0u64;

    let (d0, b0) = sbb(a.limbs[0], b.limbs[0], borrow);
    result.limbs[0] = d0;
    borrow = b0;

    let (d1, b1) = sbb(a.limbs[1], b.limbs[1], borrow);
    result.limbs[1] = d1;
    borrow = b1;

    let (d2, b2) = sbb(a.limbs[2], b.limbs[2], borrow);
    result.limbs[2] = d2;
    borrow = b2;

    let (d3, b3) = sbb(a.limbs[3], b.limbs[3], borrow);
    result.limbs[3] = d3;
    borrow = b3;

    (result, borrow)
}

/// Wrapping subtraction
pub fn sub(a: &U256, b: &U256) -> U256 {
    let (result, _borrow) = sub_with_borrow(a, b);
    result
}

// ============================================================================
// Comparison
// ============================================================================

/// Compare two U256 values
/// Returns: -1 if a < b, 0 if a == b, 1 if a > b
pub fn cmp(a: &U256, b: &U256) -> i32 {
    // Compare from most significant limb
    for i in (0..4).rev() {
        if a.limbs[i] < b.limbs[i] {
            return -1;
        }
        if a.limbs[i] > b.limbs[i] {
            return 1;
        }
    }
    0
}

/// Check if a >= b
pub fn gte(a: &U256, b: &U256) -> bool {
    cmp(a, b) >= 0
}

/// Check if a < b
pub fn lt(a: &U256, b: &U256) -> bool {
    cmp(a, b) < 0
}

// ============================================================================
// Bitwise operations
// ============================================================================

/// Bitwise XOR
pub fn xor(a: &U256, b: &U256) -> U256 {
    U256 {
        limbs: [
            a.limbs[0] ^ b.limbs[0],
            a.limbs[1] ^ b.limbs[1],
            a.limbs[2] ^ b.limbs[2],
            a.limbs[3] ^ b.limbs[3],
        ],
    }
}

/// Bitwise AND
pub fn and(a: &U256, b: &U256) -> U256 {
    U256 {
        limbs: [
            a.limbs[0] & b.limbs[0],
            a.limbs[1] & b.limbs[1],
            a.limbs[2] & b.limbs[2],
            a.limbs[3] & b.limbs[3],
        ],
    }
}

/// Bitwise OR
pub fn or(a: &U256, b: &U256) -> U256 {
    U256 {
        limbs: [
            a.limbs[0] | b.limbs[0],
            a.limbs[1] | b.limbs[1],
            a.limbs[2] | b.limbs[2],
            a.limbs[3] | b.limbs[3],
        ],
    }
}

/// Left shift by n bits (n < 256)
#[hax::requires(n < 256)]
pub fn shl(a: &U256, n: u32) -> U256 {
    if n == 0 {
        return *a;
    }
    if n >= 256 {
        return U256::ZERO;
    }

    let mut result = U256::ZERO;
    let limb_shift = (n / 64) as usize;
    let bit_shift = n % 64;

    if bit_shift == 0 {
        // Aligned shift - just move limbs
        for i in limb_shift..4 {
            result.limbs[i] = a.limbs[i - limb_shift];
        }
    } else {
        // Need to combine bits from adjacent limbs
        for i in limb_shift..4 {
            let src_idx = i - limb_shift;
            result.limbs[i] = a.limbs[src_idx] << bit_shift;
            if src_idx > 0 {
                result.limbs[i] |= a.limbs[src_idx - 1] >> (64 - bit_shift);
            }
        }
    }

    result
}

/// Right shift by n bits (n < 256)
#[hax::requires(n < 256)]
pub fn shr(a: &U256, n: u32) -> U256 {
    if n == 0 {
        return *a;
    }
    if n >= 256 {
        return U256::ZERO;
    }

    let mut result = U256::ZERO;
    let limb_shift = (n / 64) as usize;
    let bit_shift = n % 64;

    if bit_shift == 0 {
        for i in 0..(4 - limb_shift) {
            result.limbs[i] = a.limbs[i + limb_shift];
        }
    } else {
        for i in 0..(4 - limb_shift) {
            let src_idx = i + limb_shift;
            result.limbs[i] = a.limbs[src_idx] >> bit_shift;
            if src_idx < 3 {
                result.limbs[i] |= a.limbs[src_idx + 1] << (64 - bit_shift);
            }
        }
    }

    result
}

// ============================================================================
// Multiplication (schoolbook, produces 512-bit result)
// ============================================================================

/// Multiply two u64 values, returning (low, high) of 128-bit result
#[inline]
fn mul64(a: u64, b: u64) -> (u64, u64) {
    let full = (a as u128).wrapping_mul(b as u128);
    (full as u64, (full >> 64) as u64)
}

/// Multiply-accumulate: acc += a * b, returning carry
#[inline]
fn mac(acc: &mut u64, a: u64, b: u64, carry: u64) -> u64 {
    let (lo, hi) = mul64(a, b);
    let (sum1, c1) = acc.overflowing_add(lo);
    let (sum2, c2) = sum1.overflowing_add(carry);
    *acc = sum2;
    hi.wrapping_add(c1 as u64).wrapping_add(c2 as u64)
}

/// 512-bit result of U256 multiplication
#[derive(Clone, Copy, Debug)]
pub struct U512 {
    pub limbs: [u64; 8],
}

/// Full multiplication producing 512-bit result
pub fn mul_wide(a: &U256, b: &U256) -> U512 {
    let mut result = U512 { limbs: [0u64; 8] };

    // Schoolbook multiplication
    for i in 0..4 {
        let mut carry = 0u64;
        for j in 0..4 {
            carry = mac(&mut result.limbs[i + j], a.limbs[i], b.limbs[j], carry);
        }
        result.limbs[i + 4] = carry;
    }

    result
}

// ============================================================================
// Modular arithmetic (for a fixed modulus)
// ============================================================================

/// Example modulus: a 255-bit prime (similar to Curve25519's field)
/// p = 2^255 - 19
pub const MODULUS: U256 = U256 {
    limbs: [
        0xFFFFFFFFFFFFFFED, // 2^64 - 19
        0xFFFFFFFFFFFFFFFF,
        0xFFFFFFFFFFFFFFFF,
        0x7FFFFFFFFFFFFFFF, // 2^63 - 1
    ],
};

/// Modular addition: (a + b) mod p
pub fn mod_add(a: &U256, b: &U256, p: &U256) -> U256 {
    let (sum, carry) = add_with_carry(a, b);

    // If carry or sum >= p, subtract p
    if carry != 0 || gte(&sum, p) {
        let (result, _) = sub_with_borrow(&sum, p);
        result
    } else {
        sum
    }
}

/// Modular subtraction: (a - b) mod p
pub fn mod_sub(a: &U256, b: &U256, p: &U256) -> U256 {
    let (diff, borrow) = sub_with_borrow(a, b);

    // If borrow, add p back
    if borrow != 0 {
        let (result, _) = add_with_carry(&diff, p);
        result
    } else {
        diff
    }
}

/// Modular negation: (-a) mod p = p - a
pub fn mod_neg(a: &U256, p: &U256) -> U256 {
    if a.is_zero() {
        U256::ZERO
    } else {
        sub(p, a)
    }
}

// ============================================================================
// Serialization (to/from bytes)
// ============================================================================

/// Convert U256 to 32 bytes (little-endian)
pub fn to_bytes(a: &U256) -> [u8; 32] {
    let mut result = [0u8; 32];

    for i in 0..4 {
        let limb_bytes = a.limbs[i].to_le_bytes();
        for j in 0..8 {
            result[i * 8 + j] = limb_bytes[j];
        }
    }

    result
}

/// Convert 32 bytes to U256 (little-endian)
pub fn from_bytes(bytes: &[u8; 32]) -> U256 {
    let mut limbs = [0u64; 4];

    for i in 0..4 {
        let mut limb_bytes = [0u8; 8];
        for j in 0..8 {
            limb_bytes[j] = bytes[i * 8 + j];
        }
        limbs[i] = u64::from_le_bytes(limb_bytes);
    }

    U256 { limbs }
}

// ============================================================================
// Constant-time operations (for cryptographic use)
// ============================================================================

/// Constant-time conditional select: returns a if choice == 0, b if choice == 1
/// IMPORTANT: choice must be 0 or 1
#[hax::requires(choice == 0 || choice == 1)]
pub fn ct_select(a: &U256, b: &U256, choice: u64) -> U256 {
    let mask = 0u64.wrapping_sub(choice); // 0 or 0xFFFF...

    U256 {
        limbs: [
            a.limbs[0] ^ (mask & (a.limbs[0] ^ b.limbs[0])),
            a.limbs[1] ^ (mask & (a.limbs[1] ^ b.limbs[1])),
            a.limbs[2] ^ (mask & (a.limbs[2] ^ b.limbs[2])),
            a.limbs[3] ^ (mask & (a.limbs[3] ^ b.limbs[3])),
        ],
    }
}

/// Constant-time equality comparison
pub fn ct_eq(a: &U256, b: &U256) -> bool {
    let mut acc = 0u64;
    for i in 0..4 {
        acc |= a.limbs[i] ^ b.limbs[i];
    }
    acc == 0
}

/// Constant-time conditional swap
#[hax::requires(choice == 0 || choice == 1)]
pub fn ct_swap(a: &mut U256, b: &mut U256, choice: u64) {
    let mask = 0u64.wrapping_sub(choice);

    for i in 0..4 {
        let t = mask & (a.limbs[i] ^ b.limbs[i]);
        a.limbs[i] ^= t;
        b.limbs[i] ^= t;
    }
}

// ============================================================================
// Tests (these won't be extracted but verify correctness)
// ============================================================================

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_add_basic() {
        let a = U256::from_u64(100);
        let b = U256::from_u64(200);
        let sum = add(&a, &b);
        assert_eq!(sum.limbs[0], 300);
        assert_eq!(sum.limbs[1], 0);
    }

    #[test]
    fn test_add_carry() {
        let a = U256::from_limbs([u64::MAX, 0, 0, 0]);
        let b = U256::from_limbs([1, 0, 0, 0]);
        let sum = add(&a, &b);
        assert_eq!(sum.limbs[0], 0);
        assert_eq!(sum.limbs[1], 1);
    }

    #[test]
    fn test_sub_basic() {
        let a = U256::from_u64(300);
        let b = U256::from_u64(100);
        let diff = sub(&a, &b);
        assert_eq!(diff.limbs[0], 200);
    }

    #[test]
    fn test_mod_add() {
        let p = U256::from_u64(17);
        let a = U256::from_u64(15);
        let b = U256::from_u64(10);
        let result = mod_add(&a, &b, &p);
        assert_eq!(result.limbs[0], 8); // (15 + 10) mod 17 = 8
    }

    #[test]
    fn test_ct_select() {
        let a = U256::from_u64(42);
        let b = U256::from_u64(99);

        let selected_a = ct_select(&a, &b, 0);
        let selected_b = ct_select(&a, &b, 1);

        assert_eq!(selected_a.limbs[0], 42);
        assert_eq!(selected_b.limbs[0], 99);
    }

    #[test]
    fn test_serialization_roundtrip() {
        let original = U256::from_limbs([0x123456789ABCDEF0, 0xFEDCBA9876543210, 0x1111111111111111, 0x2222222222222222]);
        let bytes = to_bytes(&original);
        let recovered = from_bytes(&bytes);
        assert!(ct_eq(&original, &recovered));
    }
}
