# Changelog

All notable changes to this project are documented here. The file is generated
from Conventional Commits by [git-cliff](https://git-cliff.org) when a release is cut
with `make cut-release`.

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

### Bench

- Add scale, throughput, memory, and adversarial duplicate tests (#3)
