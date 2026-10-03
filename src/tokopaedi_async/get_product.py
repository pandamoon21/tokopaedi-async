"""Product detail (PDP) scraping.

Two things live here and they are deliberately separate:

* :func:`parse_product` — pure. Takes the decoded GraphQL JSON and returns a
  :class:`~tokopaedi_async.tokopaedi_types.ProductData`. This is the seam tests
  use; no network is involved.
* :func:`get_product` — the network-bound interface. Fetches the JSON via
  :mod:`tokopaedi_async.transport` and hands it to the parser.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, Optional

from .tokopaedi_types import (
    ProductData,
    ProductMedia,
    ProductOption,
    ProductVariant,
    TokopaediShop,
    shop_resolver,
)
from .transport import post_graphql

logger = logging.getLogger(__name__)

OPERATION = "ProductDetails/getPDPLayout"

# The full PDP layout query. Long by nature: the endpoint returns one card per
# component and the query must name every card it wants back.
_QUERY = """query PDP_getPDPLayout($productId: String, $shopDomain: String, $productKey: String, $apiVersion: Float, $whID: String, $layoutID: String, $userLocation: pdpUserLocation, $extParam: String, $tokonow: pdpTokoNow) {
pdpGetLayout(productID: $productId, shopDomain: $shopDomain, productKey: $productKey, apiVersion: $apiVersion, whID: $whID, layoutID: $layoutID, userLocation: $userLocation, extParam: $extParam, tokonow: $tokonow) {
requestID
name
pdpSession
basicInfo {
productID
initialVariantOptionID
category {
id
name
title
breadcrumbURL
isAdult
isKyc
detail {
id
name
breadcrumbURL
}
ttsID
ttsDetail {
id
name
breadcrumbURL
}
}
menu {
id
name
url
}
shopID
shopName
alias
minOrder
maxOrder
url
catalogID
needPrescription
weight
weightUnit
status
txStats {
transactionReject
transactionSuccess
countSold
itemSoldFmt
}
stats {
rating
countTalk
countView
countReview
}
defaultOngkirEstimation
isTokoNow
totalStockFmt
isGiftable
defaultMediaURL
shopMultilocation {
cityName
}
isBlacklisted
blacklistMessage {
title
description
button
}
weightWording
ttsPID
ttsSKUID
ttsShopID
}
additionalData {
fomoSocialProofs {
name
text
icons
typeIcon
backgroundColor
position
}
}
components {
name
type
kind
data {
... on pdpDataComponentSocialProofV2 {
socialProofContent {
socialProofType
socialProofID
title
subtitle
icon
applink {
appLink
}
bgColor
chevronColor
showChevron
hasSeparator
}
}
... on pdpDataProductMedia {
media {
type
URLOriginal
URLThumbnail
description
videoURLIOS
isAutoplay
index
variantOptionID
URLMaxRes
}
recommendation{
lightIcon
darkIcon
iconText
bottomsheetTitle
recommendation
}
videos {
source
url
}
containerType
liveIndicator {
isLive
channelID
mediaURL
applink
}
showJumpToVideo
}
... on pdpDataProductContent {
name
price {
value
currency
lastUpdateUnix
priceFmt
slashPriceFmt
discPercentage
currencyFmt
valueFmt
}
campaign {
campaignID
campaignType
campaignTypeName
percentageAmount
originalPrice
discountedPrice
originalStock
stock
stockSoldPercentage
endDateUnix
isActive
hideGimmick
isUsingOvo
campaignIdentifier
background
paymentInfoWording
productID
campaignLogo
showStockBar
}
thematicCampaign {
productID
campaignName
background
icon
campaignLogo
superGraphicURL
}
stock {
useStock
value
stockWording
}
variant {
isVariant
}
wholesale {
minQty
price {
value
currency
lastUpdateUnix
}
}
isFreeOngkir {
isActive
imageURL
}
preorder {
duration
timeUnit
isActive
preorderInDays
}
isCashback {
percentage
}
isTradeIn
isOS
isPowerMerchant
isWishlist
isCOD
parentName
isShowPrice
labelIcons {
iconURL
label
}
}
... on pdpDataProductInfo {
row
content {
title
subtitle
applink
}
}
... on pdpDataInfo {
title
applink
isApplink
icon
lightIcon
darkIcon
content {
icon
text
}
separator
}
... on pdpDataProductVariant {
parentID
defaultChild
sizeChart
maxFinalPrice
componentType
landingSubText
socialProof {
bgColor
contents {
name
content
iconURL
}
}
variants {
productVariantID
variantID
name
identifier
option {
productVariantOptionID
variantUnitValueID
value
hex
picture {
url
url100
}
}
}
children {
productID
price
priceFmt
slashPriceFmt
discPercentage
sku
optionID
productName
productURL
picture {
url
url100
}
stock {
stock
isBuyable
stockWording
stockWordingHTML
minimumOrder
maximumOrder
stockFmt
stockCopy
}
isCOD
isWishlist
campaignInfo {
campaignID
campaignType
campaignTypeName
discountPercentage
originalPrice
discountPrice
stock
stockSoldPercentage
endDateUnix
appLinks
isActive
hideGimmick
isUsingOvo
minOrder
campaignIdentifier
background
paymentInfoWording
campaignLogo
showStockBar
}
thematicCampaign {
campaignName
icon
background
productID
campaignLogo
superGraphicURL
}
subText
promo {
value
iconURL
productID
promoPriceFmt
subtitle
applink
color
background
promoType
superGraphicURL
priceAdditionalFmt
separatorColor
bottomsheetParam
promoCodes {
promoID
promoCode
promoCodeType
}
}
currencyFmt
valuePriceFmt
componentPriceType
isTopSold
labelIcons {
iconURL
label
}
ttsPID
ttsSKUID
}
}
... on pdpDataCustomInfo {
icon
title
isApplink
applink
separator
description
label {
value
color
}
lightIcon
darkIcon
}
... on pdpDataComponentReviewV2 {
mostHelpfulReviewParam {
limit
}
}
... on pdpDataProductDetail {
title
content {
type
key
extParam
action
title
subtitle
applink
showAtFront
showAtBottomsheet
infoLink
icon
}
catalogBottomsheet {
actionTitle
bottomSheetTitle
param
}
bottomsheet {
actionTitle
bottomSheetTitle
param
}
}
... on pdpDataOneLiner {
productID
oneLinerContent
linkText
applink
separator
isVisible
color
icon
eduLink {
appLink
}
}
... on pdpDataCategoryCarousel {
linkText
titleCarousel
applink
list {
categoryID
icon
title
isApplink
applink
}
}
... on pdpDataBundleComponentInfo {
title
widgetType
productID
whID
}
... on pdpDataDynamicOneLiner {
name
applink
separator
icon
status
chevronPos
text
bgColor
chevronColor
padding {
t
b
}
imageSize {
w
h
}
}
... on pdpDataComponentDynamicOneLinerVariant {
name
applink
separator
icon
status
chevronPos
text
bgColor
chevronColor
padding {
t
b
}
imageSize {
w
h
}
}
... on pdpDataCustomInfoTitle {
title
status
componentName
}
... on pdpDataProductDetailMediaComponent {
title
description
contentMedia {
url
ratio
type
}
show
ctaText
}
... on pdpDataOnGoingCampaign {
campaign {
campaignID
campaignType
campaignTypeName
percentageAmount
originalPrice
discountedPrice
originalStock
stock
stockSoldPercentage
endDateUnix
isActive
hideGimmick
isUsingOvo
campaignIdentifier
background
paymentInfoWording
productID
campaignLogo
showStockBar
}
thematicCampaign {
productID
campaignName
background
icon
campaignLogo
superGraphicURL
}
}
... on pdpDataProductListComponent {
thematicID
queryParam
}
... on pdpDataComponentPromoPrice {
price {
value
currency
lastUpdateUnix
priceFmt
slashPriceFmt
discPercentage
currencyFmt
valueFmt
}
promo {
value
iconURL
productID
promoPriceFmt
subtitle
applink
color
background
promoType
superGraphicURL
priceAdditionalFmt
separatorColor
bottomsheetParam
promoCodes {
promoID
promoCode
promoCodeType
}
}
componentPriceType
}
... on pdpDataComponentSDUIDivKit {
template
}
... on pdpDataComponentShipmentV4 {
data {
productID
warehouse_info {
warehouse_id
is_fulfillment
district_id
postal_code
geolocation
city_name
ttsWarehouseID
}
useBOVoucher
isCOD
metadata
}
}
... on pdpDataComponentShipmentV5 {
data {
productID
warehouse_info {
warehouse_id
is_fulfillment
district_id
postal_code
geolocation
city_name
ttsWarehouseID
}
useBOVoucher
isCOD
metadata
}
}
...on pdpDataAffordabilityGroupLabel {
affordabilityData{
productID
productVouchers {
identifier
type
text
backgroundColor
}
showChevron
chevronColor
appliedVoucherTypeIDs
}
}
}
}
}
}"""


def _find_component(components: list, name: str) -> list:
    """Return the ``data`` list of the named PDP component, or ``[]``."""
    for component in components:
        if component.get("name") == name:
            return component.get("data", [])
    return []


def _first(value: list) -> Dict[str, Any]:
    """Unwrap the one-element lists PDP components arrive in."""
    return value[0] if value else {}


def _resolve_shop_tier(pdp: Dict[str, Any]):
    """Read the shop tier out of the serialised ``pdpSession`` field.

    ``pdpSession`` is a JSON string embedded in the response; it can be absent
    or malformed, in which case the tier is unknown and resolved as ``None``.
    """
    raw_session = pdp.get("pdpSession")
    if not raw_session:
        return None
    try:
        return json.loads(raw_session).get("stier")
    except (TypeError, ValueError):
        return None


def parse_product(json_data: Dict[str, Any]) -> Optional[ProductData]:
    """Turn a decoded ``getPDPLayout`` response into a :class:`ProductData`.

    Pure function: no network, no globals. Returns ``None`` when the response
    does not carry a PDP layout, so callers can distinguish "no such product"
    from "request failed".
    """
    pdp = json_data.get("data", {}).get("pdpGetLayout")
    if not pdp:
        return None

    components = pdp.get("components", [])
    basic_info = pdp.get("basicInfo", {})

    product_content = _first(_find_component(components, "product_content"))
    product_media_raw = _first(_find_component(components, "product_media")).get("media", [])

    product_url = basic_info.get("url", "")

    product_media = [
        ProductMedia(
            original=media.get("URLOriginal", ""),
            thumbnail=media.get("URLThumbnail", ""),
            max_res=media.get("URLMaxRes", ""),
        )
        for media in product_media_raw
    ]

    product_option = []
    variants = []
    mini_variant = _first(_find_component(components, "mini_variant_options"))
    if mini_variant:
        for option in mini_variant.get("variants", []):
            product_option.append(
                ProductOption(
                    option_id=int(option.get("productVariantID", 0) or 0),
                    option_name=option.get("name", ""),
                    option_child=[child.get("value", "") for child in option.get("option", [])],
                )
            )

        for child in mini_variant.get("children", []):
            variants.append(
                ProductVariant(
                    option_ids=child.get("optionID", []),
                    option_name=child.get("productName", ""),
                    option_url=child.get("productURL", ""),
                    price=child.get("price", 0),
                    price_string=child.get("priceFmt", ""),
                    discount=child.get("discPercentage", ""),
                    image_url=child.get("picture", {}).get("url", ""),
                    stock=child.get("stock", {}).get("stock", None),
                )
            )

    description = None
    for line in _find_component(components, "product_detail"):
        if isinstance(line, dict) and line.get("key") == "deskripsi":
            description = line.get("subtitle", "")
            break
    if description is None:
        detail_content = _first(_find_component(components, "product_detail")).get("content")
        if isinstance(detail_content, list):
            for line in detail_content:
                if isinstance(line, dict) and line.get("key") == "deskripsi":
                    description = line.get("subtitle", "")
                    break

    price = product_content.get("price", {})
    category = basic_info.get("category", {})

    return ProductData(
        product_id=basic_info.get("productID"),
        product_sku=basic_info.get("ttsSKUID"),
        product_name=product_content.get("name", ""),
        url=product_url,
        main_image=basic_info.get("defaultMediaURL"),
        status=basic_info.get("status", ""),
        description=description,
        price=price.get("value", 0),
        price_text=price.get("priceFmt", ""),
        price_original=price.get("slashPriceFmt", ""),
        discount_percentage=price.get("discPercentage", ""),
        weight=int(basic_info.get("weight", 0) or 0),
        weight_unit=basic_info.get("weightUnit", ""),
        product_media=product_media,
        sold_count=int(basic_info.get("txStats", {}).get("countSold", 0) or 0),
        rating=float(basic_info.get("stats", {}).get("rating", 0) or 0),
        review_count=int(basic_info.get("stats", {}).get("countReview", 0) or 0),
        discussion_count=int(basic_info.get("stats", {}).get("countTalk", 0) or 0),
        total_stock=int(str(basic_info.get("totalStockFmt", "0")).replace(".", "") or 0),
        etalase=basic_info.get("menu", {}).get("name", ""),
        etalase_url=basic_info.get("menu", {}).get("url", ""),
        category=category.get("name", ""),
        sub_category=[detail.get("name", "") for detail in category.get("detail", [])],
        product_option=product_option,
        variants=variants,
        shop=TokopaediShop(
            shop_id=int(basic_info.get("shopID", 0) or 0),
            name=basic_info.get("shopName", ""),
            city=basic_info.get("shopMultilocation", {}).get("cityName", ""),
            url="/".join(product_url.split("/")[:-1]),
            shop_type=shop_resolver(_resolve_shop_tier(pdp)),
        ),
    )


def parse_tokped_url(url: str):
    """Split a product URL into ``(shop_domain, product_key)``.

    Returns ``("", "")`` for anything that is not a Tokopedia product URL.
    """
    try:
        path = url.split("?")[0].split("tokopedia.com/")[1].split("/")
        shop_id = path[0] if len(path) > 0 else ""
        product_key = path[1] if len(path) > 1 else ""
        return shop_id, product_key
    except (IndexError, AttributeError):
        return "", ""


async def get_product(product_id=None, url=None, debug=False, session=None) -> Optional[ProductData]:
    """Fetch full details for one product.

    Args:
        product_id: Tokopedia product id. Takes precedence when both are given.
        url: Product URL; parsed into shop domain + product key.
        debug: Log the resolved product name at DEBUG level.
        session: Optional caller-owned ``AsyncSession``. Omit on serverless so
            the request owns and closes its own connection.

    Returns:
        A :class:`ProductData`, or ``None`` when the URL cannot be parsed or
        the request failed.
    """
    if not product_id and not url:
        raise ValueError("get_product() requires either 'product_id' or 'url'.")

    if url and not product_id:
        shop_id, product_key = parse_tokped_url(url)
        if not shop_id or not product_key:
            logger.warning("Could not parse Tokopedia URL: %s", url)
            return None
    else:
        product_id = str(product_id)
        shop_id, product_key = None, None

    payload = {
        "variables": {
            "apiVersion": 1,
            "userLocation": {
                "addressID": "",
                "addressName": "",
                "receiverName": "",
                "postalCode": "",
                "districtID": "",
                "cityID": "",
                "latlon": "",
            },
            "tokonow": {"shopID": "0", "warehouses": [], "whID": "0", "serviceType": "ooc"},
            "extParam": "",
            "productId": product_id or "",
            "shopDomain": shop_id if url else "",
            "productKey": product_key if url else "",
            "whID": "",
            "layoutID": "",
        },
        "query": _QUERY,
    }

    json_data = await post_graphql(OPERATION, payload, session=session)
    if not json_data:
        return None

    product_data = parse_product(json_data)
    if product_data and debug:
        logger.debug("%s - %s...", product_data.product_id, (product_data.product_name or "")[:40])
    return product_data
