# Tokopaedi Async 🚀

**High-Performance Async Python Scraper for Tokopedia**

![PyPI](https://img.shields.io/pypi/v/tokopaedi-async) 
[![PyPI Downloads](https://static.pepy.tech/badge/tokopaedi-async)](https://pepy.tech/projects/tokopaedi-async) 
![GitHub Repo stars](https://img.shields.io/github/stars/pandamoon21/tokopaedi-async?style=social) 
![GitHub forks](https://img.shields.io/github/forks/pandamoon21/tokopaedi-async?style=social) 
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python Version](https://img.shields.io/badge/python-3.9%2B-blue)](https://www.python.org/downloads/)

**tokopaedi-async** is a high-performance, asynchronous fork of the original [Tokopaedi](https://github.com/hilmiazizi/tokopaedi) library. It leverages Python's `asyncio` and `curl_cffi` to perform massive data extraction concurrently, making it significantly faster for bulk operations like enriching product details or fetching thousands of reviews.

![Tokopaedi Runtime](https://github.com/pandamoon21/tokopaedi-async/blob/main/image/runtime.png?raw=true)

---

## ✨ Key Features

- 🚀 **Asynchronous & Concurrent**: Built on `asyncio` for non-blocking I/O.
- 🛡️ **Smart Anti-Detection**: Uses `curl_cffi` to mimic real browser fingerprints (JA3/TLS) and randomized device data.
- 🔍 **Advanced Search**: Filter by price, rating, condition, shop tier, and more.
- 📦 **Rich Product Data**: Full extraction of variants, pricing, stock, media, and descriptions.
- 💬 **Review Scraping**: Fetch customer reviews with ratings, images, and video attachments.
- 📊 **Developer Friendly**: Clean `dataclass` models with easy JSON/Pandas export.

---

## 🛠️ Installation

Install via `pip`:
```bash
pip install tokopaedi-async
```

Or using `poetry`:
```bash
poetry add tokopaedi-async
```

---

## 🚀 Quick Start

```python
import asyncio
import json
from tokopaedi_async import search, SearchFilters

async def main():
    # 1. Define Search Filters
    filters = SearchFilters(
        pmin=1000000,
        rt=4.5,
        shop_tier=2 # Official Store
    )

    print("🔍 Searching for Laptops...")
    results = await search("Asus Zenbook", max_result=20, filters=filters)
    
    # 2. Parallel Enrichment (Concurrency default: 20)
    print(f"⚡ Fetching details & reviews for {len(results)} products...")
    await results.enrich_details()
    await results.enrich_reviews(max_result=10)

    # 3. Export Data
    print(json.dumps(results.json()[0], indent=2))

if __name__ == "__main__":
    asyncio.run(main())
```

---

## 📘 API Reference

For a full list of functions, parameters, and data models, see the [**Detailed API Documentation**](docs/API.md).

### Core Functions

| Function | Description |
|----------|-------------|
| `await search(...)` | Search for products with optional filters and recursion. |
| `await get_product(...)` | Fetch detailed data for a specific product ID or URL. |
| `await get_reviews(...)` | Scrape reviews for a product with pagination support. |

### Data Enrichment

The `SearchResults` and `ProductData` objects support high-speed enrichment:

- `await results.enrich_details(concurrency=20)`
- `await results.enrich_reviews(max_result=10, concurrency=20)`

> [!TIP]
> Enrichment uses an `asyncio.Semaphore` to manage concurrency. You can adjust the `concurrency` parameter to balance speed and stability.

---

## ⚙️ Search Filters

Use `SearchFilters` to narrow down your results:

| Field | Type | Description |
|-------|------|-------------|
| `pmin` / `pmax` | `int` | Price range in IDR. |
| `condition` | `int` | `1` = New, `2` = Used. |
| `shop_tier` | `int` | `2` = OS (Official Store), `3` = Power Merchant. |
| `rt` | `float` | Minimum rating (e.g., `4.5`). |
| `is_discount` | `bool` | Only products with discounts. |
| `bebas_ongkir_extra`| `bool` | Only "Bebas Ongkir Extra". |

---

## 🧪 Development & Testing

1. Clone the repository:
   ```bash
   git clone https://github.com/pandamoon21/tokopaedi-async.git
   ```
2. Install dependencies:
   ```bash
   poetry install
   ```
3. Run the example script:
   ```bash
   python example.py
   ```
4. Run tests:
   ```bash
   pytest
   ```

---

## 🛡️ Disclaimer

This is an unofficial library and is not affiliated with, endorsed, or supported by Tokopedia. It is intended for educational and research purposes only. Please use responsibly and respect Tokopedia's Terms of Service.

## 📜 Credits & License

- Original library by [Hilmi Azizi](https://hilmiazizi.com).
- Async fork by [pandamoon21](https://github.com/pandamoon21).
- Distributed under the **MIT License**.
