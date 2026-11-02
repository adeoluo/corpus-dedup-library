//! MinHash signatures over hashed word shingles.

use rayon::prelude::*;
use std::collections::HashSet;

const PRIME: u64 = (1 << 61) - 1;

/// splitmix64 finalizer, identical to `_mix64` in the Python implementation.
#[inline]
pub fn mix64(value: u64) -> u64 {
    let mut v = value.wrapping_add(0x9E37_79B9_7F4A_7C15);
    v = (v ^ (v >> 30)).wrapping_mul(0xBF58_476D_1CE4_E5B9);
    v = (v ^ (v >> 27)).wrapping_mul(0x94D0_49BB_1331_11EB);
    v ^ (v >> 31)
}

/// Hash a token by code point, as Python's `hash_token` iterates `ord(ch)`.
pub fn hash_token(token: &str) -> u64 {
    let acc = token.chars().fold(0u64, |acc, ch| {
        acc.wrapping_mul(1_099_511_628_211).wrapping_add(ch as u64)
    });
    mix64(acc)
}

/// Python's `str.split()` separators: Unicode White_Space plus U+001C..U+001F.
#[inline]
fn is_python_space(c: char) -> bool {
    c.is_whitespace() || ('\u{1c}'..='\u{1f}').contains(&c)
}

/// The set of hashed word `k`-shingles of `text`, after lowercasing.
pub fn shingles(text: &str, k: usize) -> HashSet<u64> {
    let lowered = text.to_lowercase();
    let words: Vec<&str> = lowered
        .split(is_python_space)
        .filter(|w| !w.is_empty())
        .collect();
    let mut out = HashSet::new();
    if words.is_empty() {
        return out;
    }
    if words.len() < k {
        out.insert(hash_token(&words.join(" ")));
        return out;
    }
    let mut buf = String::new();
    for window in words.windows(k) {
        buf.clear();
        for (i, w) in window.iter().enumerate() {
            if i > 0 {
                buf.push(' ');
            }
            buf.push_str(w);
        }
        out.insert(hash_token(&buf));
    }
    out
}

/// A fixed family of `num_perm` hash permutations, derived from `seed`.
#[derive(Clone, Debug)]
pub struct MinHasher {
    pub num_perm: usize,
    pub k: usize,
    a: Vec<u64>,
    b: Vec<u64>,
}

impl MinHasher {
    pub fn new(num_perm: usize, k: usize, seed: u64) -> Self {
        let mut state = mix64(seed.wrapping_add(1));
        let mut a = Vec::with_capacity(num_perm);
        let mut b = Vec::with_capacity(num_perm);
        for _ in 0..num_perm {
            state = mix64(state);
            a.push(1 + state % (PRIME - 1));
            state = mix64(state);
            b.push(state % PRIME);
        }
        Self { num_perm, k, a, b }
    }

    /// The MinHash signature of `text`; all zeros for text with no shingles.
    pub fn signature(&self, text: &str) -> Vec<u64> {
        let hashes: Vec<u64> = shingles(text, self.k).into_iter().collect();
        if hashes.is_empty() {
            return vec![0; self.num_perm];
        }
        self.a
            .iter()
            .zip(&self.b)
            .map(|(&a, &b)| {
                hashes
                    .iter()
                    .map(|&h| ((a as u128 * h as u128 + b as u128) % PRIME as u128) as u64)
                    .min()
                    .unwrap_or(0)
            })
            .collect()
    }

    /// Signatures for many documents, computed in parallel.
    pub fn signatures(&self, texts: &[String]) -> Vec<Vec<u64>> {
        texts.par_iter().map(|t| self.signature(t)).collect()
    }
}

/// Fraction of agreeing positions: the MinHash estimate of Jaccard similarity.
pub fn estimated_jaccard(a: &[u64], b: &[u64]) -> f64 {
    if a.is_empty() {
        return 0.0;
    }
    let agree = a.iter().zip(b).filter(|(x, y)| x == y).count();
    agree as f64 / a.len() as f64
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn mix_and_token_hash_match_python() {
        // Values computed with the Python implementation.
        assert_eq!(mix64(0), 16294208416658607535);
        assert_eq!(hash_token(""), 16294208416658607535);
        assert_eq!(hash_token("the quick brown"), hash_token("the quick brown"));
    }

    #[test]
    fn short_and_empty_texts() {
        assert!(shingles("   ", 3).is_empty());
        assert_eq!(
            shingles("One two", 3),
            [hash_token("one two")].into_iter().collect()
        );
        assert_eq!(shingles("a b c d", 3).len(), 2);
    }

    #[test]
    fn python_whitespace_rules() {
        assert_eq!(shingles("a\u{1c}b", 1).len(), 2);
        assert_eq!(shingles("a\u{a0}b", 1).len(), 2);
    }

    #[test]
    fn identical_text_has_identical_signature_and_full_estimate() {
        let h = MinHasher::new(64, 3, 0);
        let s = h.signature("the cat sat on the mat today");
        assert_eq!(s, h.signature("The cat  sat on the mat today"));
        assert_eq!(estimated_jaccard(&s, &s), 1.0);
        assert_eq!(h.signature(""), vec![0; 64]);
        assert!(s.iter().all(|&v| v < PRIME));
    }

    #[test]
    fn batch_equals_single() {
        let h = MinHasher::new(32, 2, 7);
        let texts: Vec<String> = (0..50)
            .map(|i| format!("doc {i} shared words here"))
            .collect();
        let batch = h.signatures(&texts);
        for (t, s) in texts.iter().zip(&batch) {
            assert_eq!(&h.signature(t), s);
        }
    }
}
