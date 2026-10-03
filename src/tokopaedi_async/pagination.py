"""Bounded pagination over a cursor-following endpoint.

Both :func:`tokopaedi_async.search.search` and
:func:`tokopaedi_async.get_reviews.get_reviews` walk a list in pages. Before
this module they each expressed that walk as self-recursion, which put the
loop state (``result_count``, ``base_param``, ``page``) into the public
interface and capped the scrape at Python's recursion limit.

One loop, one accumulator, one place to add backoff.
"""

from __future__ import annotations

import logging
from typing import Any, Awaitable, Callable, List, Optional, Tuple

logger = logging.getLogger(__name__)

# page_fetcher(state) -> (items, next_state | None)
PageFetcher = Callable[[Any], Awaitable[Tuple[List[Any], Optional[Any]]]]


async def paginate(
    fetch_page: PageFetcher,
    start_state: Any,
    max_result: int,
    key: Optional[Callable[[Any], Any]] = None,
    max_pages: int = 100,
) -> List[Any]:
    """Walk pages until ``max_result`` items are collected or the cursor ends.

    Args:
        fetch_page: ``async (state) -> (items, next_state)``. Returning
            ``None`` for ``next_state`` ends the walk.
        start_state: State for the first page (a page number, or a cursor
            string such as Tokopedia's ``additionalParams``).
        max_result: Stop once at least this many items have been collected.
        key: Optional identity function used to drop duplicates across pages.
            Deduplication happens as pages arrive, not at the end, so a
            duplicate never inflates the running count.
        max_pages: Hard safety ceiling. Prevents an endpoint that always
            returns the same cursor from looping forever.

    Returns:
        The collected items, in page order, deduplicated when ``key`` is given.
    """
    collected: List[Any] = []
    seen = set()
    state = start_state
    pages = 0

    while state is not None and pages < max_pages:
        pages += 1
        items, next_state = await fetch_page(state)

        for item in items or []:
            if key is not None:
                marker = key(item)
                if marker in seen:
                    continue
                seen.add(marker)
            collected.append(item)

        if not items:
            # An empty page means the walk is over, regardless of the cursor.
            break
        if len(collected) >= max_result:
            break

        if next_state is None or next_state == state:
            break
        state = next_state

    if pages >= max_pages:
        logger.warning("paginate() hit max_pages=%s; results may be truncated", max_pages)

    return collected[:max_result]
