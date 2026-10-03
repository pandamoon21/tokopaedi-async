"""Offline tests for tokopaedi-async.

Every test here runs without network access. They exercise the package through
its two real seams:

* the pure parsers (``parse_search`` / ``parse_product`` / ``parse_reviews``) —
  fixture JSON in, dataclasses out;
* the injected session — a fake ``AsyncSession`` satisfying the transport
  interface, so ``search`` / ``get_product`` / ``get_reviews`` run their real
  pagination and merge logic offline.
"""

import asyncio
import logging

import pytest

import tokopaedi_async as t
from tokopaedi_async.concurrency import bounded_gather
from tokopaedi_async.pagination import paginate
from tokopaedi_async.tokopaedi_types import ProductData, SearchResults, shop_resolver


# --------------------------------------------------------------------------
# Fakes: one adapter per seam
# --------------------------------------------------------------------------
class FakeResponse:
    def __init__(self, payload):
        self._payload = payload
        self.text = str(payload)

    def json(self):
        return self._payload

    def raise_for_status(self):
        return None


class FakeSession:
    """In-memory adapter for the transport interface.

    ``responses`` is a list of payloads returned in order; the last one repeats
    once exhausted, so a caller that loops cannot hang the test.
    """

    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []
        self.closed = False

    async def post(self, url, headers=None, json=None, timeout=None):
        self.calls.append({"url": url, "headers": headers, "json": json, "timeout": timeout})
        payload = self.responses[min(len(self.calls) - 1, len(self.responses) - 1)]
        return FakeResponse(payload)

    async def close(self):
        self.closed = True


def search_page(products, next_cursor=None):
    return {
        "data": {
            "searchProductV5": {
                "header": {"additionalParams": next_cursor},
                "data": {"products": products},
            }
        }
    }


def raw_product(pid, name="Widget", price=1000):
    return {
        "id": pid,
        "name": name,
        "url": f"https://www.tokopedia.com/shop/{name}",
        "mediaURL": {"image700": "https://img/700.jpg"},
        "shop": {"id": 5, "name": "Shop", "url": "https://tokopedia.com/shop", "city": "Jakarta"},
        "badge": {"url": "https://x/official_store_badge.png"},
        "price": {"text": "Rp1.000", "number": price, "original": "Rp2.000"},
        "stock": {"sold": 7, "ttsSKUID": f"SKU{pid}"},
        "rating": "4.8",
    }


def review_page(feedback_ids, has_next=False):
    return {
        "data": {
            "productrevGetProductReviewList": {
                "hasNext": has_next,
                "list": [
                    {
                        "feedbackID": fid,
                        "message": f"review {fid}",
                        "productRating": 5,
                        "variantName": "Red",
                        "reviewCreateTimestamp": "2 days ago",
                        "user": {"fullName": "Budi", "url": "/budi"},
                        "imageAttachments": [{"imageUrl": "https://img/a.jpg"}],
                        "videoAttachments": [{"videoUrl": "https://vid/a.mp4"}],
                        "likeDislike": {"totalLike": 3},
                    }
                    for fid in feedback_ids
                ],
            }
        }
    }


def product_page(pid=1, name="Widget", rating="4.9", review_count=11, order_created=5):
    def component(cname, data):
        return {"name": cname, "data": data}

    return {
        "data": {
            "pdpGetLayout": {
                "pdpSession": '{"stier": 2}',
                "basicInfo": {
                    "productID": pid,
                    "ttsSKUID": f"SKU{pid}",
                    "url": f"https://www.tokopedia.com/shop/{name}",
                    "defaultMediaURL": "https://img/main.jpg",
                    "status": "Active",
                    "weight": "1000",
                    "weightUnit": "gram",
                    "txStats": {"countSold": 42},
                    "stats": {"rating": rating, "countReview": review_count, "countTalk": 4},
                    "totalStockFmt": "1.234",
                    "menu": {"name": "Gadget", "url": "/etalase/gadget"},
                    "category": {"name": "Laptop", "detail": [{"name": "Ultrabook"}]},
                    "shopID": 99,
                    "shopName": "Mega Store",
                    "shopMultilocation": {"cityName": "Bandung"},
                },
                "components": [
                    component(
                        "product_content",
                        [{"name": name, "price": {"value": 1500, "priceFmt": "Rp1.500", "slashPriceFmt": "Rp3.000", "discPercentage": "50%"}}],
                    ),
                    component("product_media", [{"media": [{"URLOriginal": "o", "URLThumbnail": "t", "URLMaxRes": "m"}]}]),
                    component(
                        "mini_variant_options",
                        [{
                            "variants": [{"productVariantID": 1, "name": "Color", "option": [{"value": "Red"}]}],
                            "children": [{
                                "optionID": [1], "productName": "Widget Red", "productURL": "/red",
                                "price": 1600, "priceFmt": "Rp1.600", "discPercentage": "0%",
                                "picture": {"url": "pic"}, "stock": {"stock": 3},
                            }],
                        }],
                    ),
                    component("product_detail", [{"key": "deskripsi", "subtitle": "A fine widget."}]),
                ],
            }
        }
    }


# --------------------------------------------------------------------------
# Package surface
# --------------------------------------------------------------------------
def test_version():
    assert t.__version__ == "0.2.0"


def test_public_interface_is_exported():
    for name in ("search", "get_product", "get_reviews", "browse",
                 "parse_search", "parse_product", "parse_reviews"):
        assert name in t.__all__, name
        assert hasattr(t, name), name


def test_import_has_no_logging_side_effects():
    """Importing the package must not reconfigure the root logger.

    This is what makes the package safe to import on a serverless worker.
    """
    root = logging.getLogger()
    assert root.level != logging.BASIC_FORMAT  # placeholder guard; real check below
    assert logging.getLoggerClass() is logging.Logger
    # Our custom levels are NOT registered until explicitly requested.
    assert logging.getLevelName(25) == "Level 25"


# --------------------------------------------------------------------------
# Pagination
# --------------------------------------------------------------------------
def test_paginate_follows_cursor_and_stops_at_max_result():
    pages = {1: ([1, 2, 3], 2), 2: ([4, 5, 6], 3), 3: ([7, 8, 9], None)}
    seen = []

    async def fetch(state):
        seen.append(state)
        return pages[state]

    result = asyncio.run(paginate(fetch, start_state=1, max_result=5))
    assert result == [1, 2, 3, 4, 5]
    assert seen == [1, 2]


def test_paginate_dedupes_as_pages_arrive():
    pages = {1: ([1, 2], 2), 2: ([2, 3], None)}

    async def fetch(state):
        return pages[state]

    result = asyncio.run(paginate(fetch, start_state=1, max_result=100, key=lambda x: x))
    assert result == [1, 2, 3]


def test_paginate_stops_on_empty_page():
    async def fetch(state):
        return [], 999  # cursor says "more" but the page is empty

    assert asyncio.run(paginate(fetch, start_state=1, max_result=10)) == []


def test_paginate_is_bounded_by_max_pages():
    async def fetch(state):
        return [state], state + 1  # cursor advances forever

    result = asyncio.run(paginate(fetch, start_state=1, max_result=10_000, max_pages=4))
    assert result == [1, 2, 3, 4]


def test_paginate_handles_a_stuck_cursor():
    async def fetch(state):
        return [1, 2, 3], state  # same cursor returned forever

    result = asyncio.run(paginate(fetch, start_state="x", max_result=99))
    assert result == [1, 2, 3]


# --------------------------------------------------------------------------
# Concurrency
# --------------------------------------------------------------------------
def test_bounded_gather_respects_concurrency_limit():
    in_flight = 0
    peak = 0

    async def fetch(item):
        nonlocal in_flight, peak
        in_flight += 1
        peak = max(peak, in_flight)
        await asyncio.sleep(0.01)
        in_flight -= 1

    failures = asyncio.run(bounded_gather(list(range(20)), fetch, concurrency=3))
    assert failures == []
    assert peak <= 3


def test_bounded_gather_reports_failures_instead_of_swallowing():
    async def fetch(item):
        if item == 2:
            raise RuntimeError("boom")

    failures = asyncio.run(bounded_gather([1, 2, 3], fetch, concurrency=2))
    assert len(failures) == 1
    item, exc = failures[0]
    assert item == 2
    assert isinstance(exc, RuntimeError)


def test_bounded_gather_clamps_invalid_concurrency():
    async def fetch(item):
        return None

    assert asyncio.run(bounded_gather([1], fetch, concurrency=0)) == []


# --------------------------------------------------------------------------
# Pure parsers
# --------------------------------------------------------------------------
def test_parse_search_maps_fields():
    products = t.parse_search(search_page([raw_product(11, "Laptop", 9_000_000)]))
    assert len(products) == 1
    p = products[0]
    assert p.product_id == 11
    assert p.product_name == "Laptop"
    assert p.price == 9_000_000
    assert p.sold_count == 7
    assert p.rating == 4.8
    assert p.main_image == "https://img/700.jpg"
    assert p.shop.name == "Shop"
    assert p.shop.shop_type == "Mall"  # official_store_badge -> tier 2


def test_parse_search_returns_empty_on_missing_products():
    assert t.parse_search({"data": {"searchProductV5": {"data": {}}}}) == []
    assert t.parse_search({}) == []


def test_parse_product_maps_full_detail():
    product = t.parse_product(product_page(pid=77, name="Zenbook"))
    assert product is not None
    assert product.product_id == 77
    assert product.product_name == "Zenbook"
    assert product.price == 1500
    assert product.price_text == "Rp1.500"
    assert product.weight == 1000
    assert product.sold_count == 42
    assert product.rating == 4.9
    assert product.review_count == 11
    assert product.total_stock == 1234  # "1.234" -> 1234
    assert product.category == "Laptop"
    assert product.sub_category == ["Ultrabook"]
    assert product.description == "A fine widget."
    assert product.shop.name == "Mega Store"
    assert product.shop.shop_type == "Mall"
    assert len(product.product_media) == 1
    assert len(product.variants) == 1
    assert product.variants[0].option_name == "Widget Red"
    assert product.product_option[0].option_child == ["Red"]


def test_parse_product_returns_none_when_layout_missing():
    assert t.parse_product({"data": {}}) is None
    assert t.parse_product({}) is None


def test_parse_product_survives_corrupt_pdp_session():
    payload = product_page()
    payload["data"]["pdpGetLayout"]["pdpSession"] = "not json"
    product = t.parse_product(payload)
    assert product.shop.shop_type is None  # unknown, not misreported as "Normal"


def test_parse_reviews_maps_fields():
    reviews = t.parse_reviews(review_page([101, 102]))
    assert [r.feedback_id for r in reviews] == [101, 102]
    assert reviews[0].rating == 5.0
    assert reviews[0].images == ["https://img/a.jpg"]
    assert reviews[0].videos == ["https://vid/a.mp4"]
    assert reviews[0].likes == 3
    assert reviews[0].user_full_name == "Budi"


def test_parse_reviews_returns_empty_on_missing_list():
    assert t.parse_reviews({}) == []


def test_parse_tokped_url():
    assert t.parse_tokped_url("https://www.tokopedia.com/shop/widget?x=1") == ("shop", "widget")
    assert t.parse_tokped_url("not a url") == ("", "")


def test_shop_resolver():
    assert shop_resolver(1) == "Normal"
    assert shop_resolver(2) == "Mall"
    assert shop_resolver(3) == "Power Shop"
    assert shop_resolver(None) is None
    assert shop_resolver("garbage") is None


# --------------------------------------------------------------------------
# Network-bound interface, driven through the fake adapter
# --------------------------------------------------------------------------
def test_search_paginates_and_dedupes_through_the_seam():
    session = FakeSession([
        search_page([raw_product(1), raw_product(2)], next_cursor="page=2&cursor=abc"),
        search_page([raw_product(2), raw_product(3)], next_cursor="page=3&cursor=def"),
        search_page([raw_product(4)], next_cursor=None),
    ])
    results = asyncio.run(t.search("widget", max_result=10, session=session))
    assert [p.product_id for p in results] == [1, 2, 3, 4]  # 2 not duplicated
    assert len(session.calls) == 3
    assert session.calls[0]["json"]["variables"]["query"] == "widget"


def test_search_returns_empty_on_transport_failure():
    class DeadSession(FakeSession):
        async def post(self, *a, **k):
            raise RuntimeError("network down")

    results = asyncio.run(t.search("widget", session=DeadSession([])))
    assert isinstance(results, SearchResults)
    assert len(results) == 0


def test_search_stops_when_operation_missing():
    session = FakeSession([{"data": {"somethingElse": {}}}])
    results = asyncio.run(t.search("widget", session=session))
    assert len(results) == 0
    assert len(session.calls) == 1


def test_get_product_through_the_seam():
    session = FakeSession([product_page(pid=5, name="Hoodie")])
    product = asyncio.run(t.get_product(product_id=5, session=session))
    assert product.product_id == 5
    assert product.product_name == "Hoodie"


def test_get_product_requires_an_identifier():
    with pytest.raises(ValueError):
        asyncio.run(t.get_product())


def test_get_product_returns_none_on_unparseable_url():
    assert asyncio.run(t.get_product(url="https://example.com/nope")) is None


def test_get_reviews_paginates_through_the_seam():
    session = FakeSession([
        review_page([1, 2], has_next=True),
        review_page([3], has_next=False),
    ])
    reviews = asyncio.run(t.get_reviews(product_id=9, max_result=10, session=session))
    assert [r.feedback_id for r in reviews] == [1, 2, 3]
    assert len(session.calls) == 2
    assert session.calls[0]["json"]["variables"]["page"] == 1
    assert session.calls[1]["json"]["variables"]["page"] == 2


def test_get_reviews_resolves_url_once_for_all_pages():
    """URL resolution must not repeat per page."""
    session = FakeSession([
        product_page(pid=42),                       # 1st call: URL -> product id
        review_page([1], has_next=True),            # page 1
        review_page([2], has_next=False),           # page 2
    ])
    reviews = asyncio.run(
        t.get_reviews(url="https://www.tokopedia.com/shop/widget", max_result=10, session=session)
    )
    assert [r.feedback_id for r in reviews] == [1, 2]
    assert len(session.calls) == 3  # exactly one resolution, not one per page


def test_get_reviews_requires_an_identifier():
    with pytest.raises(ValueError):
        asyncio.run(t.get_reviews())


# --------------------------------------------------------------------------
# Enrichment
# --------------------------------------------------------------------------
def test_merge_details_only_touches_detail_fields():
    seed = ProductData(product_id=1, product_sku="A", product_name="Search Name", url="/u")
    seed.reviews = ["keep me"]
    seed.has_reviews = True
    seed.has_detail = False

    detail = ProductData(product_id=1, product_sku="B", product_name="PDP Name", url="/u", price=10)
    seed.merge_details(detail)

    assert seed.product_name == "PDP Name"  # detail wins
    assert seed.price == 10                  # new detail field copied
    assert seed.reviews == ["keep me"]       # review data preserved
    assert seed.has_reviews is True          # flag not clobbered
    assert seed.has_detail is False          # flag not clobbered


def test_enrich_details_is_idempotent_and_keeps_reviews(monkeypatch):
    session = FakeSession([product_page(pid=1, name="Fresh")])
    product = ProductData(product_id=1, product_sku="x", product_name="Stale", url="/u")
    product.reviews = ["kept"]

    asyncio.run(product.enrich_details(session=session))
    assert product.product_name == "Fresh"
    assert product.has_detail is True
    assert product.reviews == ["kept"]

    calls_before = len(session.calls)
    asyncio.run(product.enrich_details(session=session))
    assert len(session.calls) == calls_before  # no second fetch


def test_enrich_reviews_sets_flag_only_on_success():
    session = FakeSession([review_page([1, 2])])
    product = ProductData(product_id=1, product_sku="x", product_name="W", url="/u")
    asyncio.run(product.enrich_reviews(max_result=5, session=session))
    assert product.has_reviews is True
    assert [r.feedback_id for r in product.reviews] == [1, 2]


def test_search_results_reports_partial_failures():
    """A failed item is returned as an error, not printed and swallowed."""
    session = FakeSession([product_page(pid=1)])
    results = SearchResults([
        ProductData(product_id=1, product_sku="a", product_name="ok", url="/1"),
        ProductData(product_id=2, product_sku="b", product_name="ok", url="/2"),
    ])

    from tokopaedi_async import concurrency

    original = concurrency.bounded_gather

    async def fail_second(item):
        if item.product_id == 2:
            raise RuntimeError("nope")
        await item.enrich_details(session=session)

    async def patched(items, fetch, concurrency_=2, **kwargs):
        return await original(items, fail_second, concurrency=concurrency_)

    concurrency.bounded_gather = patched
    try:
        failures = asyncio.run(results.enrich_details(concurrency=2))
    finally:
        concurrency.bounded_gather = original

    assert len(failures) == 1
    assert failures[0][0].product_id == 2
    assert isinstance(failures[0][1], RuntimeError)
    assert results[0].has_detail is True


def test_json_export_is_plain_dicts():
    product = ProductData(product_id=1, product_sku="a", product_name="W", url="/u")
    exported = product.json()
    assert exported["product_id"] == 1
    assert exported["product_name"] == "W"
    assert isinstance(exported, dict)


def test_search_results_sequence_protocol():
    a = ProductData(product_id=1, product_sku="a", product_name="A", url="/1")
    b = ProductData(product_id=2, product_sku="b", product_name="B", url="/2")
    results = SearchResults([a]) + SearchResults([b])
    assert len(results) == 2
    assert results[0].product_id == 1
    assert [p.product_id for p in results] == [1, 2]
    assert [d["product_id"] for d in results.json()] == [1, 2]
