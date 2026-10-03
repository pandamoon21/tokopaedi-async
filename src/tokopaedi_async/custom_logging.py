"""Logging helpers.

This module intentionally does **not** configure logging on import. A library
that calls ``logging.basicConfig()`` or ``logging.setLoggerClass()`` rewrites
the host application's root logger, which is especially harmful on a
serverless platform: each cold start re-runs the import, and the side effect
lands in a process the library does not own.

Everything logs through ``logging.getLogger(__name__)``. Applications that
want the Tokopaedi-specific levels can opt in explicitly via
:func:`enable_custom_levels`.
"""

from __future__ import annotations

import logging

# Custom levels sit between DEBUG (10) and INFO (20) so they are shown when the
# app sets its level to DEBUG, but stay quiet under the INFO default.
SEARCH_LEVEL = 25
DETAIL_LEVEL = 26
REVIEWS_LEVEL = 27

_LEVELS_REGISTERED = False


def enable_custom_levels() -> None:
    """Register the SEARCH/DETAIL/REVIEW level names on the ``logging`` module.

    Idempotent and side-effect free until called. Applications that want these
    levels in their output call this once at startup; libraries and tests do
    not need to.
    """
    global _LEVELS_REGISTERED
    if _LEVELS_REGISTERED:
        return
    logging.addLevelName(SEARCH_LEVEL, "SEARCH")
    logging.addLevelName(DETAIL_LEVEL, "DETAIL")
    logging.addLevelName(REVIEWS_LEVEL, "REVIEW")
    _LEVELS_REGISTERED = True


def get_logger(name: str = "tokopaedi_async") -> logging.Logger:
    """Return the package logger.

    Kept for backwards compatibility with the previous ``setup_custom_logging()``
    call sites, but it performs no global configuration.
    """
    return logging.getLogger(name)
