# okresult

[![PyPI version](https://img.shields.io/pypi/v/okresult.svg)](https://pypi.org/project/okresult/)
[![Python version](https://img.shields.io/pypi/pyversions/okresult.svg)](https://pypi.org/project/okresult/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Tests](https://github.com/pedrodrocha/okresult/actions/workflows/test.yml/badge.svg)](https://github.com/pedrodrocha/okresult/actions/workflows/test.yml)
[![Type checking: Pyright](https://img.shields.io/badge/type%20checking-Pyright-blue.svg)](https://github.com/microsoft/pyright)
[![Code style: Black](https://img.shields.io/badge/code%20style-Black-000000.svg)](https://github.com/psf/black)

Lightweight Result type for Python, inspired by [better-result](https://github.com/dmmulroy/better-result).

## Install

```bash
pip install okresult
```

## Quick Start

```python
from okresult import Result, safe
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
    "ok": lambda data: f"Got: {data['name']}",
    "err": lambda e: f"Failed: {e.cause}",
})
```

## Contents

- [Creating Results](#creating-results)
- [Transforming Results](#transforming-results)
- [Handling Errors](#handling-errors)
- [Extracting Values](#extracting-values)
- [Panic](#panic)
- [Retry Support](#retry-support)
- [Generator Composition](#generator-composition) *(TODO)*
- [Tagged Errors](#tagged-errors)
- [Serialization](#serialization) 
- [API Reference](#api-reference)

## Creating Results

```python
from okresult import Result, Ok, Err, safe, safe_async

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
result = safe({"try_": risky, "catch": lambda e: "Error: " + str(e)})
```

## Transforming Results

```python
from okresult import Ok, Err, map as result_map

result = (
    Ok[int, ValueError](2)
    .map(lambda x: x * 2)  # Ok(4)
    .and_then(
        # Chain Result-returning functions
        lambda x: Ok[int, ValueError](x) if x > 0 else Err[int, ValueError](ValueError("negative"))
    )
)

# Standalone functions (data-first or data-last)
result_map(result, lambda x: x + 1)
result_map(lambda x: x + 1)(result)  # Pipeable
```

## Handling Errors

```python
from okresult import Result, TaggedError

err_result: Result[int, ValueError] = Result.err(ValueError("invalid"))

# Transform errors
err_result.map_err(lambda e: RuntimeError(str(e)))  # Err(RuntimeError(...))


# Recover from specific errors
class NotFoundError(TaggedError):
    __slots__ = ("id",)
    @property
    def tag(self) -> str:
        return "NotFoundError"
    def __init__(self, id: str) -> None:
        super().__init__(f"Not found: {id}")
        self.id = id

def fetch_user(id: str) -> Result[dict[str, str], NotFoundError]:
    if id == "valid":
        return Result.ok({"name": "John", "id": id})
    return Result.err(NotFoundError(id))

def recover_from_not_found(e: NotFoundError) -> Result[dict[str, str], NotFoundError]:
    return Result.ok({"name": "Default User"})

result = fetch_user("123").match({
    "ok": lambda user: Result.ok(user),  # Pass through success
    "err": lambda e: recover_from_not_found(e) if e.tag == "NotFoundError" else Result.err(e)
})


```

## Extracting Values

```python
from okresult import Result, unwrap

result_ok = Result.ok(42)
result_err = Result.err(ValueError("invalid"))

# Unwrap (throws on Err)
value = unwrap(result_ok)
value = result_ok.unwrap()
value = result_ok.unwrap("custom error message")

# With fallback
value = result_err.unwrap_or(0)

# Pattern match
value = result_err.match({
    "ok": lambda v: v,
    "err": lambda e: 0,
})
```
## Generator Composition

*TODO: Coming soon*

## Panic

Thrown (not returned) when user callbacks throw inside Result operations. Represents a defect in your code, not a domain error.

```python
from okresult import Result, Panic

# Callback throws → Panic
try:
    Result.ok(1).map(lambda x: 1 // 0)
except Panic as p:
    print(f"Panic: {p.message}, caused by: {p.cause}")

# Catch handler throws → Panic  
try:
    Result.try_({
        "try_": lambda: 1 / 1,
        "catch": lambda e: 1 // 0  # Bug in handler
    })
except Panic as p:
    print(f"Panic: {p.message}, caused by: {p.cause}")

# and_then callback throws → Panic
try:
    Result.ok(1).and_then(lambda x: 1 // 0)
except Panic as p:
    print(f"Panic: {p.message}, caused by: {p.cause}")

# match handler throws → Panic
try:
    Result.ok(1).match({
        "ok": lambda x: 1 // 0,  # Bug in handler
        "err": lambda e: 0
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
from okresult import safe, safe_async

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
        }
    }
)
```

## UnhandledException

When `safe()` or `safe_async()` catches an exception without a custom handler, the error type is `UnhandledException`:

```python
from okresult import Result, UnhandledException, safe, safe_async, TaggedError
import json

# Automatic — error type is UnhandledException
def parse_json(input: str) -> dict:
    return json.loads(input)

result = safe(parse_json)

# Custom handler — you control the error type using TaggedError
class ParseError(TaggedError):
    __slots__ = ("cause",)
    
    @property
    def tag(self) -> str:
        return "ParseError"
    
    def __init__(self, cause: Exception) -> None:
        super().__init__(f"Parse failed: {str(cause)}")
        self.cause = cause

result = safe({
    "try_": lambda: parse_json('{"key": "value"}'),
    "catch": lambda e: ParseError(e)
})

# Same for async
async def fetch_and_parse(json_str: str) -> dict:
    # Simulate async work
    return parse_json(json_str)

# Async with custom error handler
result = await safe_async({
    "try_": lambda: fetch_and_parse('invalid'),
    "catch": lambda e: ParseError(e)
})
```

## Tagged Errors

```python
from okresult import Result, TaggedError
from typing import Union, TypeAlias

class NotFoundError(TaggedError):
    __slots__ = ("id",)
    @property
    def tag(self) -> str:
        return "NotFoundError"
    def __init__(self, id: str) -> None:
        super().__init__(f"Not found: {id}")
        self.id = id

class ValidationError(TaggedError):
    __slots__ = ("field",)
    @property
    def tag(self) -> str:
        return "ValidationError"
    def __init__(self, field: str) -> None:
        super().__init__(f"Invalid: {field}")
        self.field = field

AppError: TypeAlias = Union[NotFoundError, ValidationError] 

result_err = Result.err(ValidationError("name"))

def handle_validation_error(e: ValidationError) -> Result[dict[str, str], ValidationError]:
    return Result.ok({"message": f"Invalid: {e.field}"})
def handle_not_found_error(e: NotFoundError) -> Result[dict[str, str], NotFoundError]:
    return Result.ok({"name": "Default User"})

# Exhaustive matching
result_exhaustive = TaggedError.match(
    result_err.unwrap_err(),
    {
        "ValidationError": handle_validation_error,
        "NotFoundError": handle_not_found_error,
    }
)

# Partial matching with a fallback
result_partial = TaggedError.match_partial(
    result_err.unwrap_err(),
    {
        "ValidationError": handle_validation_error,
        "NotFoundError": handle_not_found_error,
    },
    otherwise=lambda e: Result.ok({"message": "Unknown error"})
)

```


## Serialization

Rehydrate Results from JSON for storage or network transfer.

```python
from okresult import Result
import json

# Serialize a Result to JSON (e.g., storage or network transfer)
original = Result.ok(42)
serialized_dict = original.serialize()            # {'status': 'ok', 'value': 42}
serialized_json = json.dumps(serialized_dict)     # "{\"status\":\"ok\",\"value\":42}"

# Rehydrate the serialized Result back to a Result instance
hydrated = Result.hydrate(json.loads(serialized_json))


# Now you can use Result methods again
doubled = hydrated.map(lambda x: x * 2)  # Ok(84)

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

## API Reference

### Types

| Type | Description |
|------|-------------|
| `Result[A, E]` | Base type for results (Ok or Err) |
| `Ok[A, E]` | Success variant |
| `Err[A, E]` | Error variant |
| `Matcher[A, B, E, F]` | TypedDict for pattern matching |
| `TaggedError` | Base class for tagged errors |
| `UnhandledException` | Error type for unhandled exceptions |

### Result Creation

| Function | Description |
|----------|-------------|
| `Result.ok(value)` | Create success result |
| `Result.err(error)` | Create error result |
| `Result.hydrate(data)` | Deserialize from dict; returns Result[object, object] \| None |
| `Result.hydrate_as(data, *, ok, err)` | Typed deserialization with decoders; returns Result[T, U] \| None |
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
