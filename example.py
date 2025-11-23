import asyncio
import json
from tokopaedi import search, SearchFilters, get_product, get_reviews

async def main():
    filters = SearchFilters(
        bebas_ongkir_extra = True,
        pmin = 15000000,
        pmax = 25000000,
        rt = 4.5
    )

    print("--- 1. Melakukan Pencarian (Async) ---")
    results = await search("Asus Zenbook S14 32GB", max_result=10, debug=True, filters=filters)
    
    if results:
        print(f"Ditemukan {len(results)} produk. Melakukan enrichment data secara paralel...")
        
        # parallel
        await results.enrich_details(debug=True)
        await results.enrich_reviews(max_result=50, debug=True)

        with open('result.json','w') as f:
            f.write(json.dumps(results.json(), indent=4))
        print("Data hasil pencarian berhasil disimpan ke result.json")

    print("\n--- 2. Mengambil Produk Satuan (Async) ---")
    product_url = 'https://www.tokopedia.com/larocheposayofficial/la-roche-posay-pure-vit-c-eye-yeux-cream-15ml?source=homepage.top_carousel.0.38456'
    product = await get_product(url=product_url, debug=True)
    
    if product:
        await product.enrich_reviews(debug=True)
        print(json.dumps(product.json(), indent=4))

if __name__ == "__main__":
    asyncio.run(main())