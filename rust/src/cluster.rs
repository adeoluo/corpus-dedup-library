//! Union-find clustering of confirmed duplicate pairs; the lowest id in a cluster is kept.

use crate::minhash::estimated_jaccard;

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
    let n = signatures.len();
    let mut parent: Vec<usize> = (0..n).collect();
    let mut confirmed = Vec::new();
    for &(a, b) in candidates {
        if estimated_jaccard(&signatures[a], &signatures[b]) >= threshold {
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
}
