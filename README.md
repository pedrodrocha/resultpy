# okresult

[![PyPI version](https://img.shields.io/pypi/v/okresult.svg)](https://pypi.org/project/okresult/)
[![Python version](https://img.shields.io/pypi/pyversions/okresult.svg)](https://pypi.org/project/okresult/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Tests](https://github.com/pedrodrocha/okresult/actions/workflows/test.yml/badge.svg)](https://github.com/pedrodrocha/okresult/actions/workflows/test.yml)
![Coverage](./coverage.svg)
[![Type checking: Pyright](https://img.shields.io/badge/type%20checking-Pyright-blue.svg)](https://github.com/microsoft/pyright)
[![Code style: Black](https://img.shields.io/badge/code%20style-Black-000000.svg)](https://github.com/psf/black)

Lightweight Result type for Python, inspired by [better-result](https://github.com/dmmulroy/better-result).

## Install

```bash
pip install okresult
```

## Quick Start

```python
from okresult import Result, safe, fn
import json

# Wrap throwing functions
def load_user() -> dict[str, str]:
    return json.loads('{"name": "John", "age": 30}')
parsed = safe(load_user)

# Check and use
if parsed.is_ok():
    print(parsed.unwrap())
else:
    print(parsed.unwrap_err())

# Or use pattern matching
message = parsed.match({
    "ok": fn[dict[str, str], str](lambda data: f"Got: {data['name']}"),
    "err": fn[object, str](lambda e: f"Failed: {e.cause}"),
})
```

## Contents

- [Creating Results](#creating-results)
- [Transforming Results](#transforming-results)
- [Handling Errors](#handling-errors)
- [Extracting Values](#extracting-values)
- [Generator Composition](#generator-composition)
- [Panic](#panic)
- [Retry Support](#retry-support)
- [Tagged Errors](#tagged-errors)
- [Serialization](#serialization) 
- [Typed Lambda Expressions](#typed-lambda-expressions)
- [API Reference](#api-reference)

## Creating Results

```python
from okresult import Result, Ok, Err, safe, safe_async, fn

# Success
ok = Result.ok(42)

# Error
err = Result.err(ValueError("failed"))

# From throwing function
def risky() -> float:
    raise ValueError("Invalid input")

result = safe(risky)

# From async function
async def risky_async() -> float:
    raise ValueError("Invalid input")

result = await safe_async(risky_async)

# With custom error handling
result = safe({"try_": risky, "catch": fn[Exception, str](lambda e: "Error: " + str(e))})
```

## Transforming Results

```python
from okresult import Ok, Err, map as result_map, fn

result = (
    Ok[int, ValueError](2)
    .map(fn[int, int](lambda x: x * 2))  # Ok(4)
    .and_then(
        # Chain Result-returning functions
        fn[int, Result[int, ValueError]](lambda x: Ok[int, ValueError](x) if x > 0 else Err[int, ValueError](ValueError("negative")))
    )
)

# Standalone functions (data-first or data-last)
result_map(result, fn[int, int](lambda x: x + 1))
result_map(fn[int, int](lambda x: x + 1))(result)  # Pipeable
```

## Handling Errors

```python
from okresult import Result, TaggedError, fn
from typing import Union, TypeAlias

err_result: Result[int, ValueError] = Result.err(ValueError("invalid"))

# Transform errors
err_result.map_err(fn[ValueError, RuntimeError](lambda e: RuntimeError(str(e))))  # Err(RuntimeError(...))


# Recover from specific errors
class NotFoundError(TaggedError):
    TAG = "NotFoundError"

    __slots__ = ("id",)
    
    def __init__(self, id: str) -> None:
        super().__init__(f"Not found: {id}")
        self.id = id

class ValidationError(TaggedError):
    TAG = "ValidationError"
    __slots__ = ("field",)
    
    def __init__(self, field: str) -> None:
        super().__init__(f"Invalid: {field}")
        self.field = field

AppError: TypeAlias = Union[NotFoundError, ValidationError]

def fetch_user(id: str) -> Result[dict[str, str], AppError]:
    if id == "valid":
        return Result.ok({"name": "John", "id": id})
    if not id:
        return Result.err(ValidationError("id"))
    return Result.err(NotFoundError(id))

default_user = {"name": "Default User"}


result = fetch_user("123").match({
    "ok": fn[dict[str, str], Result[dict[str, str], AppError]](lambda user: Result.ok(user)),
    "err": fn[AppError, Result[dict[str, str], AppError]](
        lambda e: Result.ok(default_user) if e.tag == "NotFoundError" else Result.err(e)
    )
})


```

## Extracting Values

```python
from okresult import Result, unwrap, fn

result_ok = Result.ok(42)
result_err = Result.err(ValueError("invalid"))

# Unwrap (throws on Err)
value = unwrap(result_ok)
value = result_ok.unwrap()

# With fallback
value = result_err.unwrap_or(0)

# Pattern match
value = result_err.match({
    "ok": fn[int, int](lambda v: v),
    "err": fn[ValueError, int](lambda e: 0),
})
```

## Generator Composition

Chain multiple Results without nested callbacks or early returns. Values are automatically unwrapped on success and short-circuited on error.

### Why?

Without generator composition, chaining many operations leads to deeply nested callbacks or "callback hell":

```python
# Without generator composition - deeply nested callbacks
def parse_number(s: str) -> Result[int, str]:
    try:
        return Result.ok(int(s))
    except ValueError:
        return Result.err(f"Invalid number: {s}")

def divide(a: int, b: int) -> Result[float, str]:
    if b == 0:
        return Result.err("Division by zero")
    return Result.ok(a / b)

result = parse_number("10").and_then(
    lambda a: parse_number("2").and_then(
        lambda b: divide(a, b).and_then(
            lambda c: Result.ok(c * 2)  # Another operation
        )
    )
)
```

With generator composition, the same code reads linearly:

```python
# With generator composition - clean and readable
def compute() -> Do[float, str]:
    a: int = yield parse_number("10")
    b: int = yield parse_number("2")
    c: float = yield divide(a, b)
    d: float = yield Result.ok(c * 2)  # Another operation
    return Result.ok(d)

result = Result.gen(compute) 
# ^Result.ok(10)
```

Generator composition scales infinitely - you can chain as many operations as needed without nesting getting deeper. Each `yield` automatically unwraps `Ok` values and short-circuits on `Err`.

### Synchronous Composition

```python
from okresult import Result, Do

def parse_number(s: str) -> Result[int, str]:
    try:
        return Result.ok(int(s))
    except ValueError:
        return Result.err(f"Invalid number: {s}")

def divide(a: int, b: int) -> Result[float, str]:
    if b == 0:
        return Result.err("Division by zero")
    return Result.ok(a / b)

def compute() -> Do[float, str]:
    a: int = yield parse_number("10")  # Unwraps or short-circuits
    b: int = yield parse_number("2")
    c: float = yield divide(a, b)
    return Result.ok(c)

result = Result.gen(compute)
# Result[float, str] - errors from all yields are collected into union type

# Short-circuiting on error
def compute_with_error() -> Do[float, str]:
    a: int = yield parse_number("10")
    b: int = yield parse_number("invalid")  # This will short-circuit
    c: float = yield divide(a, b)
    return Result.ok(c)

result_err = Result.gen(compute_with_error)
# Returns Err("Invalid number: invalid")
```

### Async Composition

```python
from okresult import Result, DoAsync
import asyncio

async def fetch_user(id: int) -> Result[dict[str, str], str]:
    await asyncio.sleep(0.001)  # Simulate async work
    if id > 0:
        return Result.ok({"name": "John", "id": str(id)})
    return Result.err("Invalid user ID")

async def fetch_posts(user_id: str) -> Result[list[dict[str, str]], str]:
    await asyncio.sleep(0.001)  # Simulate async work
    return Result.ok([{"title": "Post 1"}, {"title": "Post 2"}])

async def load_user_data() -> DoAsync[dict[str, object], str]:
    user_id = 123
    user = yield await fetch_user(user_id)
    posts = yield await fetch_posts(user["id"])
    yield Result.ok({"user": user, "posts": posts})

result = await Result.gen_async(load_user_data)
# Result[dict[str, object], str]
```

Errors from all yielded Results are automatically collected into the final error union type. The generator short-circuits on the first `Err`, so subsequent yields are skipped.

**Note:** Async generators must yield the final Result as the last value (non-empty `return` statements are a SyntaxError per [PEP 525](https://peps.python.org/pep-0525/)). Raising `StopAsyncIteration` with a value is not supported at the moment by choice. Always use `yield Result.ok(...)` instead.

## Panic

Thrown (not returned) when user callbacks throw inside Result operations. Represents a defect in your code, not a domain error.

```python
from okresult import Result, Panic, fn

# Callback throws → Panic
try:
    Result.ok(1).map(fn[int, int](lambda x: 1 // 0))
except Panic as p:
    print(f"Panic: {p.message}, caused by: {p.cause}")

# Catch handler throws → Panic  
try:
    safe({
        "try_": lambda: 1 / 1,
        "catch": fn[Exception, int](lambda e: 1 // 0)  # Bug in handler
    })
except Panic as p:
    print(f"Panic: {p.message}, caused by: {p.cause}")

# and_then callback throws → Panic
try:
    Result.ok(1).and_then(fn[int, Result[int, str]](lambda x: 1 // 0))
except Panic as p:
    print(f"Panic: {p.message}, caused by: {p.cause}")

# match handler throws → Panic
try:
    Result.ok(1).match({
        "ok": fn[int, int](lambda x: 1 // 0),  # Bug in handler
        "err": fn[str, int](lambda e: 0)
    })
except Panic as p:
    print(f"Panic: {p.message}, caused by: {p.cause}")
```

### Why Panic?

`Err` is for recoverable domain errors. `Panic` is for bugs — like Rust's `panic!()`. If your `.map()` callback throws, that's not an error to handle, it's a defect to fix. Returning `Err` would collapse type safety (`Result[T, E]` becomes `Result[T, E | Unknown]`).

### Panic Properties

| Property | Type | Description |
|----------|------|-------------|
| `message` | `str` | Describes where/what panicked (e.g., "map failed") |
| `cause` | `Exception` | The exception that was thrown |


## Retry Support

```python
from okresult import safe, safe_async, fn

def risky() -> float:
    raise ValueError("Invalid input")

# Sync retry
result = safe(risky, {"retry": {"times": 3}})

# Async retry with backoff
async def fetch(url: str) -> str:
    raise ConnectionError("Network error")

result = await safe_async(
    lambda: fetch("https://api.example.com"),  
    {
        "retry": {
            "times": 3,
            "delay_ms": 100,
            "backoff": "exponential",  # or "linear" | "constant"
            # Optional: only retry for certain error types/flags
            "should_retry": lambda e: isinstance(e, ConnectionError),
        },
    },
)

# With custom error mapping and richer predicates
from okresult import TaggedError
from typing import Union

class RetryableException(TaggedError):
    TAG = "RetryableException"
    __slots__ = ("msg",)
    
    def __init__(self, msg: str) -> None:
        super().__init__(msg)
        self.msg = msg

class NonRetryableException(TaggedError):
    TAG = "NonRetryableException"
    __slots__ = ("msg",)
    
    def __init__(self, msg: str) -> None:
        super().__init__(msg)
        self.msg = msg

ApiError = Union[RetryableException, NonRetryableException]

async def call_api(url: str) -> str:
    raise RuntimeError("rate limited")

result = await safe_async(
    {
        "try_": lambda: call_api("https://api.example.com"),
        "catch": fn[Exception, ApiError](
            lambda e: RetryableException(str(e)) if "rate limited" in str(e) else NonRetryableException(str(e))
        ),
    },
    {
        "retry": {
            "times": 3,
            "delay_ms": 100,
            "backoff": "exponential",
            "should_retry": lambda e: e.tag == "RetryableException",
        },
    },
)

# Async predicates: For async decisions (e.g. feature flags, rate limits)
async def check_rate_limit() -> bool:
    return True

result = await safe_async(
    lambda: call_api("https://api.example.com"),
    {
        "retry": {
            "times": 3,
            "delay_ms": 100,
            "backoff": "exponential",
            # should_retry can be async in safe_async
            "should_retry": async lambda e: await check_rate_limit(),
        },
    },
)
```

## UnhandledException

When `safe()` or `safe_async()` catches an exception without a custom handler, the error type is `UnhandledException`:

```python
from okresult import Result, UnhandledException, safe, safe_async, TaggedError, fn
import json

# Automatic — error type is UnhandledException
def parse_json(input: str) -> dict[str, str]:
    return json.loads(input)

result = safe(lambda: parse_json('{"key": "value"}'))  

# Custom handler — you control the error type using TaggedError
class ParseError(TaggedError):
    TAG = "ParseError"
    __slots__ = ("cause",)
    
    def __init__(self, cause: Exception) -> None:
        super().__init__(f"Parse failed: {str(cause)}")
        self.cause = cause

result = safe({
    "try_": lambda: parse_json('{"key": "value"}'),  
    "catch": fn[Exception, ParseError](lambda e: ParseError(e))
})

# Same for async
async def fetch_and_parse(json_str: str) -> dict[str, str]:
    # Simulate async work
    return parse_json(json_str)

# Async with custom error handler
result = await safe_async({
    "try_": lambda: fetch_and_parse('invalid'),  
    "catch": fn[Exception, ParseError](lambda e: ParseError(e))
})
```

## Tagged Errors

```python
from okresult import Result, TaggedError, fn
from typing import Union, TypeAlias

class NotFoundError(TaggedError):
    TAG = "NotFoundError"
    __slots__ = ("id",)
    def __init__(self, id: str) -> None:
        super().__init__(f"Not found: {id}")
        self.id = id

class ValidationError(TaggedError):
    TAG = "ValidationError"
    __slots__ = ("field",)
    def __init__(self, field: str) -> None:
        super().__init__(f"Invalid: {field}")
        self.field = field

AppError: TypeAlias = Union[NotFoundError, ValidationError] 

result_err = Result.err(ValidationError("name"))

# Exhaustive matching
result_exhaustive = TaggedError.match(
    result_err.unwrap_err(),
    {
        ValidationError: fn[ValidationError, Result[dict[str, str], ValidationError]](lambda e: Result.ok({"message": f"Invalid: {e.field}"})),
        NotFoundError: fn[NotFoundError, Result[dict[str, str], ValidationError]](lambda e: Result.ok({"name": "Default User"})),
    }
)

# Partial matching with a fallback
result_partial = TaggedError.match_partial(
    result_err.unwrap_err(),
    {
        ValidationError: fn[ValidationError, Result[dict[str, str], ValidationError]](lambda e: Result.ok({"message": f"Invalid: {e.field}"})),
        NotFoundError: fn[NotFoundError, Result[dict[str, str], ValidationError]](lambda e: Result.ok({"name": "Default User"})),
    },
    otherwise=fn[TaggedError, Result[dict[str, str], ValidationError]](lambda e: Result.ok({"message": "Unknown error"}))
)

```


## Serialization

Rehydrate Results from JSON for storage or network transfer.

```python
from okresult import Result, fn
import json

# Serialize a Result to JSON (e.g., storage or network transfer)
original = Result.ok(42)
serialized_dict = original.serialize()            # {'status': 'ok', 'value': 42}
serialized_json = json.dumps(serialized_dict)     # "{\"status\":\"ok\",\"value\":42}"

# Rehydrate the serialized Result back to a Result instance
hydrated = Result.hydrate(json.loads(serialized_json))


# Now you can use Result methods again
doubled = hydrated.map(fn[int, int](lambda x: x * 2))  # Ok(84)

# Works with Err too
err_result = Result.err(ValueError("failed"))
err_json = json.dumps(err_result.serialize())     # "{\"status\":\"err\",\"value\":\"failed\"}"
rehydrated = Result.hydrate(json.loads(err_json))

# Note: Exceptions are serialized as strings for portability.
# Rehydrating an Err produced from an Exception yields Err("failed") (a string),
# not an Exception instance. Use typed hydration to reconstruct specific types.

# Typed hydration with decoders
def decode_int(x: object) -> int:
    if isinstance(x, int):
        return x
    raise ValueError("expected int")

def decode_error(x: object) -> ValueError:
    # Turn the serialized error payload back into a ValueError
    return ValueError(str(x))

typed: Result[int, ValueError] | None = Result.hydrate_as(
    json.loads(serialized_json),
    ok=decode_int,
    err=decode_error,
)

```

## Typed Lambda Expressions

Python doesn't support type annotations inside `lambda` expressions, making it difficult to express precise types for inline functions. The `fn` helper provides a way to create typed callables using subscript syntax, achieving a close semantic equivalent to a "typed lambda" in Python.

```python
from okresult import fn

# Explicitly typed lambda
double = fn[int, int](lambda x: x * 2)
add_one = fn[int, int](lambda x: x + 1)

# Works with Result transformations
result = Result.ok(5).map(double)  # Ok(10)

# Works with match handlers
message = result.match({
    "ok": fn[int, str](lambda x: f"Value: {x}"),
    "err": fn[str, str](lambda e: f"Error: {e}"),
})
```

At runtime, `fn` returns the provided callable unchanged (no wrapping, allocation, or indirection). All type information is enforced statically by type checkers (e.g., pyright, mypy). The above `double` example is equivalent, from a typing perspective, to defining a named function:

```python
def double(x: int) -> int:
    return x * 2
```

Instead of requiring verbose named functions or explicit `Callable` annotations, `fn` shifts the type declaration to the call boundary while keeping lambdas concise and idiomatic. It's particularly useful in functional-style APIs (e.g., `map`, `and_then`, `match`) where lambdas are common and precise typing significantly improves developer experience.

## API Reference

### Types

| Type | Description |
|------|-------------|
| `Result[A, E]` | Base type for results (Ok or Err) |
| `Ok[A, E]` | Success variant |
| `Err[A, E]` | Error variant |
| `Do[A, E]` | Type alias for Generator[Result[Any, E], Any, Result[A, E]] |
| `DoAsync[A, E]` | Type alias for AsyncGenerator[Result[Any, E], Any] |
| `Matcher[A, B, E, F]` | TypedDict for pattern matching |
| `TaggedError` | Base class for tagged errors |
| `UnhandledException` | Error type for unhandled exceptions |

### Result Creation

| Function | Description |
|----------|-------------|
| `Result.ok(value)` | Create success result |
| `Result.err(error)` | Create error result |
| `Result.gen(fn, context?)` | Generator-based Result composition (do-notation) |
| `Result.gen_async(fn, context?)` | Async generator-based Result composition |
| `Result.flatten(result)` | Flatten nested Result into single Result  |
| `Result.partition(results)` | Partition iterable of Results into a tuppl (list[ok_values], list[err_values]) |
| `Result.hydrate(data)` | Deserialize from dict |
| `Result.hydrate_as(data, *, ok, err)` | Typed deserialization with decoders |
| `Ok(value)` | Create Ok instance |
| `Err(error)` | Create Err instance |
| `safe(fn, config?)` | Wrap throwing function with optional retry |
| `safe_async(fn, config?)` | Wrap async function with optional retry |

### Module-Level Functions (Data-First & Data-Last)

| Function | Description |
|----------|-------------|
| `map(result, fn)` or `map(fn)(result)` | Transform success value |
| `map_err(result, fn)` or `map_err(fn)(result)` | Transform error value |
| `tap(result, fn)` or `tap(fn)(result)` | Side effect on success |
| `tap_async(result, fn)` or `tap_async(fn)(result)` | Async side effect on success |
| `and_then(result, fn)` or `and_then(fn)(result)` | Chain Result-returning function |
| `and_then_async(result, fn)` or `and_then_async(fn)(result)` | Chain async Result-returning function |
| `match(result, handlers)` or `match(handlers)(result)` | Pattern match on Result |
| `unwrap(result, message?)` | Extract value or raise |

### Instance Methods

| Method | Description |
|--------|-------------|
| `.status` | Property: `"ok"` or `"err"` |
| `.is_ok()` | Check if Ok |
| `.is_err()` | Check if Err |
| `.map(fn)` | Transform success value |
| `.map_err(fn)` | Transform error value |
| `.serialize()` | Serialize to dict for storage/transport |
| `.and_then(fn)` | Chain Result-returning function |
| `.and_then_async(fn)` | Chain async Result-returning function |
| `.match({"ok": fn, "err": fn})` | Pattern match |
| `.unwrap(message?)` | Extract value or raise |
| `.unwrap_or(fallback)` | Extract value or return fallback |
| `.unwrap_err(message?)` | Extract error or raise |
| `.tap(fn)` | Side effect on success |
| `.tap_async(fn)` | Async side effect on success |

### TaggedError Methods

| Method | Description |
|--------|-------------|
| `TaggedError.is_error(value)` | Type guard for Exception instances |
| `TaggedError.is_tagged_error(value)` | Type guard for TaggedError instances |
| `TaggedError.match(error, handlers)` | Exhaustive match by tag string |
| `TaggedError.match_partial(error, handlers, otherwise)` | Partial match by tag string with fallback |
| `.tag` | Property: error tag string |
| `.message` | Property: error message |

### Configuration Types

| Type | Description |
|------|-------------|
| `SafeConfig` | Configuration for `safe()` |
| `SafeConfigAsync` | Configuration for `safe_async()` |
| `SafeOptions[A, E]` | Options with custom error mapping |
| `RetryConfig` | Retry configuration for sync operations |
| `RetryConfigAsync` | Retry configuration for async operations |

## License

MIT
