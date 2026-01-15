from typing import TypeVar, Callable, Awaitable, Literal, Generic, overload
from typing_extensions import TypedDict
import asyncio

from .result import Result, Ok, Err
from .error import UnhandledException

A = TypeVar("A")
E = TypeVar("E")


class RetryConfig(TypedDict, total=False):
    """Retry configuration for sync operations."""

    times: int


class RetryConfigAsync(TypedDict, total=False):
    """Retry configuration for async operations with delays."""

    times: int
    delay_ms: int
    backoff: Literal["constant", "linear", "exponential"]


class SafeConfig(TypedDict, total=False):
    """Configuration for safe()."""

    retry: RetryConfig


class SafeConfigAsync(TypedDict, total=False):
    """Configuration for safe_async()."""

    retry: RetryConfigAsync


class SafeOptions(TypedDict, Generic[A, E]):
    """Options for safe/safe_async with custom error mapping."""

    try_: Callable[[], A]
    catch: Callable[[Exception], E]


@overload
def safe(
    thunk: Callable[[], A],
    config: SafeConfig | None = None,
) -> Result[A, UnhandledException]: ...


@overload
def safe(
    thunk: SafeOptions[A, E],
    config: SafeConfig | None = None,
) -> Result[A, E]: ...


def safe(
    thunk: Callable[[], A] | SafeOptions[A, E],
    config: SafeConfig | None = None,
) -> Result[A, E] | Result[A, UnhandledException]:
    """
    Wraps a potentially throwing function into a Result.

    Supports two calling patterns:
    1. Simple thunk: `safe(lambda: risky_operation())`
    2. With custom error mapping: `safe({"try_": fn, "catch": mapper})`

    Parameters
    ----------
    thunk : Callable[[], A] | SafeOptions[A, E]
        Either a callable that may throw, or options with try_/catch.
    config : SafeConfig | None, default None
        Optional configuration with retry settings.

    Returns
    -------
    Result[A, UnhandledException] | Result[A, E]
        Ok with the value, or Err with UnhandledException or custom error.

    Examples
    --------
    >>> safe(lambda: int("42"))
    Ok(42)
    >>> safe(lambda: int("bad"))
    Err(UnhandledException(ValueError(...)))
    >>> safe(lambda: int("bad"), {"retry": {"times": 3}})
    Err(UnhandledException(ValueError(...)))  # After 3 retries
    >>> safe({"try_": lambda: int("bad"), "catch": lambda e: str(e)})
    Err("invalid literal for int()...")
    >>> def risky() -> float:
    ...     raise ValueError("Invalid input")
    >>> safe(risky)
    Err(UnhandledException(ValueError('Invalid input')))
    >>> safe({"try_": risky, "catch": lambda e: "Error: " + str(e)})
    Err('Error: Invalid input')
    """

    def execute() -> Result[A, E] | Result[A, UnhandledException]:
        if callable(thunk):
            try:
                return Ok(thunk())
            except Exception as e:
                return Err(UnhandledException(e))
        else:
            try:
                return Ok(thunk["try_"]())
            except Exception as e:
                return Err(thunk["catch"](e))

    retry_config = (config or {}).get("retry", {})
    times = retry_config.get("times", 0) if retry_config else 0

    result = execute()

    for _ in range(times):
        if result.is_ok():
            break
        result = execute()

    return result


@overload
async def safe_async(
    thunk: Callable[[], Awaitable[A]],
    config: SafeConfigAsync | None = None,
) -> Result[A, UnhandledException]: ...


@overload
async def safe_async(
    thunk: SafeOptions[Awaitable[A], E],
    config: SafeConfigAsync | None = None,
) -> Result[A, E]: ...


async def safe_async(
    thunk: Callable[[], Awaitable[A]] | SafeOptions[Awaitable[A], E],
    config: SafeConfigAsync | None = None,
) -> Result[A, E] | Result[A, UnhandledException]:
    """
    Wraps a potentially throwing async function into a Result.

    Supports two calling patterns:
    1. Simple thunk: `safe_async(lambda: fetch_data())`
    2. With custom error mapping: `safe_async({"try_": fn, "catch": mapper})`

    Parameters
    ----------
    thunk : Callable[[], Awaitable[A]] | SafeOptions[Awaitable[A], E]
        Either an async callable that may throw, or options with try_/catch.
    config : SafeConfigAsync | None, default None
        Optional configuration with retry settings (times, delay_ms, backoff).

    Returns
    -------
    Result[A, UnhandledException] | Result[A, E]
        Ok with the value, or Err with UnhandledException or custom error.

    Examples
    --------
    >>> async def risky_async() -> float:
    ...     raise ValueError("Invalid input")
    >>> await safe_async(risky_async)
    Err(UnhandledException(ValueError('Invalid input')))
    >>> async def fetch(url: str) -> str:
    ...     raise ConnectionError("Network error")
    >>> await safe_async(
    ...     lambda: fetch("https://api.example.com"),
    ...     {
    ...         "retry": {
    ...             "times": 3,
    ...             "delay_ms": 100,
    ...             "backoff": "exponential",  # or "linear" | "constant"
    ...         }
    ...     }
    ... )
    Err(UnhandledException(ConnectionError('Network error')))  # After retries
    """

    async def execute() -> Result[A, E] | Result[A, UnhandledException]:
        if callable(thunk):
            try:
                return Ok(await thunk())
            except Exception as e:
                return Err(UnhandledException(e))
        else:
            try:
                return Ok(await thunk["try_"]())
            except Exception as e:
                return Err(thunk["catch"](e))

    def get_delay(attempt: int) -> float:
        if not config:
            return 0
        retry_config = config.get("retry")
        if not retry_config:
            return 0
        delay_ms = retry_config.get("delay_ms", 0)
        backoff = retry_config.get("backoff", "constant")
        if backoff == "constant":
            return delay_ms / 1000
        elif backoff == "linear":
            return (delay_ms * (attempt + 1)) / 1000
        else:  # exponential
            return (delay_ms * (2**attempt)) / 1000

    retry_config = (config or {}).get("retry", {})
    times = retry_config.get("times", 0) if retry_config else 0

    result = await execute()

    for attempt in range(times):
        if result.is_ok():
            break
        delay = get_delay(attempt)
        if delay > 0:
            await asyncio.sleep(delay)
        result = await execute()

    return result
