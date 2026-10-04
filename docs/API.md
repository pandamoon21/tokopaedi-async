# 📘 API Documentation

Detailed reference for `tokopaedi-async` v0.2.2.

```bash
uv add tokopaedi-async          # recommended
pip install tokopaedi-async     # or pip
```

Every function that touches the network is a coroutine and takes an optional `session`
argument. Omit `session` on serverless (each request owns its connection) and pass one in a
long-lived process to reuse connections.

---

## 🔍 Core functions

### `await search(keyword, max_result=100, filters=None, debug=False, session=None)`

Search products, paginated.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `keyword` | `str` | `"zenbook 14 32gb"` | Search term. |
| `max_result` | `int` | `100` | Upper bound on returned products. Pagination stops as soon as it is reached. |
| `filters` | `SearchFilters \| None` | `None` | Optional filters (see below). |
| `debug` | `bool` | `False` | Log each product at `DEBUG` level. |
| `session` | `AsyncSession \| None` | `None` | Reuse an existing HTTP session. |

**Returns** `SearchResults`.

Pages are fetched until `max_result` is reached or the API returns no next cursor.
Products are deduplicated by `product_id` as pages arrive. The walk is bounded by
`max_pages=100`, so a stuck cursor cannot loop forever. Transport failures are logged and
`None`; the returned container is then empty rather than an exception.

---

### `await get_product(product_id=None, url=None, debug=False, session=None)`

Fetch one product's full detail page (variants, media, description, stock, shop).

| Parameter | Type | Description |
|---|---|---|
| `product_id` | `str \| int \| None` | Tokopedia product id. Takes precedence when both are given. |
| `url` | `str \| None` | Product URL; parsed into shop domain + product key. |
| `debug` | `bool` | Log the resolved product name at `DEBUG` level. |
| `session` | `AsyncSession \| None` | Reuse an existing HTTP session. |

**Returns** `ProductData | None`. `None` means the URL could not be parsed or the request
failed.

**Raises** `ValueError` when neither `product_id` nor `url` is provided.

---

### `await get_reviews(product_id=None, url=None, max_result=10, debug=False, session=None)`

Fetch a product's customer reviews, paginated.

| Parameter | Type | Description |
|---|---|---|
| `product_id` | `str \| int \| None` | Tokopedia product id. |
| `url` | `str \| None` | Product URL; resolved to an id **once**, up front. |
| `max_result` | `int` | Upper bound on returned reviews. Default `10`. |
| `debug` | `bool` | Log each review at `DEBUG` level. |
| `session` | `AsyncSession \| None` | Reuse an existing HTTP session. |

**Returns** `List[ProductReview]`. Empty when the product has no reviews or the request
failed.

**Raises** `ValueError` when neither argument is provided, or when `url` cannot be resolved
to a product id.

The endpoint pages in fixed increments of 10 (`PAGE_SIZE`). Pagination stops when a page is
empty or the response reports `hasNext: false`. Reviews are deduplicated by `feedback_id`.

---

### `await browse(keyword, max_result=20, filters=None, reviews_per_product=0, concurrency=10, session=None)`

Search **and** enrich every result in one call — the common bulk workflow.

| Parameter | Type | Description |
|---|---|---|
| `keyword` | `str` | Search term. |
| `max_result` | `int` | Maximum number of products. Default `20`. |
| `filters` | `SearchFilters \| None` | Optional filters. |
| `reviews_per_product` | `int` | When `> 0`, also fetch this many reviews per product. |
| `concurrency` | `int` | Maximum in-flight enrichment requests. Default `10`. |
| `session` | `AsyncSession \| None` | Reuse an existing HTTP session. |

**Returns** `SearchResults` with details (and reviews when requested) attached. Enrichment
failures are logged and skipped, so a partial result is still returned.

---

## 🧩 Pure parsers

These take an already-decoded GraphQL response and return dataclasses. No network, no
globals — they are the seam to test against.

### `parse_search(payload) -> List[ProductData]`

Input: the full decoded response from the `SearchResult/getProductResult` operation.
Returns `[]` when the response carries no product list.

### `parse_product(payload) -> ProductData | None`

Input: the decoded response from `ProductDetails/getPDPLayout`.
Returns `None` when the response carries no PDP layout, so "no such product" is
distinguishable from "request failed".

### `parse_reviews(payload) -> List[ProductReview]`

Input: the decoded response from `ProductReview/getProductReviewReadingList`.
Returns `[]` when the response carries no review list.

### `parse_tokped_url(url) -> (str, str)`

Split a product URL into `(shop_domain, product_key)`. Returns `("", "")` for anything that
is not a Tokopedia product URL.

---

## 🏗️ Data models

All models are `@dataclass` and expose `.json()` returning a plain `dict`.

### `ProductData`

| Field | Type | Notes |
|---|---|---|
| `product_id` | `int` | |
| `product_sku` | `str` | |
| `product_name` | `str` | |
| `url` | `str` | |
| `main_image` | `str \| None` | |
| `status` | `str \| None` | |
| `description` | `str \| None` | |
| `price` | `int \| None` | In IDR. |
| `price_text` | `str \| None` | Formatted, e.g. `"Rp1.500"`. |
| `price_original` | `str \| None` | Pre-discount price. |
| `discount_percentage` | `str \| None` | |
| `weight` / `weight_unit` | `int \| None` / `str \| None` | |
| `product_media` | `List[ProductMedia]` | |
| `sold_count` | `int \| None` | |
| `rating` | `float \| None` | |
| `review_count` | `int \| None` | Reviews reported on the PDP. |
| `discussion_count` | `int \| None` | |
| `total_stock` | `int \| None` | |
| `etalase` / `etalase_url` | `str \| None` | Storefront shelf. |
| `category` | `str \| None` | |
| `sub_category` | `List[str] \| None` | |
| `product_option` | `List[ProductOption] \| None` | |
| `variants` | `List[ProductVariant] \| None` | |
| `shop` | `TokopaediShop \| None` | |
| `reviews` | `List[ProductReview] \| None` | Populated by `enrich_reviews`. |
| `has_detail` | `bool` | `True` once `enrich_details` has run. |
| `has_reviews` | `bool` | `True` once `enrich_reviews` has run. |

Methods:

- `await enrich_details(debug=False, session=None)` — fetch and merge PDP data. Idempotent.
  Only fields owned by a PDP fetch are merged (`DETAIL_FIELDS`); review data is preserved.
- `await enrich_reviews(max_result=None, debug=False, session=None)` — fetch and attach
  reviews. Idempotent.
- `merge_details(detail)` — the explicit merge rule, usable directly with a fixture.
- `json()` — plain dict.

### `ProductReview`

| Field | Type |
|---|---|
| `feedback_id` | `int` |
| `variant_name` | `str \| None` |
| `message` | `str` |
| `rating` | `float` |
| `review_age` | `str` |
| `user_full_name` | `str` |
| `user_url` | `str` |
| `response_message` | `str \| None` |
| `response_created_text` | `str \| None` |
| `images` | `List[str]` |
| `videos` | `List[str]` |
| `likes` | `int` |

### `TokopaediShop`

`shop_id: int`, `name: str`, `city: str | None`, `url: str`,
`shop_type: str | None` (`"Normal"` / `"Mall"` / `"Power Shop"` / `None`).

### `ProductMedia`

`original: str`, `thumbnail: str`, `max_res: str`.

### `ProductOption`

`option_id: int`, `option_name: str`, `option_child: List[str]`.

### `ProductVariant`

`option_ids: List[int]`, `option_name: str`, `option_url: str`, `price: int`,
`price_string: str`, `discount: str`, `image_url: str | None`, `stock: int | None`.

---

## 📦 `SearchResults`

The list-like container returned by `search()` and `browse()`.

| Operation | Behaviour |
|---|---|
| `len(results)` | Number of products. |
| `results[i]` | Product at index `i`. |
| `for p in results` | Iterate products. |
| `results.json()` | `List[dict]`. |
| `results.append(p)` / `results.extend([...])` | Mutate. |
| `results_a + results_b` | New combined container. |

Methods:

- `await enrich_details(debug=False, concurrency=10, session=None)` — enrich every product.
  **Returns** `List[tuple[ProductData, Exception]]` of failures; empty means full success.
- `await enrich_reviews(max_result=10, debug=False, concurrency=10, session=None)` — same,
  for reviews.

Both run with at most `concurrency` requests in flight. Lower `concurrency` on a small
serverless instance or when the API is throttling.

---

## ⚙️ `SearchFilters`

Every field is optional; only the fields you set are sent to the API.

| Field | Type | Meaning |
|---|---|---|
| `pmin` / `pmax` | `int` | Price range in IDR. |
| `condition` | `int` | `1` = new, `2` = used. |
| `shop_tier` | `int` | `2` = Mall / Official Store, `3` = Power Shop / Power Merchant. |
| `rt` | `float` | Minimum average rating, `0.0`–`5.0`. |
| `is_discount` | `bool` | Discounted products only. |
| `bebas_ongkir_extra` | `bool` | "Bebas Ongkir Extra" products only. |
| `is_fulfillment` | `bool` | Fulfilled by Tokopedia only. |
| `is_plus` | `bool` | Tokopedia Plus products only. |
| `cod` | `bool` | Cash-on-delivery eligible only. |
| `latest_product` | `int` | Product age in days: `7`, `30`, or `90`. |

---

## 🧰 Utilities

### `paginate(fetch_page, start_state, max_result, key=None, max_pages=100)`

The bounded cursor loop used internally. Useful when you want to walk a custom cursor.

`fetch_page` is `async (state) -> (items, next_state)`; return `None` for `next_state` to
stop. `key` deduplicates across pages; `max_pages` is a hard safety ceiling.

### `bounded_gather(items, fetch, concurrency=10)`

Run `await fetch(item)` for every item with at most `concurrency` in flight.

**Returns** `List[tuple[item, Exception]]` for the failures. `asyncio.CancelledError` is
re-raised rather than reported as a data error, so host shutdown propagates correctly.

### `enable_custom_levels()`

Opt in to the `SEARCH` (25), `DETAIL` (26), and `REVIEW` (27) log levels. Idempotent and
never called automatically — importing the package configures nothing.

### `GQL_ENDPOINT`, `DEFAULT_TIMEOUT`

`transport.GQL_ENDPOINT` is the GraphQL URL template; `transport.DEFAULT_TIMEOUT` is the
per-request timeout in seconds (20). Lower it if your platform's limit is tighter.

---

## 🚨 Error handling

| Situation | Behaviour |
|---|---|
| Invalid arguments (`get_product()` with nothing, unparseable URL for reviews) | raises `ValueError` |
| HTTP failure, timeout, or connection error | logged at `WARNING`; returns `None` (single) or `[]`/empty container (batch) |
| Response missing the expected GraphQL operation | returns empty; pagination stops |
| One item fails during batch enrichment | recorded in the returned failure list; the rest complete |
| Invocation cancelled (host shutdown) | `asyncio.CancelledError` propagates |

To distinguish "no results" from "request failed", call the network function and the parser
separately, or check `response is None` before parsing.
