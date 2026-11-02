# Records docs/demo/dedup.gif from a real run: `vhs docs/demo/dedup.tape`
# (after `cargo build --release --manifest-path rust/Cargo.toml`).
Output docs/demo/dedup.gif
Set Shell "bash"
Set FontSize 15
Set Width 1300
Set Height 480
Set Padding 18
Set Theme "Catppuccin Mocha"
Set TypingSpeed 30ms

Hide
Type "export PS1='$ ' PATH=$PWD/rust/target/release:$PATH" Enter
Type "uv run -q python benchmarks/make_jsonl.py 20000 > /tmp/corpus.jsonl && clear" Enter
Sleep 5s
Show
Type "wc -l < /tmp/corpus.jsonl" Enter
Sleep 1s
Type "corpus-dedup --threshold 0.6 < /tmp/corpus.jsonl > /tmp/deduped.jsonl" Enter
Sleep 2s
Type "wc -l < /tmp/deduped.jsonl" Enter
Sleep 3s
