# Changelog

All notable changes to this project are documented here. The file is generated
from Conventional Commits by [git-cliff](https://git-cliff.org) when a release is cut
with `make cut-release`.

## [0.3.1] 2026-11-08

### Bug fixes

- Report the released version and keep version strings in step on release (#14)

### Documentation

- Describe the supply chain accurately (#11)
- Complete citation metadata and bump it on release (#13)

### Maintenance

- Latest toolchain and CI versions (#12)

## [0.3.0] 2026-11-02

### Features

- Build the Rust core into the package; exact verification in Rust (#10)

## [0.2.0] 2026-11-02

### Features

- Streaming CLI for large corpora, and C4 benchmarks against datasketch (#9)

### Documentation

- Recorded terminal demo of a real run, with its vhs tape
- Install the corpus-dedup CLI with Homebrew (#5)
- Remove authorship statements from docs and scripts
- Recorded demos of more commands, with their vhs tapes (#7)
- Recorded demos of the HTTP service and more commands (#8)

### Build and CI

- Build release archives for Linux and macOS on arm64 and amd64 (#6)

### Maintenance

- Classify squash merges in the changelog by the commits they contain

## [0.1.0] 2026-11-02

### Features

- Implement MinHash and LSH near-deduplication with quality filtering (#1)
- **rust:** Bit-exact Rust core for MinHash, LSH and clustering, with a JSONL CLI
- **backend:** Optional Rust backend for deduplicate, parity tests in CI

### Documentation

- Add explicit comparison scope and honest baseline framing (#2)
- Standard README structure and language framing (#4)
- Horizontal layered architecture diagram
- Compact horizontal architecture diagram
- Rust core results, usage, ADR 0004 and diagram
- List the Rust modules in AGENTS.md and llms.txt

### Build and CI

- Run CodeQL on main and on a weekly schedule only

### Maintenance

- Initialize repository with license and overview
- Remove Dependabot configuration
- Add release automation, AGENTS.md, llms.txt and contributor docs
