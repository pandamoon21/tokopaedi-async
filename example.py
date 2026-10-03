"""End-to-end example: search, enrich, and export.

Run it with::

    python example.py

It performs real requests against Tokopedia. If you want the offline path
(no network), see ``tests/test_tokopaedi.py`` — the same calls run against a
fake session there.
"""

import asyncio
import json

from tokopaedi_async import SearchFilters, browse, get_product


async def find_laptops():
    """Search, then enrich every result with details and reviews."""
    filters = SearchFilters(
        bebas_ongkir_extra=True,
        pmin=15_000_000,
        pmax=25_000_000,
        rt=4.5,
    )

    print("1. Searching (paginated, async)...")
    # browse() = search + parallel enrichment in one call.
    # concurrency=8 instead of the default 10: this is a laptop-class query
    # and the shop rate-limits bursts.
    results = await browse(
        "Asus Zenbook S14 32GB",
        max_result=10,
        filters=filters,
        reviews_per_product=20,
        concurrency=8,
    )

    print(f"   {len(results)} products, details + reviews attached.")
    for product in list(results)[:3]:
        review_count = len(product.reviews or [])
        print(f"   - [{product.product_id}] {product.product_name} "
              f"| {product.price_text} | {review_count} reviews")

    with open("result.json", "w", encoding="utf-8") as handle:
        json.dump(results.json(), handle, indent=4, ensure_ascii=False)
    print("   Saved to result.json")


async def one_product():
    """Fetch a single product by URL, then attach its reviews."""
    url = (
        "https://www.tokopedia.com/larocheposayofficial/"
        "la-roche-posay-pure-vit-c-eye-yeux-cream-15ml"
    )

    print("\n2. Fetching one product by URL...")
    product = await get_product(url=url)
    if product is None:
        print("   Product could not be fetched (bad URL or request failed).")
        return

    await product.enrich_reviews(max_result=10)
    print(f"   {product.product_name} — {product.review_count} reviews on the PDP, "
          f"{len(product.reviews or [])} fetched")


async def main():
    await find_laptops()
    await one_product()


if __name__ == "__main__":
    asyncio.run(main())
