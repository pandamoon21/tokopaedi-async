# 📘 API Documentation

This document provides a detailed reference for all the core functions and classes in `tokopaedi-async`.

---

## 🔍 Core Functions

### `async search(keyword, max_result=100, filters=None, debug=False)`
Search for products on Tokopedia. This function is recursive and will continue to fetch pages until `max_result` is reached or no more results are available.

- **Parameters:**
    - `keyword` (`str`): The search term.
    - `max_result` (`int`): Target number of results. (Default: `100`)
    - `filters` (`SearchFilters`): Optional filters for the search.
    - `debug` (`bool`): If `True`, logs progress using the custom logger.
- **Returns:** `SearchResults` object (a list-like container of `ProductData`).

### `async get_product(product_id=None, url=None, debug=False)`
Fetch full details for a specific product.

- **Parameters:**
    - `product_id` (`str`|`int`): The Tokopedia Product ID.
    - `url` (`str`): Full Tokopedia product URL (used if `product_id` is not provided).
    - `debug` (`bool`): If `True`, logs progress.
- **Returns:** `ProductData` object.

### `async get_reviews(product_id=None, url=None, max_result=10, debug=False)`
Fetch customer reviews for a specific product. This function is recursive.

- **Parameters:**
    - `product_id` (`str`|`int`): The Tokopedia Product ID.
    - `url` (`str`): Full Tokopedia product URL.
    - `max_result` (`int`): Target number of reviews. (Default: `10`)
    - `debug` (`bool`): If `True`, logs progress.
- **Returns:** `List[ProductReview]`.

---

## 🏗️ Data Models (Dataclasses)

### `ProductData`
Represents a single product and its metadata.

- `product_id`: `int`
- `product_name`: `str`
- `price`: `int`
- `url`: `str`
- `shop`: `TokopaediShop`
- `reviews`: `List[ProductReview]`
- `enrich_details()`: Instance method to fetch full details.
- `enrich_reviews()`: Instance method to fetch reviews for this product.

### `ProductReview`
Represents a customer review.

- `feedback_id`: `int`
- `message`: `str`
- `rating`: `float`
- `images`: `List[str]`
- `videos`: `List[str]`

### `SearchFilters`
Container for search parameters.

- `pmin` / `pmax`: Price range.
- `condition`: `1` (New) or `2` (Used).
- `shop_tier`: `2` (Official Store) or `3` (Power Merchant).
- `rt`: Min rating.
- `latest_product`: `7`, `30`, or `90` days.
- `is_discount`: `bool`
- `bebas_ongkir_extra`: `bool`

---

## ⚡ Concurrency & Performance

`SearchResults` provides two powerful methods for bulk data fetching:

### `await results.enrich_details(concurrency=20, debug=False)`
Iterates through all `ProductData` in the search results and fetches their full details (description, variants, etc.) in parallel.

### `await results.enrich_reviews(max_result=10, concurrency=20, debug=False)`
Fetches up to `max_result` reviews for every product in the search results in parallel.

---

## 🛡️ Anti-Detection

The library uses `curl_cffi` to bypass common scraping protections.
- **JA3 Fingerprinting:** Mimics the TLS handshake of a real iOS application.
- **Device Simulation:** Randomizes `X-Tkpd-Userid` and `Fingerprint-Data` headers.
- **SSL Verification:** Currently set to `verify=False` to avoid issues with certain network environments (use with caution).
