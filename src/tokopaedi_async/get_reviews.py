"""Customer review scraping.

:func:`parse_reviews` is the pure seam (GraphQL JSON in, ``ProductReview``
list out). :func:`get_reviews` walks pages via
:mod:`tokopaedi_async.pagination`.

The previous implementation re-resolved a product URL to an id on *every*
recursive page, so a URL-based call fetched the full PDP once per page. URL
resolution now happens exactly once, at the top.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List

from .get_product import get_product
from .pagination import paginate
from .tokopaedi_types import ProductReview
from .transport import post_graphql

logger = logging.getLogger(__name__)

OPERATION = "ProductReview/getProductReviewReadingList"

_QUERY = """query productrevGetProductReviewList($productID: String!, $page: Int!, $limit: Int!, $sortBy: String,
$filterBy: String, $opt: String) {
productrevGetProductReviewList(productID: $productID, page: $page, limit: $limit, sortBy: $sortBy,
filterBy: $filterBy, opt: $opt) {
list {
feedbackID
variantName
message
productRating
reviewCreateTime
reviewCreateTimestamp
isAnonymous
isReportable
reviewResponse {
message
createTime
}
user {
userID
fullName
image
url
label
}
imageAttachments {
attachmentID
imageThumbnailUrl
imageUrl
}
videoAttachments {
attachmentID
videoUrl
}
likeDislike {
totalLike
likeStatus
}
stats {
key
formatted
count
}
badRatingReasonFmt
}
shop {
shopID
name
url
image
}
variantFilter {
isUnavailable
ticker
}
hasNext
}
}"""

# The endpoint pages in fixed increments of 10.
PAGE_SIZE = 10


def parse_reviews(payload: Dict[str, Any]) -> List[ProductReview]:
    """Turn a decoded review-list response into ``ProductReview`` items.

    Pure function: no network, no globals. Returns ``[]`` when the response
    carries no review list.
    """
    items = (
        payload.get("data", {})
        .get("productrevGetProductReviewList", {})
        .get("list", [])
    )
    if not items:
        return []

    reviews: List[ProductReview] = []
    for item in items:
        user = item.get("user", {})
        response = item.get("reviewResponse", {}) or {}
        like_dislike = item.get("likeDislike", {})

        reviews.append(
            ProductReview(
                feedback_id=int(item.get("feedbackID", 0) or 0),
                variant_name=item.get("variantName", ""),
                message=item.get("message", ""),
                rating=float(item.get("productRating", 0) or 0),
                review_age=item.get("reviewCreateTimestamp", ""),
                user_full_name=user.get("fullName", ""),
                user_url=user.get("url", ""),
                response_message=response.get("message", ""),
                response_created_text=response.get("createTime", ""),
                images=[img.get("imageUrl", "") for img in item.get("imageAttachments", [])],
                videos=[v.get("videoUrl", "") for v in item.get("videoAttachments", [])],
                likes=like_dislike.get("totalLike", 0),
            )
        )
    return reviews


def has_next_page(payload: Dict[str, Any]) -> bool:
    """Whether the response advertises another review page."""
    return bool(
        payload.get("data", {})
        .get("productrevGetProductReviewList", {})
        .get("hasNext")
    )


async def get_reviews(
    product_id=None,
    url=None,
    max_result: int = 10,
    debug: bool = False,
    session=None,
) -> List[ProductReview]:
    """Fetch up to ``max_result`` customer reviews for one product.

    Args:
        product_id: Tokopedia product id.
        url: Product URL; resolved to an id once, up front, when ``product_id``
            is not given.
        max_result: Upper bound on returned reviews.
        debug: Log per-page progress at DEBUG level.
        session: Optional caller-owned ``AsyncSession`` for connection reuse.

    Returns:
        A list of :class:`ProductReview`. Empty when the product has no
        reviews or the request failed.

    Raises:
        ValueError: When neither ``product_id`` nor ``url`` is provided, or
            when the URL cannot be resolved to a product id.
    """
    if not product_id and not url:
        raise ValueError("get_reviews() requires either 'product_id' or 'url'.")

    if not product_id:
        product = await get_product(url=url, session=session)
        if not product or not product.product_id:
            raise ValueError(f"Could not resolve a product id from URL: {url}")
        product_id = product.product_id
    product_id = str(product_id)

    async def fetch_page(page: int):
        payload = {
            "query": _QUERY,
            "variables": {
                "productID": product_id,
                "page": page,
                "filterBy": "",
                "opt": "",
                "limit": PAGE_SIZE,
                "sortBy": "informative_score desc",
            },
        }
        response = await post_graphql(OPERATION, payload, session=session)
        if not response:
            return [], None

        reviews = parse_reviews(response)
        if debug:
            for review in reviews:
                logger.debug("%s - %s...", review.feedback_id, review.message.replace("\n", "")[:40])

        if not reviews or not has_next_page(response):
            return reviews, None
        return reviews, page + 1

    return await paginate(
        fetch_page,
        start_state=1,
        max_result=max_result,
        key=lambda review: review.feedback_id,
    )
