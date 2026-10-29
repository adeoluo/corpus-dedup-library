# Threat Model - Corpus Dedup Library

## Assets
- The HTTP service's availability and the integrity of its responses.

## Trust boundaries
- The only external input is the JSON body and path of a request. The algorithms and the built-in
  corpus are in-process and trusted.

## Entry points and mitigations

### `POST /dedup`
- **Malformed JSON** is rejected with 400 before routing.
- **Validation:** documents must be a non-empty, bounded list of bounded strings; the threshold must
  be a number in (0, 1]. Oversized or wrong-type input returns 400 with a message.
- **Bounded work:** the document count and size are capped, so a single request cannot force
  unbounded hashing.

### `POST /quality`
- The text must be a bounded string; oversized or wrong-type input returns 400.

### `GET` routes
- `/health`, `/ready`, `/report`, and `/metrics` take no user input and return fixed-shape payloads.
  `/metrics` exposes only aggregate counters.

## Non-threats (by construction)
- **No secrets:** the service holds no credentials and makes no outbound calls.
- **No persistence:** the service holds no corpus between requests; nothing is written on the request
  path.
- **No code execution:** inputs are text and numbers; no user-supplied string is evaluated as code.

## Supply chain
- Zero runtime dependencies. Development tooling is pinned via `uv.lock`. CodeQL and dependency
  scanning run in CI.

## Residual risk
- Large batches are CPU-intensive; the per-request caps bound the work, and a production deployment
  would add a rate limiter behind a reverse proxy.
