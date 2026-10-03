"""Bounded-concurrency fan-out for enrichment.

``SearchResults.enrich_details`` and ``SearchResults.enrich_reviews`` used to
each repeat the same semaphore + ``asyncio.gather`` + swallow-errors block.
The policy — how wide to fan out, what to do with a failed item — now lives
here once, and failures are returned instead of printed.

The interface is deliberately small: give it items a ``fetch`` coroutine and
get back both the successes and a per-item error list. Tests inject a fake
``fetch``; production injects the real network call. Two adapters, so the
seam is real.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Awaitable, Callable, List, Sequence, Tuple, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")

# Kept modest on purpose: serverless runtimes give one invocation a small CPU
# slice, and Tokopedia throttles bursts. Override per call when needed.
DEFAULT_CONCURRENCY = 10


async def bounded_gather(
    items: Sequence[T],
    fetch: Callable[[T], Awaitable[None]],
    concurrency: int = DEFAULT_CONCURRENCY,
) -> List[Tuple[T, Exception]]:
    """Run ``fetch(item)`` for every item, at most ``concurrency`` at a time.

    Args:
        items: The work list.
        fetch: ``async (item) -> None``. Mutates the item in place; that is the
            enrichment contract, since ``ProductData`` objects are the payload.
        concurrency: Maximum in-flight calls. Values below 1 are clamped to 1.

    Returns:
        A list of ``(item, exception)`` pairs for the items that failed.
        An empty list means every item succeeded. Callers decide whether a
        partial failure is acceptable; nothing is printed and nothing is
        swallowed silently.
    """
    limit = max(1, int(concurrency))
    semaphore = asyncio.Semaphore(limit)
    failures: List[Tuple[T, Exception]] = []

    async def _run(item: T) -> None:
        async with semaphore:
            try:
                await fetch(item)
            except asyncio.CancelledError:
                # Never convert cancellation into a data error; the host is
                # shutting the invocation down.
                raise
            except Exception as exc:  # noqa: BLE001 - one bad item must not kill the batch
                failures.append((item, exc))

    if items:
        await asyncio.gather(*(_run(item) for item in items))

    return failures


def log_failures(failures: List[Tuple[object, Exception]], label: str, total: int = 0) -> None:
    """Emit one warning summarising a failed batch.

    Uniform failure reporting keeps the ``debug`` flag out of the hot path and
    out of the interface.
    """
    if not failures:
        return
    preview = ""
    for item, exc in failures[:3]:
        preview += f" {getattr(item, 'product_id', '?')}={exc!r};"
    logger.warning("%s: %d of %d failed.%s", label, len(failures), total or len(failures), preview)
