//! PyO3 bindings, built by maturin into the `corpus_dedup_rs` extension module.

use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;

use crate::{MinHasher, candidate_pairs as lsh_pairs, cluster as cluster_pairs, cluster_exact};

/// MinHash signatures for `texts`, computed in parallel with the GIL released.
#[pyfunction]
#[pyo3(signature = (texts, num_perm, k, seed))]
fn signatures(
    py: Python<'_>,
    texts: Vec<String>,
    num_perm: usize,
    k: usize,
    seed: u64,
) -> Vec<Vec<u64>> {
    let hasher = MinHasher::new(num_perm, k, seed);
    py.detach(|| hasher.signatures(&texts))
}

/// Sorted candidate pairs `(a, b)`, `a < b`, from LSH banding.
#[pyfunction]
fn candidate_pairs(
    py: Python<'_>,
    signatures: Vec<Vec<u64>>,
    bands: usize,
    rows: usize,
) -> PyResult<Vec<(usize, usize)>> {
    py.detach(|| lsh_pairs(&signatures, bands, rows))
        .map_err(PyValueError::new_err)
}

/// `(keep, drop, confirmed_pairs, clusters)` for candidates at or above `threshold`.
#[pyfunction]
#[allow(clippy::type_complexity)]
fn cluster(
    py: Python<'_>,
    signatures: Vec<Vec<u64>>,
    candidates: Vec<(usize, usize)>,
    threshold: f64,
) -> (Vec<usize>, Vec<usize>, Vec<(usize, usize)>, Vec<Vec<usize>>) {
    let c = py.detach(|| cluster_pairs(&signatures, &candidates, threshold));
    (c.keep, c.drop, c.confirmed, c.clusters)
}

/// Like `cluster`, but confirms candidates by exact shingle Jaccard over `texts`.
#[pyfunction]
#[allow(clippy::type_complexity)]
fn cluster_exact_jaccard(
    py: Python<'_>,
    texts: Vec<String>,
    candidates: Vec<(usize, usize)>,
    k: usize,
    threshold: f64,
) -> (Vec<usize>, Vec<usize>, Vec<(usize, usize)>, Vec<Vec<usize>>) {
    let c = py.detach(|| cluster_exact(&texts, &candidates, k, threshold));
    (c.keep, c.drop, c.confirmed, c.clusters)
}

#[pymodule]
fn corpus_dedup_rs(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(signatures, m)?)?;
    m.add_function(wrap_pyfunction!(candidate_pairs, m)?)?;
    m.add_function(wrap_pyfunction!(cluster, m)?)?;
    m.add_function(wrap_pyfunction!(cluster_exact_jaccard, m)?)?;
    m.add("__version__", env!("CARGO_PKG_VERSION"))?;
    Ok(())
}
