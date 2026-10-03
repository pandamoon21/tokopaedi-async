# Tokopaedi Async

High-performance, serverless-safe async Python scraper for Tokopedia. It talks to
Tokopedia's internal GraphQL API (`gql.tokopedia.com`) through `curl_cffi`, reproducing a
real iOS TLS/JA3 fingerprint. It is a fork of the original
[Tokopaedi](https://github.com/hilmiazizi/tokopaedi) library.

## Project overview

- **Purpose:** extract product data, reviews, and search results from Tokopedia
  concurrently, from a long-lived process or a function runtime.
- **Core technologies:** Python 3.9+, `asyncio`, `curl_cffi` (JA3/TLS fingerprinting),
  `dataclasses`.
- **Architecture:**
  - **Transport seam:** `transport.py` owns the endpoint, headers, fingerprint, session
    lifecycle, and timeout. It is the only module that imports `AsyncSession` or performs a
    POST. Every scraper goes through `post_graphql()`.
  - **Pagination:** `pagination.py` provides one bounded cursor loop used by both `search`
    and `get_reviews`. No recursion on the request path.
  - **Concurrency:** `concurrency.py` provides one bounded fan-out (`bounded_gather`) used by
    both `enrich_details` and `enrich_reviews`. Failures are returned as data.
  - **Pure parsers:** each scraper exposes `parse_search` / `parse_product` /
    `parse_reviews` — fixture JSON in, dataclasses out. This is the test seam.
  - **Anti-detection:** randomized iPhone user agents, screen resolutions, and a base64
    `Fingerprint-Data` header, built in `get_fingerprint.py`.
  - **Data models:** `ProductData`, `ProductReview`, `TokopaediShop`, etc. in
    `tokopaedi_types.py`, plus the `SearchResults` container.

## Key source files

| File | Responsibility |
|---|---|
| `src/tokopaedi_async/transport.py` | The seam: one POST, headers, fingerprint, session lifecycle, timeout. |
| `src/tokopaedi_async/pagination.py` | Bounded cursor loop (`paginate`). |
| `src/tokopaedi_async/concurrency.py` | Bounded fan-out (`bounded_gather`). |
| `src/tokopaedi_async/search.py` | `search()` + `parse_search()`. |
| `src/tokopaedi_async/get_product.py` | `get_product()` + `parse_product()` + `parse_tokped_url()`. |
| `src/tokopaedi_async/get_reviews.py` | `get_reviews()` + `parse_reviews()`. |
| `src/tokopaedi_async/tokopaedi_types.py` | Dataclasses, `SearchResults`, shop tier mapping. |
| `src/tokopaedi_async/get_fingerprint.py` | Randomized iOS device fingerprint. |
| `src/tokopaedi_async/custom_logging.py` | Opt-in log levels; configures nothing on import. |
| `examples/serverless_app.py` | FastAPI app runnable on Vercel / Lambda / Cloud Run. |

## Development

Uses **Poetry** for dependency management.

```bash
poetry install            # includes pytest
poetry run pytest         # 35 offline tests, no network
poetry run python example.py   # hits the real API
```

Installing as a dependency:

```bash
pip install tokopaedi-async
```

### Usage

```python
import asyncio
from tokopaedi_async import browse

async def main():
    results = await browse(
        "Asus Zenbook S14 32GB",
        max_result=10,
        reviews_per_product=20,
        concurrency=8,
    )
    print(results.json())

asyncio.run(main())
```

## Conventions

- **Async everywhere.** All network operations are coroutines. Never block the event loop.
- **No import-time side effects.** No `logging.basicConfig()`, no socket creation, no
  environment reads at module level. The test suite asserts the root logger is untouched
  after import; adding a side effect breaks serverless safety.
- **Failures are values.** A single failed request is logged and returned as `None` / `[]` /
  a `(item, exception)` pair. Argument errors still raise `ValueError`.
- **Parsers stay pure.** No I/O and no globals inside `parse_*` functions.
- **One seam.** Never call `AsyncSession` or `.post()` outside `transport.py`; push new
  request shapes through `post_graphql()`.
- **Bounded work.** Every unbounded loop needs a ceiling: `max_pages` for pagination,
  `concurrency` for fan-out, `max_result` for result sets.
- **Type safety.** Keep the dataclass definitions in `tokopaedi_types.py` authoritative.

## Serverless notes

- Omit `session=` on serverless: each request then creates and closes its own session, on
  both the success and failure paths. Do not cache a module-level session across
  invocations.
- `transport.DEFAULT_TIMEOUT` (20s) applies to every request. Lower it when the platform's
  wall-clock limit is tighter.
- Clamp `max_result`, `reviews_per_product`, and `concurrency` from user input so one caller
  cannot exhaust the invocation budget. See `examples/serverless_app.py`.

## Testing

Tests live in `tests/test_tokopaedi.py`.

```bash
pytest                      # 35 passed
pytest --cov=tokopaedi_async   # ~86% statement coverage
```

The suite is offline by design: it drives the real pagination, dedupe, and merge logic
through a `FakeSession` that satisfies the transport interface, and exercises the pure
parsers with fixture payloads. There is no network access and no API key.

`pytest.ini` disables the `xonsh` plugin (`-p no:xonsh`), which fails to load outside a
Windows console.

## Known issues / TODO

- [ ] Proxy support: needs a `transport` adapter that injects a proxy into the session.
- [ ] Retry with backoff on `429`/`5xx`: `pagination` and `concurrency` are the places to add
      it; `transport` is where the status code is visible.
- [ ] Rate-limit pacing between pages (currently bounded by `concurrency` only).
- [ ] Type the `session` parameter against a `Protocol` so custom adapters need no import of
      `curl_cffi`.
- [ ] Load-test the fingerprint rotation over long runs.
