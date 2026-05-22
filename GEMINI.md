# Tokopaedi Async

High-performance, asynchronous Python scraper for Tokopedia, leveraging `curl_cffi` for non-blocking I/O and advanced anti-detection. It is a fork of the original [Tokopaedi](https://github.com/hilmiazizi/tokopaedi) library.

## Project Overview

- **Purpose:** Efficiently extract product data, reviews, and search results from Tokopedia concurrently.
- **Core Technologies:** Python 3.9+, `asyncio`, `curl_cffi` (for JA3/TLS fingerprinting), `dataclasses`.
- **Architecture:** 
    - **Scraping Engine:** Uses GraphQL queries to Tokopedia's internal API (`gql.tokopedia.com`).
    - **Anti-Detection:** Randomized user agents and browser fingerprints (`Fingerprint-Data` header) via `get_fingerprint.py`.
    - **Data Models:** Structured using `ProductData`, `ProductReview`, `SearchResults`, etc., in `tokopaedi_types.py`.
    - **Concurrency:** Uses `asyncio.Semaphore` (default 20) for bounded parallel enrichment of data.

## Key Source Files

- `src/tokopaedi_async/search.py`: Implements product search with recursive pagination and filter support.
- `src/tokopaedi_async/get_product.py`: Fetches rich product details including variants, media, and shop info.
- `src/tokopaedi_async/get_reviews.py`: Scrapes customer reviews with recursive pagination.
- `src/tokopaedi_async/tokopaedi_types.py`: Defines the `dataclass` models and the `SearchResults` container with enrichment methods.
- `src/tokopaedi_async/get_fingerprint.py`: Logic for generating realistic iOS/iPhone browser fingerprints.

## Development & Usage

### Building and Running

This project uses **Poetry** for dependency management.

- **Installation:** `pip install tokopaedi-async` (or `poetry install` for development).
- **Basic Usage:**
  ```python
  import asyncio
  from tokopaedi_async import search

  async def main():
      results = await search("keyword", max_result=50)
      await results.enrich_details()
      await results.enrich_reviews()
      print(results.json())

  asyncio.run(main())
  ```

### Development Conventions

- **Async Everywhere:** All network operations MUST be `async`. Use `await` for `search()`, `get_product()`, `get_reviews()`, and enrichment methods.
- **Data Enrichment:** Prefer using `SearchResults.enrich_details()` and `SearchResults.enrich_reviews()` for bulk operations as they handle concurrency efficiently.
- **Logging:** Use the custom logger from `custom_logging.py`.
- **Error Handling:** Network calls are wrapped in `try-except` blocks; failures generally return `None` or empty lists/objects rather than raising exceptions.
- **Type Safety:** Adhere to the `dataclass` definitions in `tokopaedi_types.py`.

## Testing

Tests are located in the `tests/` directory.

- **Run tests:** `pytest` (Install `pytest` as a dev dependency if not present).
- **Test File:** `tests/test_tokopaedi.py` contains basic integration tests for core functions.

## TODO / Known Issues

- [ ] Add more comprehensive unit tests for individual extractor functions.
- [ ] Implement proxy support for `curl_cffi` sessions.
- [ ] Improve error reporting instead of silent failures in some extractors.
