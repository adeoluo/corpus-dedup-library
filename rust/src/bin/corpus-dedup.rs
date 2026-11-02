//! `corpus-dedup`: stream JSONL on stdin, write the deduplicated lines to stdout.
//!
//! Each input line is a JSON object; the text to compare is read from `--field`
//! (default `text`). Lines are kept in input order; the first occurrence of each
//! near-duplicate cluster survives. A summary goes to stderr.

use std::io::{self, BufRead, BufWriter, Write};
use std::process::ExitCode;
use std::time::Instant;

use corpus_dedup_rs::{candidate_pairs, cluster, MinHasher};

struct Args {
    threshold: f64,
    bands: usize,
    rows: usize,
    k: usize,
    seed: u64,
    field: String,
}

const USAGE: &str = "usage: corpus-dedup [--threshold 0.6] [--bands 16] [--rows 4] [--k 2] [--seed 0] [--field text] < in.jsonl > out.jsonl";

fn parse_args() -> Result<Args, String> {
    let mut args = Args {
        threshold: 0.6,
        bands: 16,
        rows: 4,
        k: 2,
        seed: 0,
        field: "text".into(),
    };
    let mut it = std::env::args().skip(1);
    while let Some(flag) = it.next() {
        if flag == "-h" || flag == "--help" {
            return Err(USAGE.into());
        }
        if flag == "-V" || flag == "--version" {
            println!("corpus-dedup {}", env!("CARGO_PKG_VERSION"));
            std::process::exit(0);
        }
        let value = it
            .next()
            .ok_or_else(|| format!("{flag} needs a value\n{USAGE}"))?;
        let bad = |e: &dyn std::fmt::Display| format!("invalid {flag} {value:?}: {e}");
        match flag.as_str() {
            "--threshold" => args.threshold = value.parse().map_err(|e| bad(&e))?,
            "--bands" => args.bands = value.parse().map_err(|e| bad(&e))?,
            "--rows" => args.rows = value.parse().map_err(|e| bad(&e))?,
            "--k" => args.k = value.parse().map_err(|e| bad(&e))?,
            "--seed" => args.seed = value.parse().map_err(|e| bad(&e))?,
            "--field" => args.field = value,
            _ => return Err(format!("unknown flag {flag}\n{USAGE}")),
        }
    }
    if !(0.0..=1.0).contains(&args.threshold) || args.bands == 0 || args.rows == 0 || args.k == 0 {
        return Err("threshold must be in [0, 1]; bands, rows and k must be positive".into());
    }
    Ok(args)
}

fn run(args: &Args) -> Result<(), String> {
    let start = Instant::now();
    let mut lines = Vec::new();
    let mut texts = Vec::new();
    for (number, line) in io::stdin().lock().lines().enumerate() {
        let line = line.map_err(|e| format!("read error: {e}"))?;
        if line.trim().is_empty() {
            continue;
        }
        let value: serde_json::Value = serde_json::from_str(&line)
            .map_err(|e| format!("line {}: invalid JSON: {e}", number + 1))?;
        let text = value
            .get(&args.field)
            .and_then(|v| v.as_str())
            .ok_or_else(|| format!("line {}: missing string field {:?}", number + 1, args.field))?;
        texts.push(text.to_owned());
        lines.push(line);
    }
    let hasher = MinHasher::new(args.bands * args.rows, args.k, args.seed);
    let signatures = hasher.signatures(&texts);
    let candidates = candidate_pairs(&signatures, args.bands, args.rows)?;
    let result = cluster(&signatures, &candidates, args.threshold);

    let mut out = BufWriter::new(io::stdout().lock());
    for &doc in &result.keep {
        writeln!(out, "{}", lines[doc]).map_err(|e| format!("write error: {e}"))?;
    }
    out.flush().map_err(|e| format!("write error: {e}"))?;
    eprintln!(
        "documents={} kept={} dropped={} clusters={} candidate_pairs={} seconds={:.3}",
        texts.len(),
        result.keep.len(),
        result.drop.len(),
        result.clusters.len(),
        candidates.len(),
        start.elapsed().as_secs_f64()
    );
    Ok(())
}

fn main() -> ExitCode {
    match parse_args().and_then(|args| run(&args)) {
        Ok(()) => ExitCode::SUCCESS,
        Err(message) => {
            eprintln!("{message}");
            ExitCode::from(2)
        }
    }
}
