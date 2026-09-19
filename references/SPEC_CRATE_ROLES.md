# The three roles of a spec crate under hax-lean

A crate extracted with `haxpipeT` ([hax-lean](https://github.com/spitters/hax-lean))
serves three roles at once. Each role reads a different part of the extraction
and places its own requirement on the Rust. A change to the crate is checked
against all three.

| Role | What it reads | Requirement on the Rust |
|---|---|---|
| 1. Compiler front-end source | the `<fn>_impExpr` AST literals and the `<fn>_secrecy` tables | one function per algorithm of the standard; secrets typed by the secret newtypes; field and curve operations through the `Field` / `ModArith` / `EcGroup` trait surface |
| 2. Crypto-proof anchor | the surface functions and the generated `class <X>Deps` | state threading in the fragment `haxpipeT` writes back; external primitives, and nothing else, behind `<X>Deps` |
| 3. Independent validation | the crate's own top-level functions under `cargo test` | enough of the standard implemented to consume vectors published by the standards body |

## Role 1: compiler front-end source

- Keep one function per algorithm of the standard, so that an emitted kernel
  corresponds to a named item of the specification.
- Declare every modulus as a `pub const`; it travels through the extraction and
  is reconstructed downstream.
- Give a value that must not influence control flow or memory access a secret
  type at its binding, not at its use. The `<fn>_secrecy` table is computed from
  the types of the bindings.

## Role 2: crypto-proof anchor

`haxpipeT` threads a mutation back to the caller for one shape: a function whose
result is `()` and that has exactly one `&mut` parameter
(`HaxLean/ThreadMutations.lean`, `mutWriteParam`). Write state threading in that
fragment, and return everything else by value:

| Write | In place of |
|---|---|
| `fn absorb(x: &mut Xof, data: &[u8])` | — |
| `fn squeeze_byte(x: Xof) -> (Xof, u8)` | `fn squeeze(x: &mut Xof, out: &mut [u8])`, `fn next(x: &mut Xof) -> u8` |
| `fn pack(w: &Poly, out: &mut [u8], at: usize)` | `pack(w, &mut out[a..b])` |
| `let (ok, v) = match f(x) { Some(v) => (true, v), None => (false, 0) }; if ok { … }` | `if let Some(v) = f(x) { a[j] = v; }` in a loop body |
| `match g(x) { Some(h) => Some((z, h)), None => None }` | `g(x).map(\|h\| (z, h))` |
| `let (_, out) = squeeze_64(x); out` | `squeeze_64(x).1` |

An output whose length depends on a parameter set is returned in a buffer of the
largest size, with a function that gives the length in use.

After an extraction, read the generated `class <X>Deps`: it lists the external
primitives of the crate and nothing else.

## Role 3: independent validation

- The expected bytes are read from a file published by the standards body (NIST
  ACVP/CAVP, RFC appendices) and compared with the output of the crate's own
  top-level functions. Identities, round trips and parameter checks do not
  validate a specification: they hold for any self-consistent implementation.
- A crate that implements only kernels cannot consume such vectors. Implement the
  scheme far enough that it can.
- For an arithmetic kernel over a small domain, test the whole domain against the
  postconditions stated in the standard and against a transcription of the
  reference implementation's formula.
- State in `validation.toml` the kind of reference the tests use.
- Record the provenance of every vector file: source, commit, selection.

## When the crate changes

A change to the Rust is complete when all three roles have been rechecked.

1. **Role 3.** `cargo test` in both profiles; `cargo clippy --all-targets -- -D
   warnings`; `cargo doc` with `RUSTDOCFLAGS=-D warnings`; `hax-lint`.
2. **Re-extract.** `cargo hax json`, then `haxpipeT --hax --emit-certified --name
   <X>` into a scratch file. Read `class <X>Deps`, then install the file.
3. **Role 2.** Compute the transitive importers of the regenerated module and check
   each, the language server first, then one build of all of them. A theorem that
   pins a normal form by `rfl` fails exactly where a body changed; the pinned form
   follows the extraction, never the reverse.
4. **Role 1.** Rebuild the modules that lower the `_impExpr` bodies.
5. Commit the Rust, the regenerated extraction and the repaired consumers
   together.
