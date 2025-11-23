
# Tokopaedi Async - High-Performance Async Python Scraper for Tokopedia
![PyPI](https://img.shields.io/pypi/v/tokopaedi-async) [![PyPI Downloads](https://static.pepy.tech/badge/tokopaedi-async)](https://pepy.tech/projects/tokopaedi-async) ![GitHub Repo stars](https://img.shields.io/github/stars/pandamoon21/tokopaedi-async?style=social) [![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://github.com/pandamoon21/tokopaedi-async/blob/main/LICENSE) ![GitHub forks](https://img.shields.io/github/forks/pandamoon21/tokopaedi-async?style=social)

**Extract product data, reviews, and search results from Tokopedia with ease.**

tokopaedi-async is a high-performance fork of the original [**Tokopaedi**](https://github.com/hilmiazizi/tokopaedi) library. It leverages Python's asyncio and curl_cffi to perform massive data extraction concurrently, making it significantly faster for bulk operations like enriching product details or fetching thousands of reviews.


![Tokopaedi Runtime](https://github.com/pandamoon21/tokopaedi-async/blob/main/image/runtime.png?raw=true)

## Key Features

- 🚀 **Asynchronous & Concurrent**: Built on asyncio for non-blocking I/O. Fetch details for more products in the time it takes to fetch one.
- 🔍 **Product Search**: Search products with advanced filters (price, rating, condition, official store, etc.).
- 📦 **Detailed Product Data**: Retrieve rich product details, including variants, pricing, stock, and media.
- 💬 **Reviews Scraper**: Scrape product reviews with ratings, timestamps, and more.
- 🛡️ **Smart Anti-Detection**: Uses curl_cffi to mimic real browser fingerprints (JA3/TLS) and rotating user agents.
- 📊 **JSON Export**: Easy serialization to JSON or Pandas DataFrame.


## Installation
Tokopaedi is available on PyPi: [https://pypi.org/project/tokopaedi-async/](https://pypi.org/project/tokopaedi-async/)

Install Tokopaedi via pip:

```bash
pip install tokopaedi-async
```

##  Quick Start
Since this library is asynchronous, you must run it within an `async` function using `asyncio`.
```python
import asyncio
import json
from tokopaedi import search, SearchFilters, get_product

async def main():
    # 1. Setup Filters (Optional)
    filters = SearchFilters(
        bebas_ongkir_extra=True,
        pmin=15000000,
        pmax=25000000,
        rt=4.5
    )

    print("🔍 Searching...")
    # 'await' is required for search
    results = await search("Asus Zenbook S14 32GB", max_result=100, debug=True, filters=filters)
    
    # 2. Parallel Enrichment
    # This runs 20+ concurrent requests to fetch details/reviews almost instantly
    print(f"⚡ Enriching data for {len(results)} products...")
    await results.enrich_details(debug=True)
    await results.enrich_reviews(max_result=50, debug=True)

    # 3. Save to JSON
    with open('result.json', 'w') as f:
        f.write(json.dumps(results.json(), indent=4))
    print("✅ Done!")

if __name__ == "__main__":
    asyncio.run(main())
```

## 📘 API Overview

### 🔍 `async search(keyword: str, max_result: int = 100, filters: Optional[SearchFilters] = None, debug: bool = False) -> SearchResults`

Search for products from Tokopedia.

```python
results = await search(
    keyword="Laptop Gaming", 
    max_result=100, 
    filters=filters, 
    debug=True
)
```

**Parameters:**

-   `keyword`: string keyword (e.g., `"logitech mouse"`).
    
-   `max_result`: Expected number of results to return.
    
-   `filters`: Optional `SearchFilters` instance to narrow search results.
    
-   `debug`: Show debug message if True
    

**Returns:**

-   A `SearchResults` instance (list-like object of `ProductSearchResult`), supporting `.json()` for easy export.
    

----------

### 📦 `async get_product(product_id: Optional[Union[int, str]] = None, url: Optional[str] = None, debug: bool = False) -> ProductData`

Fetch detailed information for a given Tokopedia product.

**Parameters:**

- `product_id`: (Optional) The product ID returned from `search()`. If provided, this will take precedence over `url`.
- `url`: (Optional) The full product URL. Used only if `product_id` is not provided.
- `debug`: If `True`, prints debug output for troubleshooting.

> ⚠️ Either `product_id` or `url` must be provided. If both are given, `product_id` is used and `url` is ignored.

**Returns:**

- A `ProductData` instance containing detailed information such as product name, pricing, variants, media, stock, rating, etc.
- Supports `.json()` for easy serialization (e.g., to use with `pandas` or export as `.json`).

----------

### 🗣️ `async get_reviews(product_id: Optional[Union[int, str]] = None, url: Optional[str] = None, max_count: int = 20, debug: bool = False) -> List[ProductReview]`

Scrape customer reviews for a given product.

**Parameters:**

- `product_id`: (Optional) The product ID to fetch reviews for. Takes precedence over `url` if both are provided.
- `url`: (Optional) Full product URL. Used only if `product_id` is not provided.
- `max_count`: Maximum number of reviews to fetch (default: 20).
- `debug`: Show debug messages if `True`.

> ⚠️ Either `product_id` or `url` must be provided.

**Returns:**

- A list of `ProductReview` objects.
- Each object supports `.json()` for serialization (e.g., for use with `pandas` or JSON export).

**Returns:**

-   A new `SearchResults` object with `.product_detail` and `.product_reviews` fields filled in (if data was provided).
    
----------
###  `SearchFilters` – Optional Search Filters

Use `SearchFilters` to refine your search results. All fields are optional. Pass it into the `search()` function via the `filters` argument.

#### Example:
```python
from tokopaedi_async import SearchFilters

filters = SearchFilters(
    pmin=100000,           # Min Price
    pmax=5000000,          # Max Price
    condition=1,           # 1=New, 2=Used
    shop_tier=2,           # 2=Official Store, 3=Power Merchant
    rt=4.5,                # Min Rating
    latest_product=30,     # Added in last 30 days
    is_discount=True,      # Only discounted items
    is_fulfillment=True,   # "Dilayani Tokopedia"
    is_plus=True           # Tokopedia PLUS
)

results = await search("logitech mouse", filters=filters)
```

#### Available Fields:

| Field                 | Type     | Description                                       | Accepted Values                  |
|----------------------|----------|---------------------------------------------------|----------------------------------|
| `pmin`               | `int`    | Minimum price (in IDR)                            | e.g., `100000`                   |
| `pmax`               | `int`    | Maximum price (in IDR)                            | e.g., `1000000`                  |
| `condition`          | `int`    | Product condition                                 | `1` = New, `2` = Used            |
| `shop_tier`          | `int`    | Type of shop                                      | `2` = Mall, `3` = Power Shop     |
| `rt`                 | `float`  | Minimum rating                                    | e.g., `4.5`                      |
| `latest_product`     | `int`    | Product recency filter                            | `7`, `30`, `90`               |
| `bebas_ongkir_extra` | `bool`   | Filter for extra free shipping                   | `True` / `False`                 |
| `is_discount`        | `bool`   | Only show discounted products                    | `True` / `False`                 |
| `is_fulfillment`     | `bool`   | Only Fulfilled by Tokopedia                      | `True` / `False`                 |
| `is_plus`            | `bool`   | Only Tokopedia PLUS sellers                      | `True` / `False`                 |
| `cod`                | `bool`   | Cash on delivery available                        | `True` / `False`                 |


## Product Details & Reviews Enrichment

Tokopaedi supports data enrichment to attach detailed product information and customer reviews directly to search results. This is useful when you want to go beyond basic search metadata and analyze full product details or customer feedback.
#### Example:
```python
# Enrich search results
results = search("Asus Zenbook S14 32GB", max_result=10, debug=True, filters=filters)
results.enrich_details(debug=True)
results.enrich_reviews(max_result=50, debug=True)

# Enrich product detail with reviews
product = get_product(url="https://www.tokopedia.com/asusrogindonesia/asus-tuf-a15-fa506ncr-ryzen-7-7435hs-rtx3050-4gb-8gb-512gb-w11-ohs-o365-15-6fhd-144hz-ips-rgb-blk-r735b1t-om-laptop-8gb-512gb-4970d?extParam=whid%3D17186756&aff_unique_id=&channel=others&chain_key=")
product.enrich_reviews(max_result=50, debug=True)
```

Enrichment methods are available on both the `SearchResults` container and individual `ProductData` objects:

### On `SearchResults`

```python
# Fetches details for ALL items in the list concurrently
await results.enrich_details() 

# Fetches reviews for ALL items in the list concurrently
await results.enrich_reviews(max_result=20)
```

- `enrich_details(debug: bool = False) -> None`  
  Enriches all items in the result with detailed product info.  
  - `debug`: If `True`, logs each enrichment step.

- `enrich_reviews(max_result: int = 10, debug: bool = False) -> None`  
  Enriches all items with customer reviews (up to `max_result` per product).  
  - `max_result`: Number of reviews to fetch for each product.  
  - `debug`: If `True`, logs the review enrichment process.

### On `ProductData`

```python
await product.enrich_details()
await product.enrich_reviews()
```

- `enrich_details(debug: bool = False) -> None`  
  Enriches this specific product with detailed information.

- `enrich_reviews(max_result: int = 10, debug: bool = False) -> None`  
  Enriches this product with customer reviews.

This design allows for flexibility: enrich a full result set at once, or enrich individual items selectively as needed.


## 📋 Changelog

### 0.1.0
- Initial release based on [tokopaedi 0.2.3](https://github.com/hilmiazizi/tokopaedi/tree/3d74be192ff9c4e278df24eb930329a1117c68ea)

## Disclaimer

This is an unofficial library and is not affiliated with, endorsed, or supported by Tokopedia. It is intended for educational and research purposes only. Please use responsibly and respect the website's Terms of Service.

## Credits & License

Original library by [**Hilmi Azizi**](https://hilmiazizi.com) - Thanks :)

Async fork maintained by [**pandamoon21**](https://github.com/pandamoon21).

Distributed under the MIT License. See [LICENSE](https://github.com/pandamoon21/tokopaedi-async/blob/main/LICENSE) for more information.
