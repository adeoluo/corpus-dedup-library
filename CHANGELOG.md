# Changelog

All notable changes to this project are documented here. The file is generated
from Conventional Commits by [git-cliff](https://git-cliff.org) when a release is cut
with `make cut-release`.

## Unreleased

### Features

- Implement MinHash and LSH near-deduplication with quality filtering (#1)

### Documentation

- Add explicit comparison scope and honest baseline framing (#2)
- Standard README structure and language framing (#4)
- Horizontal layered architecture diagram
- Compact horizontal architecture diagram

### Build and CI

- Run CodeQL on main and on a weekly schedule only

### Maintenance

- Initialize repository with license and overview
- Remove Dependabot configuration

### Bench

- Add scale, throughput, memory, and adversarial duplicate tests (#3)
