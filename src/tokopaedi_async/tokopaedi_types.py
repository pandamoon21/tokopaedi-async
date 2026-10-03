from dataclasses import dataclass, field, asdict
from typing import List, Optional, Iterator


def shop_resolver(shop_tier):
    """Map a shop tier (id or badge image URL) to its display name.

    Accepts the numeric tier (``1``/``2``/``3``) or the badge URL the search
    API returns in its place. Unknown input resolves to ``None`` rather than
    silently claiming "Normal".
    """
    if shop_tier is None:
        return None

    try:
        tier = int(shop_tier)
    except (TypeError, ValueError):
        if isinstance(shop_tier, str):
            if 'PM%20Pro%20Small.png' in shop_tier:
                tier = 3
            elif 'official_store_badge' in shop_tier:
                tier = 2
            else:
                return None
        else:
            return None

    return {1: 'Normal', 2: 'Mall', 3: 'Power Shop'}.get(tier)

@dataclass
class ProductReview:
    feedback_id: int
    variant_name: Optional[str]
    message: str
    rating: float
    review_age: str
    user_full_name: str
    user_url: str
    response_message: Optional[str]
    response_created_text: Optional[str]
    images: List[str] = field(default_factory=list)
    videos: List[str] = field(default_factory=list)
    likes: int = 0

    def json(self):
        return asdict(self)

@dataclass
class TokopaediShop:
    shop_id: int
    name: str
    city: Optional[str]
    url: str
    shop_type: Optional[str] = None

@dataclass
class ProductMedia:
    original: str
    thumbnail: str
    max_res: str

@dataclass
class ProductOption:
    option_id: int
    option_name: str
    option_child: List[str]

@dataclass
class ProductVariant:
    option_ids: List[int]
    option_name: str
    option_url: str
    price: int
    price_string: str
    discount: str
    image_url: Optional[str] = None
    stock: Optional[int] = None

@dataclass
class ProductData:
    product_id: int
    product_sku: str
    product_name: str
    url: str
    main_image: Optional[str] = None
    status: Optional[str] = None
    description: Optional[str] = None
    price: Optional[int] = None
    price_text: Optional[str] = None
    price_original: Optional[str] = None
    discount_percentage: Optional[str] = None
    weight: Optional[int] = None
    weight_unit: Optional[str] = None
    product_media: List[ProductMedia] = field(default_factory=list)
    sold_count: Optional[int] = None
    rating: Optional[float] = None
    review_count: Optional[int] = None
    discussion_count: Optional[int] = None
    total_stock: Optional[int] = None
    etalase: Optional[str] = None
    etalase_url: Optional[str] = None
    category: str = None
    sub_category: Optional[List[str]] = None
    product_option: Optional[List[ProductOption]] = None
    variants: Optional[List[ProductVariant]] = None
    shop: TokopaediShop = None
    reviews: Optional[List[ProductReview]] = None
    has_detail: bool = False
    has_reviews: bool = False

    # Fields owned by a PDP fetch. ``enrich_details`` merges only these, so a
    # search result's review fields can never be clobbered by a product fetch.
    DETAIL_FIELDS = (
        "product_sku",
        "product_name",
        "url",
        "main_image",
        "status",
        "description",
        "price",
        "price_text",
        "price_original",
        "discount_percentage",
        "weight",
        "weight_unit",
        "product_media",
        "sold_count",
        "rating",
        "review_count",
        "discussion_count",
        "total_stock",
        "etalase",
        "etalase_url",
        "category",
        "sub_category",
        "product_option",
        "variants",
        "shop",
    )

    def merge_details(self, detail: "ProductData") -> "ProductData":
        """Copy the PDP-owned fields from ``detail`` onto this product.

        Precedence is explicit and one-directional: the detail fetch wins for
        :attr:`DETAIL_FIELDS`, everything else on this object is preserved.
        Replaces the previous reflective copy of *every* non-``None`` field,
        which silently overwrote review data and changed behavior whenever a
        dataclass field was added.
        """
        for field_name in self.DETAIL_FIELDS:
            value = getattr(detail, field_name, None)
            if value is not None:
                setattr(self, field_name, value)
        return self

    def json(self):
        return asdict(self)

    async def enrich_details(self, debug: bool = False, session=None):
        """Fetch this product's full PDP data and merge it in.

        Idempotent: a second call is a no-op once ``has_detail`` is set.
        """
        if self.has_detail:
            return self
        from .get_product import get_product

        enriched = await get_product(product_id=self.product_id, debug=debug, session=session)
        if enriched is not None:
            self.merge_details(enriched)
            self.has_detail = True
        return self

    async def enrich_reviews(self, max_result=None, debug: bool = False, session=None):
        """Fetch this product's reviews and attach them.

        Idempotent: a second call is a no-op once ``has_reviews`` is set.
        ``has_reviews`` is only set when the fetch actually returns.
        """
        if self.has_reviews:
            return self
        from .get_reviews import get_reviews

        self.reviews = await get_reviews(
            product_id=self.product_id,
            debug=debug,
            max_result=max_result or 10,
            session=session,
        )
        self.has_reviews = True
        return self


class SearchResults:
    def __init__(self, items: List[ProductData] = None):
        self.items = items or []

    async def enrich_details(self, debug=False, concurrency=10, session=None):
        """Populate PDP details for every product, bounded by ``concurrency``.

        Returns a list of ``(item, exception)`` pairs for the products that
        failed. An empty list means full success; a partial failure leaves the
        successful products enriched.
        """
        from .concurrency import bounded_gather, log_failures

        failures = await bounded_gather(
            self.items,
            lambda item: item.enrich_details(debug=debug, session=session),
            concurrency=concurrency,
        )
        log_failures(failures, "enrich_details", total=len(self.items))
        return failures

    async def enrich_reviews(self, max_result=10, debug=False, concurrency=10, session=None):
        """Populate reviews for every product, bounded by ``concurrency``.

        Returns a list of ``(item, exception)`` pairs for the products that
        failed, mirroring :meth:`enrich_details`.
        """
        from .concurrency import bounded_gather, log_failures

        failures = await bounded_gather(
            self.items,
            lambda item: item.enrich_reviews(max_result=max_result, debug=debug, session=session),
            concurrency=concurrency,
        )
        log_failures(failures, "enrich_reviews", total=len(self.items))
        return failures

    def append(self, item: ProductData) -> None:
        self.items.append(item)

    def extend(self, more: List[ProductData]) -> None:
        self.items.extend(more)

    def __getitem__(self, index) -> ProductData:
        return self.items[index]

    def __iter__(self) -> Iterator[ProductData]:
        return iter(self.items)

    def __len__(self) -> int:
        return len(self.items)

    def json(self) -> List[dict]:
        return [item.json() for item in self.items]

    def __repr__(self) -> str:
        return f"<SearchResults total={len(self.items)}>"

    def __add__(self, other: "SearchResults") -> "SearchResults":
        if not isinstance(other, SearchResults):
            return NotImplemented
        return SearchResults(self.items + other.items)

    def __iadd__(self, other: "SearchResults") -> "SearchResults":
        if not isinstance(other, SearchResults):
            return NotImplemented
        self.extend(other.items)
        return self
    