//! End-to-end tests of the `corpus-dedup` binary over stdin and stdout.

use std::io::Write;
use std::process::{Command, Output, Stdio};

fn run(args: &[&str], input: &str) -> Output {
    let mut child = Command::new(env!("CARGO_BIN_EXE_corpus-dedup"))
        .args(args)
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()
        .expect("spawn corpus-dedup");
    child
        .stdin
        .take()
        .unwrap()
        .write_all(input.as_bytes())
        .unwrap();
    child.wait_with_output().unwrap()
}

#[test]
fn keeps_first_of_each_cluster_in_input_order() {
    let input = concat!(
        "{\"text\": \"the quick brown fox jumps over the lazy dog\"}\n",
        "{\"text\": \"a completely different sentence about databases\"}\n",
        "\n",
        "{\"text\": \"The quick brown fox jumps over the lazy dog\"}\n",
    );
    let out = run(&[], input);
    assert!(out.status.success());
    let stdout = String::from_utf8(out.stdout).unwrap();
    assert_eq!(stdout.lines().count(), 2);
    assert!(stdout.starts_with("{\"text\": \"the quick"));
    let stderr = String::from_utf8(out.stderr).unwrap();
    assert!(stderr.contains("documents=3 kept=2 dropped=1"), "{stderr}");
}

#[test]
fn custom_field_and_errors() {
    let out = run(&["--field", "body"], "{\"body\": \"x y z\"}\n");
    assert!(out.status.success());
    let missing = run(&[], "{\"body\": \"x\"}\n");
    assert_eq!(missing.status.code(), Some(2));
    assert!(String::from_utf8(missing.stderr)
        .unwrap()
        .contains("missing string field"));
    let invalid = run(&[], "not json\n");
    assert_eq!(invalid.status.code(), Some(2));
    let bad_threshold = run(&["--threshold", "1.5"], "");
    assert_eq!(bad_threshold.status.code(), Some(2));
}

#[test]
fn file_mode_matches_stdin_mode_and_preserves_bytes() {
    let dir = std::env::temp_dir().join(format!("corpus-dedup-test-{}", std::process::id()));
    std::fs::create_dir_all(&dir).unwrap();
    let input = dir.join("in.jsonl");
    let output = dir.join("out.jsonl");
    let mut text = String::new();
    for i in 0..50 {
        text.push_str(&format!(
            "{{\"id\": {i}, \"text\": \"shared words about topic {} plus filler words here\"}}\n",
            i % 10
        ));
        if i % 7 == 0 {
            text.push_str("\r\n");
        }
    }
    text.push_str("{\"id\": 99, \"text\": \"caf\u{e9} na\u{ef}ve r\u{e9}sum\u{e9} unique line\"}");
    std::fs::write(&input, &text).unwrap();
    let stdin_out = run(&[], &text);
    assert!(stdin_out.status.success());
    let file_run = Command::new(env!("CARGO_BIN_EXE_corpus-dedup"))
        .args([
            "--input",
            input.to_str().unwrap(),
            "--output",
            output.to_str().unwrap(),
        ])
        .output()
        .unwrap();
    assert!(
        file_run.status.success(),
        "{}",
        String::from_utf8_lossy(&file_run.stderr)
    );
    let from_file = std::fs::read_to_string(&output).unwrap();
    assert_eq!(from_file, String::from_utf8(stdin_out.stdout).unwrap());
    // The 50 templated lines differ by one digit, so they collapse to a few clusters.
    let kept = from_file.lines().count();
    assert!(kept > 1 && kept < 51, "kept {kept}");
    assert!(from_file.ends_with("unique line\"}\n"));
    std::fs::remove_dir_all(&dir).unwrap();
}
