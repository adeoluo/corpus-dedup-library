//! LSH banding: documents sharing any band bucket become candidate pairs.

use std::collections::{BTreeSet, HashMap};

#[inline]
fn hash_band(band: &[u64]) -> u64 {
    band.iter().fold(1_469_598_103_934_665_603u64, |acc, &v| {
        (acc ^ v).wrapping_mul(1_099_511_628_211)
    })
}

/// Unordered candidate pairs `(a, b)` with `a < b`, sorted, from `bands * rows` signatures.
pub fn candidate_pairs(
    signatures: &[Vec<u64>],
    bands: usize,
    rows: usize,
) -> Result<Vec<(usize, usize)>, String> {
    let width = bands * rows;
    if let Some((i, s)) = signatures
        .iter()
        .enumerate()
        .find(|(_, s)| s.len() != width)
    {
        return Err(format!(
            "signature {i} has length {} != bands*rows {width}",
            s.len()
        ));
    }
    let mut pairs = BTreeSet::new();
    for band in 0..bands {
        let mut buckets: HashMap<u64, Vec<usize>> = HashMap::new();
        for (doc, sig) in signatures.iter().enumerate() {
            buckets
                .entry(hash_band(&sig[band * rows..(band + 1) * rows]))
                .or_default()
                .push(doc);
        }
        for members in buckets.values().filter(|m| m.len() > 1) {
            for (i, &a) in members.iter().enumerate() {
                for &b in &members[i + 1..] {
                    pairs.insert(if a < b { (a, b) } else { (b, a) });
                }
            }
        }
    }
    Ok(pairs.into_iter().collect())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn shared_band_collides_and_length_is_checked() {
        let sigs = vec![vec![1, 2, 3, 4], vec![1, 2, 9, 9], vec![5, 6, 7, 8]];
        assert_eq!(candidate_pairs(&sigs, 2, 2).unwrap(), vec![(0, 1)]);
        assert!(candidate_pairs(&[vec![1, 2, 3]], 2, 2).is_err());
    }
}
