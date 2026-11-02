# Records docs/demo/http.gif from a real run: `vhs docs/demo/http.tape` from the repo root.
Output docs/demo/http.gif
Set Shell "bash"
Set FontSize 15
Set Width 1300
Set Height 440
Set Padding 18
Set Theme "Catppuccin Mocha"
Set TypingSpeed 22ms

Hide
Type `export PS1='$ ' && uv sync -q && source .venv/bin/activate` Enter
Sleep 2s
Type `python -m corpus_dedup_library serve --port 18306 >/dev/null 2>&1 &` Enter
Sleep 2s
Sleep 8.0s
Type `clear` Enter
Sleep 1s
Show
Type `curl -s localhost:18306/dedup -d '{"documents": ["the cat sat on the mat today", "The cat sat on the mat today", "a different sentence entirely here"], "threshold": 0.6}' | jq -c` Enter
Sleep 3s
Type `curl -s localhost:18306/quality -d '{"text": "buy buy buy buy buy buy"}' | jq -c` Enter
Sleep 3s
Hide
Type `kill %1` Enter
Sleep 1s
