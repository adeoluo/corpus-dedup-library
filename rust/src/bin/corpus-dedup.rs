//! `corpus-dedup`: remove near-duplicate lines from a JSONL corpus.
//!
//! Each input line is a JSON object; the text to compare is read from `--field`
//! (default `text`). Lines are kept in input order; the first occurrence of each
//! near-duplicate cluster survives. A summary goes to stderr.
//!
//! Input is read in batches whose signatures are computed in parallel, so memory
//! holds the MinHash signatures, not the text. With `--input FILE` the kept lines
//! are copied from the file in a second pass, so memory stays proportional to the
//! number of documents however long they are. Reading stdin keeps each line so it
//! can be written after deduplication.

use std::fs::File;
use std::io::{self, BufRead, BufReader, BufWriter, Read, Seek, SeekFrom, Write};
use std::process::ExitCode;
use std::time::Instant;

use corpus_dedup_rs::{MinHasher, candidate_pairs, cluster};

const BATCH: usize = 20_000;

struct Args {
    threshold: f64,
    bands: usize,
    rows: usize,
    k: usize,
    seed: u64,
    field: String,
    input: Option<String>,
    output: Option<String>,
}

const USAGE: &str = "usage: corpus-dedup [--threshold 0.6] [--bands 16] [--rows 4] [--k 2] [--seed 0] [--field text] [--input in.jsonl] [--output out.jsonl]\n       (without --input reads stdin; without --output writes stdout)";

fn parse_args() -> Result<Args, String> {
    let mut args = Args {
        threshold: 0.6,
        bands: 16,
        rows: 4,
        k: 2,
        seed: 0,
        field: "text".into(),
        input: None,
        output: None,
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
            "--input" => args.input = Some(value),
            "--output" => args.output = Some(value),
            _ => return Err(format!("unknown flag {flag}\n{USAGE}")),
        }
    }
    if !(0.0..=1.0).contains(&args.threshold) || args.bands == 0 || args.rows == 0 || args.k == 0 {
        return Err("threshold must be in [0, 1]; bands, rows and k must be positive".into());
    }
    Ok(args)
}

/// A non-empty input line: its byte span in the input and, when reading stdin, its text.
struct Line {
    start: u64,
    len: u64,
    text: Option<String>,
}

fn extract(line: &str, field: &str, number: usize) -> Result<String, String> {
    let value: serde_json::Value =
        serde_json::from_str(line).map_err(|e| format!("line {number}: invalid JSON: {e}"))?;
    value
        .get(field)
        .and_then(|v| v.as_str())
        .map(str::to_owned)
        .ok_or_else(|| format!("line {number}: missing string field {field:?}"))
}

fn run(args: &Args) -> Result<(), String> {
    let start = Instant::now();
    let hasher = MinHasher::new(args.bands * args.rows, args.k, args.seed);
    let keep_text = args.input.is_none();
    let mut reader: Box<dyn BufRead> = match &args.input {
        Some(path) => Box::new(BufReader::with_capacity(
            1 << 20,
            File::open(path).map_err(|e| format!("{path}: {e}"))?,
        )),
        None => Box::new(BufReader::with_capacity(1 << 20, io::stdin().lock())),
    };

    let mut lines: Vec<Line> = Vec::new();
    let mut signatures: Vec<Vec<u64>> = Vec::new();
    let mut batch: Vec<String> = Vec::with_capacity(BATCH);
    let mut buf = String::new();
    let (mut offset, mut number) = (0u64, 0usize);
    loop {
        buf.clear();
        let read = reader
            .read_line(&mut buf)
            .map_err(|e| format!("read error: {e}"))?;
        if read > 0 {
            number += 1;
            let trimmed = buf.trim_end_matches(['\n', '\r']);
            if !trimmed.trim().is_empty() {
                batch.push(extract(trimmed, &args.field, number)?);
                lines.push(Line {
                    start: offset,
                    len: trimmed.len() as u64,
                    text: keep_text.then(|| trimmed.to_owned()),
                });
            }
            offset += read as u64;
        }
        if batch.len() == BATCH || (read == 0 && !batch.is_empty()) {
            signatures.extend(hasher.signatures(&batch));
            batch.clear();
        }
        if read == 0 {
            break;
        }
    }
    let hashed = start.elapsed().as_secs_f64();
    let candidates = candidate_pairs(&signatures, args.bands, args.rows)?;
    let result = cluster(&signatures, &candidates, args.threshold);
    drop(signatures);

    let sink: Box<dyn Write> = match &args.output {
        Some(path) => Box::new(File::create(path).map_err(|e| format!("{path}: {e}"))?),
        None => Box::new(io::stdout().lock()),
    };
    let mut out = BufWriter::with_capacity(1 << 20, sink);
    let werr = |e: io::Error| format!("write error: {e}");
    if let Some(path) = &args.input {
        let mut file = File::open(path).map_err(|e| format!("{path}: {e}"))?;
        let mut chunk = Vec::new();
        for &doc in &result.keep {
            let line = &lines[doc];
            file.seek(SeekFrom::Start(line.start)).map_err(werr)?;
            chunk.resize(line.len as usize, 0);
            file.read_exact(&mut chunk).map_err(werr)?;
            out.write_all(&chunk).map_err(werr)?;
            out.write_all(b"\n").map_err(werr)?;
        }
    } else {
        for &doc in &result.keep {
            if let Some(text) = &lines[doc].text {
                writeln!(out, "{text}").map_err(werr)?;
            }
        }
    }
    out.flush().map_err(werr)?;
    eprintln!(
        "documents={} kept={} dropped={} clusters={} candidate_pairs={} hash_seconds={:.3} seconds={:.3}",
        lines.len(),
        result.keep.len(),
        result.drop.len(),
        result.clusters.len(),
        candidates.len(),
        hashed,
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
