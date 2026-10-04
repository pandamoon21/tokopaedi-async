"""tokopaedi-async — async scraper for Tokopedia's internal GraphQL API.

Public interface
----------------
Network-bound (async):

* :func:`search` — search products, paginated.
* :func:`get_product` — fetch one product's full detail.
* :func:`get_reviews` — fetch one product's reviews, paginated.
* :func:`browse` — search + batch enrichment in one call.

Pure (no network, test seams):

* :func:`parse_search`, :func:`parse_product`, :func:`parse_reviews` — turn a
  decoded GraphQL response into dataclasses.

Types:

* :class:`SearchFilters`, :class:`SearchResults`, :class:`ProductData`,
  :class:`ProductReview`, :class:`TokopaediShop`.
"""

__version__ = "0.2.2"

import logging
from dataclasses import dataclass
from typing import Optional

from .concurrency import DEFAULT_CONCURRENCY, bounded_gather
from .get_product import get_product, parse_product, parse_tokped_url
from .get_reviews import get_reviews, parse_reviews
from .pagination import paginate
from .search import search, parse_search
from .tokopaedi_types import ProductData, ProductReview, SearchResults, TokopaediShop

logger = logging.getLogger(__name__)

__all__ = [
    "__version__",
    "search",
    "get_product",
    "get_reviews",
    "browse",
    "parse_search",
    "parse_product",
    "parse_reviews",
    "parse_tokped_url",
    "paginate",
    "bounded_gather",
    "DEFAULT_CONCURRENCY",
    "SearchFilters",
    "SearchResults",
    "ProductData",
    "ProductReview",
    "TokopaediShop",
]


@dataclass
class SearchFilters:
    """Optional filters for :func:`search`.

    Every field defaults to ``None``, which means "do not constrain". Only the
    fields you set are sent to the API.
    """

    #: Free-shipping products only ("Bebas Ongkir Extra").
    bebas_ongkir_extra: Optional[bool] = None

    #: Discounted products only.
    is_discount: Optional[bool] = None

    #: ``1`` = new, ``2`` = used.
    condition: Optional[int] = None

    #: Shop tier: ``2`` = Mall / Official Store, ``3`` = Power Shop / Power Merchant.
    shop_tier: Optional[int] = None

    #: Minimum price in IDR.
    pmin: Optional[int] = None

    #: Maximum price in IDR.
    pmax: Optional[int] = None

    #: Fulfilled by Tokopedia only.
    is_fulfillment: Optional[bool] = None

    #: Tokopedia Plus products only.
    is_plus: Optional[bool] = None

    #: Cash-on-delivery eligible products only.
    cod: Optional[bool] = None

    #: Minimum average rating, ``0.0``–``5.0``.
    rt: Optional[float] = None

    #: Product age in days: ``7``, ``30``, or ``90``.
    latest_product: Optional[int] = None


async def browse(
    keyword: str,
    max_result: int = 20,
    filters: Optional[SearchFilters] = None,
    reviews_per_product: int = 0,
    concurrency: int = DEFAULT_CONCURRENCY,
    session=None,
) -> SearchResults:
    """Search, then enrich every result — the common bulk workflow in one call.

    Args:
        keyword: Search term.
        max_result: Maximum number of products to return.
        filters: Optional :class:`SearchFilters`.
        reviews_per_product: When greater than ``0``, also fetch this many
            reviews per product.
        concurrency: Maximum in-flight enrichment requests. Lower it when the
            host is small (serverless free tier) or Tokopedia is throttling.
        session: Optional caller-owned ``AsyncSession``.

    Returns:
        A :class:`SearchResults` whose items carry details, and reviews when
        requested. Enrichment failures are logged and skipped, so a partial
        result is still returned.
    """
    results = await search(keyword, max_result=max_result, filters=filters, session=session)
    await results.enrich_details(concurrency=concurrency, session=session)
    if reviews_per_product > 0:
        await results.enrich_reviews(
            max_result=reviews_per_product, concurrency=concurrency, session=session
        )
    return results
