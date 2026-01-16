from typing import TypeVar, Callable, Awaitable, Literal, Generic, overload
from typing_extensions import TypedDict
import asyncio

from .result import Result, Ok, Err
from .error import UnhandledException, panic

A = TypeVar("A")
E = TypeVar("E")


class RetryConfig(TypedDict, total=False):
    times: int


class RetryConfigAsync(TypedDict, total=False):
    times: int
    delay_ms: int
    backoff: Literal["constant", "linear", "exponential"]


class SafeConfig(TypedDict, total=False):
    retry: RetryConfig


class SafeConfigAsync(TypedDict, total=False):
    retry: RetryConfigAsync


class SafeOptions(TypedDict, Generic[A, E]):
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
    def execute() -> Result[A, E] | Result[A, UnhandledException]:
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
    async def execute() -> Result[A, E] | Result[A, UnhandledException]:
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
