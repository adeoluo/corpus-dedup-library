//! Union-find clustering of confirmed duplicate pairs; the lowest id in a cluster is kept.

use rayon::prelude::*;

use crate::minhash::{estimated_jaccard, shingles};

/// Result of clustering: kept and dropped ids, confirmed pairs, and multi-member clusters.
#[derive(Debug, Default, PartialEq)]
pub struct Clusters {
    pub keep: Vec<usize>,
    pub drop: Vec<usize>,
    pub confirmed: Vec<(usize, usize)>,
    pub clusters: Vec<Vec<usize>>,
}

fn find(parent: &mut [usize], mut x: usize) -> usize {
    while parent[x] != x {
        parent[x] = parent[parent[x]];
        x = parent[x];
    }
    x
}

/// Confirm candidates whose estimated Jaccard is at least `threshold`, then cluster.
pub fn cluster(signatures: &[Vec<u64>], candidates: &[(usize, usize)], threshold: f64) -> Clusters {
    cluster_confirmed(signatures.len(), candidates, |i| {
        let (a, b) = candidates[i];
        estimated_jaccard(&signatures[a], &signatures[b]) >= threshold
    })
}

/// Exact Jaccard similarity of two sorted, deduplicated shingle lists. Same value as the
/// Python `exact_jaccard`: 1.0 when both are empty, else |A ∩ B| / |A ∪ B|.
pub fn sorted_jaccard(a: &[u64], b: &[u64]) -> f64 {
    if a.is_empty() && b.is_empty() {
        return 1.0;
    }
    let (mut i, mut j, mut shared) = (0, 0, 0usize);
    while i < a.len() && j < b.len() {
        match a[i].cmp(&b[j]) {
            std::cmp::Ordering::Less => i += 1,
            std::cmp::Ordering::Greater => j += 1,
            std::cmp::Ordering::Equal => {
                shared += 1;
                i += 1;
                j += 1;
            }
        }
    }
    shared as f64 / (a.len() + b.len() - shared) as f64
}

/// Confirm candidates whose exact shingle Jaccard is at least `threshold`, then cluster.
/// Shingle sets are built once per document that appears in a candidate, and pairs are
/// scored, both in parallel.
pub fn cluster_exact(
    texts: &[String],
    candidates: &[(usize, usize)],
    k: usize,
    threshold: f64,
) -> Clusters {
    let mut needed = vec![false; texts.len()];
    for &(a, b) in candidates {
        needed[a] = true;
        needed[b] = true;
    }
    let sets: Vec<Vec<u64>> = texts
        .par_iter()
        .zip(needed.par_iter())
        .map(|(text, &need)| {
            if !need {
                return Vec::new();
            }
            let mut set: Vec<u64> = shingles(text, k).into_iter().collect();
            set.sort_unstable();
            set
        })
        .collect();
    let keep: Vec<bool> = candidates
        .par_iter()
        .map(|&(a, b)| sorted_jaccard(&sets[a], &sets[b]) >= threshold)
        .collect();
    cluster_confirmed(texts.len(), candidates, |i| keep[i])
}

/// Union the candidates for which `confirm(index)` holds, then group by root.
fn cluster_confirmed(
    n: usize,
    candidates: &[(usize, usize)],
    confirm: impl Fn(usize) -> bool,
) -> Clusters {
    let mut parent: Vec<usize> = (0..n).collect();
    let mut confirmed = Vec::new();
    for (i, &(a, b)) in candidates.iter().enumerate() {
        if confirm(i) {
            let (ra, rb) = (find(&mut parent, a), find(&mut parent, b));
            if ra != rb {
                let (lo, hi) = if ra < rb { (ra, rb) } else { (rb, ra) };
                parent[hi] = lo;
            }
            confirmed.push((a, b));
        }
    }
    let mut groups: Vec<Vec<usize>> = vec![Vec::new(); n];
    for doc in 0..n {
        let root = find(&mut parent, doc);
        groups[root].push(doc);
    }
    let mut out = Clusters {
        confirmed,
        ..Default::default()
    };
    for members in groups.into_iter().filter(|g| !g.is_empty()) {
        out.keep.push(members[0]);
        out.drop.extend(&members[1..]);
        if members.len() > 1 {
            out.clusters.push(members);
        }
    }
    out.keep.sort_unstable();
    out.drop.sort_unstable();
    out.confirmed.sort_unstable();
    out
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn transitive_clusters_keep_lowest_id() {
        let sigs = vec![vec![1, 1], vec![1, 1], vec![1, 1], vec![2, 3]];
        let c = cluster(&sigs, &[(1, 2), (0, 1)], 0.9);
        assert_eq!(c.keep, vec![0, 3]);
        assert_eq!(c.drop, vec![1, 2]);
        assert_eq!(c.clusters, vec![vec![0, 1, 2]]);
        assert_eq!(c.confirmed, vec![(0, 1), (1, 2)]);
    }

    #[test]
    fn exact_jaccard_on_sorted_sets() {
        assert_eq!(sorted_jaccard(&[], &[]), 1.0);
        assert_eq!(sorted_jaccard(&[1], &[]), 0.0);
        assert_eq!(sorted_jaccard(&[1, 2, 3], &[2, 3, 4]), 0.5);
    }

    #[test]
    fn exact_clusters_confirm_only_true_near_duplicates() {
        let texts: Vec<String> = [
            "the cat sat on the mat today",
            "the cat sat on the mat today",
            "a completely different sentence here",
            "",
        ]
        .iter()
        .map(|s| s.to_string())
        .collect();
        let c = cluster_exact(&texts, &[(0, 1), (0, 2), (2, 3)], 3, 0.8);
        assert_eq!(c.confirmed, vec![(0, 1)]);
        assert_eq!(c.keep, vec![0, 2, 3]);
        assert_eq!(c.clusters, vec![vec![0, 1]]);
    }
}
