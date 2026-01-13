from __future__ import annotations

from .result import (
    Err,
    Ok,
    Result,
    Matcher,
    map,
    map_err,
    tap,
    tap_async,
    unwrap,
    and_then,
    and_then_async,
    match,
)

from .safe import (
    safe,
    safe_async,
    UnhandledException,
    SafeConfig,
    SafeConfigAsync,
    SafeOptions,
    RetryConfig,
    RetryConfigAsync,
)

__all__ = [
    # Result types
    "Err",
    "Ok",
    "Result",
    "Matcher",
    # Result functions
    "map",
    "map_err",
    "tap",
    "tap_async",
    "unwrap",
    "and_then",
    "and_then_async",
    "match",
    # Safe functions
    "safe",
    "safe_async",
    "UnhandledException",
    "SafeConfig",
    "SafeConfigAsync",
    "SafeOptions",
    "RetryConfig",
    "RetryConfigAsync",
]
