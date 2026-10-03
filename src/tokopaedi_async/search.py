"""Product search.

:func:`parse_search` is the pure seam (GraphQL JSON in, ``ProductData`` list
out). :func:`search` is the network-bound interface: it builds the query
parameters, walks pages via :mod:`tokopaedi_async.pagination`, and dedupes by
product id as pages arrive.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
from urllib.parse import parse_qs, quote

from .pagination import paginate
from .tokopaedi_types import ProductData, SearchResults, TokopaediShop, shop_resolver
from .transport import post_graphql

logger = logging.getLogger(__name__)

OPERATION = "SearchResult/getProductResult"

# Base query string the Tokopedia iOS app sends for a normal search.
_BASE_PARAM = (
    "user_warehouseId=0&user_shopId=0&user_postCode=10110&srp_initial_state=false"
    "&breadcrumb=true&ep=product&user_cityId=0&q={keyword}&related=true&source=search"
    "&srp_enter_method=normal_search&enter_method=normal_search&l_name=sre&user_districtId=0"
    "&srp_feature_id=&catalog_rows=0&page=1&srp_component_id=02.01.00.00&ob=0&srp_sug_type="
    "&src=search&with_template=true&show_adult=false&srp_direct_middle_page=false"
    "&channel=product%20search&rf=false&navsource=home&use_page=true&dep_id=&device=ios"
)

_QUERY = """query Search_SearchProduct($params: String!, $query: String!) {
 global_search_navigation(keyword: $query, size: 5, device: "ios", params: $params){
 data {
 source
 keyword
 title
 nav_template
 background
 see_all_applink
 show_topads
 info
 list {
 category_name
 name
 info
 image_url
 subtitle
 strikethrough
 background_url
 logo_url
 applink
 component_id
 }
 component_id
 tracking_option
 }
 }
 searchProductV5(params: $params) {
 header {
 totalData
 responseCode
 keywordProcess
 keywordIntention
 componentID
 meta {
 productListType
 hasPostProcessing
 hasButtonATC
 dynamicFields
 }
 isQuerySafe
 additionalParams
 autocompleteApplink
 backendFilters
 backendFiltersToggle
 }
 data {
 totalDataText
 products {
 id
 ttsProductID
 name
 url
 applink
 mediaURL {
  image
  image300
  image500
  image700
  videoCustom
 }
 shop {
  id
  name
  url
  city
  ttsSellerID
 }
 badge {
  title
  url
 }
 price {
  text
  number
  range
  original
  discountPercentage
 }
 freeShipping {
  url
 }
 labelGroups {
  id
  position
  title
  type
  url
  styles {
  key
  value
  }
 }
 category {
  id
  name
  breadcrumb
  gaKey
 }
 rating
 wishlist
 meta {
  parentID
  warehouseID
  isPortrait
  isImageBlurred
  dynamicFields
 }
 stock {
  sold
  ttsSKUID
 }
 }
 }
 }
}
"""


def parse_search(payload: Dict[str, Any]) -> List[ProductData]:
    """Turn a decoded ``searchProductV5`` response into ``ProductData`` items.

    Pure function: no network, no globals. Returns ``[]`` when the response
    carries no product list, so an empty page and a failed page stay
    distinguishable at the call site.
    """
    products = (
        payload.get("data", {})
        .get("searchProductV5", {})
        .get("data", {})
        .get("products")
    )
    if not products:
        return []

    results: List[ProductData] = []
    for product in products:
        price_data = product.get("price", {})
        shop_info = product.get("shop", {}) or {}
        stock = product.get("stock", {}) or {}
        rating = product.get("rating")

        results.append(
            ProductData(
                product_id=product.get("id"),
                product_sku=stock.get("ttsSKUID"),
                product_name=product.get("name"),
                category=(product.get("category") or {}).get("name"),
                url=product.get("url"),
                sold_count=stock.get("sold"),
                price_original=price_data.get("original"),
                price=price_data.get("number"),
                price_text=price_data.get("text"),
                rating=float(rating) if rating else None,
                main_image=(product.get("mediaURL") or {}).get("image700"),
                shop=TokopaediShop(
                    shop_id=shop_info.get("id"),
                    name=shop_info.get("name"),
                    city=shop_info.get("city"),
                    url=shop_info.get("url"),
                    shop_type=shop_resolver(str((product.get("badge") or {}).get("url"))),
                ),
            )
        )
    return results


def source_results(payload: Dict[str, Any]) -> Optional[SearchResults]:
    """Extract the search wrapper, or ``None`` when the operation is absent.

    Distinguishes "Tokopedia did not return a search payload" (``None``) from
    "the search returned zero products" (an empty ``SearchResults``).
    """
    section = payload.get("data", {}).get("searchProductV5")
    if not section:
        return None
    return SearchResults(parse_search(payload))


def dedupe(items) -> SearchResults:
    """Collapse a sequence of products to one entry per ``product_id``."""
    if not items:
        return SearchResults()
    return SearchResults(list({item.product_id: item for item in items}.values()))


def filters_to_query(filters) -> str:
    """Serialise a :class:`SearchFilters` into a query-string fragment.

    ``None`` fields are omitted so they do not override the API defaults.
    """
    filter_dict = {k: v for k, v in vars(filters).items() if v is not None}
    return "&".join(f"{k}={quote(str(v), safe=',')}" for k, v in filter_dict.items())


def merge_params(original: str, additional: Optional[str] = None) -> str:
    """Merge two query strings; keys in ``additional`` win."""
    merged = {k: v[0] for k, v in parse_qs(original).items()}
    if additional:
        merged.update({k: v[0] for k, v in parse_qs(additional).items()})
    return "&".join(f"{k}={quote(str(v), safe=',')}" for k, v in merged.items())


async def search(
    keyword: str = "zenbook 14 32gb",
    max_result: int = 100,
    filters=None,
    debug: bool = False,
    session=None,
) -> SearchResults:
    """Search Tokopedia for ``keyword`` and return up to ``max_result`` products.

    Args:
        keyword: Search term.
        max_result: Upper bound on returned products. Pagination stops as soon
            as it is reached.
        filters: Optional :class:`~tokopaedi_async.SearchFilters`.
        debug: Log per-page progress at DEBUG level.
        session: Optional caller-owned ``AsyncSession`` for connection reuse.

    Returns:
        A :class:`SearchResults` container. Empty when nothing matched; the
        container is falsy, so ``if results:`` reads correctly.

    Pagination is iterative, dedupes by product id per page, and is bounded by
    ``max_pages`` (see :func:`tokopaedi_async.pagination.paginate`), so a
    cursor that never advances cannot hang the call.
    """
    base_param = _BASE_PARAM.format(keyword=quote(keyword))
    if filters is not None:
        base_param = merge_params(base_param, filters_to_query(filters))

    async def fetch_page(cursor: str):
        payload = {
            "query": _QUERY,
            "variables": {"params": cursor, "query": keyword},
        }
        response = await post_graphql(OPERATION, payload, session=session)
        if not response:
            return [], None

        page = source_results(response)
        if page is None:
            # Operation missing from the response: stop, don't loop.
            return [], None
        if debug:
            for item in page:
                logger.debug("%s - %s...", item.product_id, (item.product_name or "")[:40])

        next_cursor = (
            response.get("data", {})
            .get("searchProductV5", {})
            .get("header", {})
            .get("additionalParams")
        )
        return list(page), next_cursor

    items = await paginate(
        fetch_page,
        start_state=base_param,
        max_result=max_result,
        key=lambda item: item.product_id,
    )
    return SearchResults(items)
