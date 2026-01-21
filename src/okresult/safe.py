from typing import (
    TypeVar,
    Callable,
    Awaitable,
    Literal,
    Generic,
    overload,
    TypeAlias,
    cast,
)
from typing_extensions import TypedDict
import asyncio

from .result import Result, Ok, Err, try_or_panic
from .error import UnhandledException, panic

A = TypeVar("A")
E = TypeVar("E")
ErrT = TypeVar("ErrT", default=UnhandledException)

# Alias for the retry predicate. Callers supply a single-arg predicate for their
# concrete error type (e.g., Callable[[MyError], bool]); helpers like
# retry_config(_async) infer that type from the predicate.
ShouldRetryCallable: TypeAlias = Callable[[ErrT], bool]


class RetryConfig(TypedDict, Generic[ErrT], total=False):
    """Configuration for retry behavior in safe.

    Attributes:
        times: Number of retry attempts.
        should_retry: Predicate to decide if an error should trigger a retry.
            Defaults to always retry.
    """

    times: int
    should_retry: ShouldRetryCallable[ErrT]


class RetryConfigAsync(TypedDict, Generic[ErrT], total=False):
    """Configuration for retry behavior in safe_async.

    Attributes:
        times: Number of retry attempts.
        delay_ms: Delay in milliseconds between retries.
        backoff: Backoff strategy (constant, linear, or exponential).
        should_retry: Predicate to decide if an error should trigger a retry.
            Defaults to always retry.
    """

    times: int
    delay_ms: int
    backoff: Literal["constant", "linear", "exponential"]
    should_retry: ShouldRetryCallable[ErrT]


class SafeConfig(TypedDict, Generic[ErrT], total=False):
    """Configuration for safe execution.

    Attributes:
        retry: Retry configuration.
    """

    retry: RetryConfig[ErrT]


class SafeConfigAsync(TypedDict, Generic[ErrT], total=False):
    """Configuration for safe async execution.

    Attributes:
        retry: Retry configuration.
    """

    retry: RetryConfigAsync[ErrT]


def retry_config(
    *, times: int, should_retry: ShouldRetryCallable[E] | None = None
) -> SafeConfig[E]:
    """Helper to build a typed retry config for safe.

    The type of ``should_retry`` drives the error type ``E`` so callers can
    avoid annotating the whole config explicitly.
    """

    cfg: RetryConfig[E] = {"times": times}
    if should_retry is not None:
        cfg["should_retry"] = should_retry
    return {"retry": cfg}


def retry_config_async(
    *,
    times: int,
    delay_ms: int = 0,
    backoff: Literal["constant", "linear", "exponential"] = "constant",
    should_retry: ShouldRetryCallable[E] | None = None,
) -> SafeConfigAsync[E]:
    """Helper to build a typed retry config for safe_async.

    The type of ``should_retry`` drives the error type ``E`` so callers can
    avoid annotating the whole config explicitly.
    """

    cfg: RetryConfigAsync[E] = {
        "times": times,
        "delay_ms": delay_ms,
        "backoff": backoff,
    }
    if should_retry is not None:
        cfg["should_retry"] = should_retry
    return {"retry": cfg}


class SafeOptions(TypedDict, Generic[A, E]):
    """Options for safe execution with custom error handling.

    Attributes:
        try_: Function to execute.
        catch: Function to transform caught exceptions.
    """

    try_: Callable[[], A]
    catch: Callable[[Exception], E]


@overload
def safe(
    thunk: Callable[[], A],
    config: SafeConfig[UnhandledException] | None = None,
) -> Result[A, UnhandledException]: ...


@overload
def safe(
    thunk: SafeOptions[A, E],
    config: SafeConfig[E] | None = None,
) -> Result[A, E]: ...


def safe(
    thunk: Callable[[], A] | SafeOptions[A, E],
    config: SafeConfig[E] | None = None,
) -> Result[A, E | UnhandledException]:
    """Executes function safely, wrapping result/error in Result.

    Args:
        thunk: Function to execute or options dict with try_ and catch.
        config: Optional retry configuration.

    Returns:
        Result containing value or error.

    Raises:
        Panic: If catch handler throws.

    Example:
        >>> safe(lambda: 1 / 0)
        Err(UnhandledException(...))
        >>> safe({"try_": lambda: parse(x), "catch": lambda e: "error"})
        Err("error")
    """

    def execute() -> Result[A, E | UnhandledException]:
        if callable(thunk):
            try:
                return Ok(thunk())
            except Exception as e:
                return Err(UnhandledException(e))
        else:
            try:
                return Ok(thunk["try_"]())
            except Exception as original_cause:
                # If the user's catch handler throws, it's a defect — Panic
                try:
                    return Err(thunk["catch"](original_cause))
                except Exception as catch_handler_error:
                    panic("Result.safe catch handler threw", catch_handler_error)

    retry_config: RetryConfig[E] | None = (
        config["retry"] if config is not None and "retry" in config else None
    )
    times: int = (
        retry_config["times"] if retry_config and "times" in retry_config else 0
    )

    def _always_retry(_: E) -> bool:
        return True

    should_retry_fn: ShouldRetryCallable[E] | None = (
        retry_config["should_retry"]
        if retry_config and "should_retry" in retry_config
        else None
    )
    should_retry: ShouldRetryCallable[E] = should_retry_fn or _always_retry

    result = execute()

    for _ in range(times):
        if result.is_ok():
            break
        error = result.unwrap_err()
        should_continue = try_or_panic(
            lambda: should_retry(cast(E, error)), "should_retry predicate threw"
        )
        if not should_continue:
            break
        result = execute()

    return result


@overload
async def safe_async(
    thunk: Callable[[], Awaitable[A]],
    config: SafeConfigAsync[UnhandledException] | None = None,
) -> Result[A, UnhandledException]: ...


@overload
async def safe_async(
    thunk: SafeOptions[Awaitable[A], E],
    config: SafeConfigAsync[E] | None = None,
) -> Result[A, E]: ...


async def safe_async(
    thunk: Callable[[], Awaitable[A]] | SafeOptions[Awaitable[A], E],
    config: SafeConfigAsync[E] | None = None,
) -> Result[A, E | UnhandledException]:
    """Executes async function safely, wrapping result/error in Result.

    Supports retry with configurable delay and backoff.

    Args:
        thunk: Async function to execute or options dict with try_ and catch.
        config: Optional retry configuration with delay and backoff.

    Returns:
        Result containing value or error.

    Raises:
        Panic: If catch handler throws.

    Example:
        >>> await safe_async(lambda: fetch(url))
        Ok(...)
        >>> await safe_async(
        ...     lambda: fetch(url),
        ...     {"retry": {"times": 3, "delay_ms": 100, "backoff": "exponential"}}
        ... )
    """

    async def execute() -> Result[A, E | UnhandledException]:
        if callable(thunk):
            try:
                return Ok(await thunk())
            except Exception as e:
                return Err(UnhandledException(e))
        else:
            try:
                return Ok(await thunk["try_"]())
            except Exception as original_cause:
                # If the user's catch handler throws, it's a defect — Panic
                try:
                    return Err(thunk["catch"](original_cause))
                except Exception as catch_handler_error:
                    panic("Result.safe_async catch handler threw", catch_handler_error)

    def get_delay(attempt: int, retry_config: RetryConfigAsync[E] | None) -> float:
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

    retry_config: RetryConfigAsync[E] | None = (
        config["retry"] if config is not None and "retry" in config else None
    )
    times: int = (
        retry_config["times"] if retry_config and "times" in retry_config else 0
    )

    def _always_retry(_: E) -> bool:
        return True

    should_retry_fn: ShouldRetryCallable[E] | None = (
        retry_config["should_retry"]
        if retry_config and "should_retry" in retry_config
        else None
    )
    should_retry: ShouldRetryCallable[E] = should_retry_fn or _always_retry

    result = await execute()

    for attempt in range(times):
        if result.is_ok():
            break
        error = result.unwrap_err()
        should_continue = try_or_panic(
            lambda: should_retry(cast(E, error)), "should_retry predicate threw"
        )
        if not should_continue:
            break
        delay = get_delay(attempt, retry_config)
        if delay > 0:
            await asyncio.sleep(delay)
        result = await execute()

    return result
