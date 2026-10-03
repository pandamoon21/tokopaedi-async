"""Minimal ASGI service wrapping tokopaedi-async.

Runs unchanged on a serverless platform (Vercel Python runtime, AWS Lambda
behind a function URL, Google Cloud Run) and locally via uvicorn:

    pip install fastapi uvicorn
    uvicorn examples.serverless_app:app --reload
    curl "http://127.0.0.1:8000/search?q=zenbook&limit=5"

Serverless notes
----------------
* Nothing heavy happens at import time. ``tokopaedi_async`` has no import-time
  side effects, so a cold start is just an import.
* Every request owns and closes its own HTTP session (the default when no
  ``session`` is passed). On a serverless platform you cannot rely on a
  module-level session surviving between invocations — the worker may be
  frozen or recycled — so per-request sessions are the correct default.
* ``concurrency`` is lowered to keep a single invocation inside its CPU and
  rate budgets. Raise it when running on a dedicated worker.
* ``max_result`` and ``reviews`` are clamped so one caller cannot ask for
  10 000 products and blow the function's time limit.
"""

from __future__ import annotations

import logging

from fastapi import FastAPI, HTTPException, Query

import tokopaedi_async as tokopaedi

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="tokopaedi-async", version=tokopaedi.__version__)

# One invocation's budget stays small on purpose.
MAX_PRODUCTS = 40
MAX_REVIEWS = 20
CONCURRENCY = 8


@app.get("/health")
async def health() -> dict:
    """Cheap liveness probe that does not touch the network."""
    return {"status": "ok", "version": tokopaedi.__version__}


@app.get("/search")
async def search_products(
    q: str = Query(..., min_length=1, description="Search keyword"),
    limit: int = Query(10, ge=1, le=MAX_PRODUCTS),
    reviews: int = Query(0, ge=0, le=MAX_REVIEWS, description="Reviews per product"),
    min_rating: float | None = Query(None, ge=0.0, le=5.0),
    min_price: int | None = Query(None, ge=0),
    max_price: int | None = Query(None, ge=0),
) -> dict:
    """Search, enrich, and return plain JSON.

    One request = one bounded scrape. No shared mutable state, so the function
    scales horizontally without coordination.
    """
    filters = tokopaedi.SearchFilters(rt=min_rating, pmin=min_price, pmax=max_price)

    try:
        results = await tokopaedi.browse(
            q,
            max_result=limit,
            filters=filters,
            reviews_per_product=reviews,
            concurrency=CONCURRENCY,
        )
    except Exception as exc:  # noqa: BLE001 - surface a clean 502 to the caller
        logger.exception("scrape failed for %r", q)
        raise HTTPException(status_code=502, detail=f"scrape failed: {exc}") from exc

    return {"query": q, "count": len(results), "products": results.json()}


# Vercel's Python runtime looks for a module-level ASGI ``app``; the same
# object works for uvicorn, AWS Lambda (via Mangum), and Cloud Run.
#
# To deploy on Vercel, point a vercel.json at this file:
#
#   {
#     "builds": [{"src": "examples/serverless_app.py", "use": "@vercel/python"}],
#     "routes": [{"src": "/(.*)", "dest": "examples/serverless_app.py"}]
#   }
