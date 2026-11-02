//! Rust core of corpus-dedup-library: MinHash signatures, LSH banding, and clustering.
//!
//! Every function reproduces the Python implementation in `src/corpus_dedup_library`
//! bit for bit: the same splitmix64 mixing, the same FNV-style token and band hashes,
//! the same `(a*h + b) mod (2^61 - 1)` permutation family, and the same whitespace
//! and lowercasing rules. `tests/test_rust_parity.py` checks this on random and
//! adversarial text; the Rust unit tests pin known values.

pub mod cluster;
pub mod lsh;
pub mod minhash;

#[cfg(feature = "python")]
mod python;

pub use cluster::{cluster, cluster_exact, Clusters};
pub use lsh::candidate_pairs;
pub use minhash::{hash_token, shingles, MinHasher};
