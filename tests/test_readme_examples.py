from okresult import (
    Result,
    Ok,
    Err,
    safe,
    fn,
    map as result_map,
    unwrap,
    TaggedError,
    Panic,
    Do,
    DoAsync,
)
import json
import asyncio
import pytest
from typing import Union, TypeAlias


# Error types for testing (shared across examples)
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


class TestQuickStart:
    def test_load_user_example(self) -> None:
        def load_user() -> dict[str, str]:
            return json.loads('{"name": "John", "age": "30"}')

        parsed: Result[dict[str, str], Exception] = safe(load_user)

        if parsed.is_ok():
            user_data = parsed.unwrap()
            assert isinstance(user_data, dict) and "name" in user_data
            assert user_data["name"] == "John"
        else:
            assert False, "Should be ok"

        message = parsed.match(
            {
                "ok": fn[dict[str, str], str](lambda data: f"Got: {data['name']}"),
                "err": fn[Exception, str](
                    lambda e: f"Failed: {getattr(e, 'cause', e)}"
                ),
            }
        )
        assert "Got: John" in message


class TestCreatingResults:
    def test_creates_ok(self) -> None:
        ok = Result.ok(42)
        assert ok.is_ok()

    def test_creates_err(self) -> None:
        err = Result.err(ValueError("failed"))
        assert err.is_err()

    def test_safe_with_throwing_function(self) -> None:
        def risky() -> float:
            raise ValueError("Invalid input")

        result = safe(risky)
        assert result.is_err()

    def test_safe_with_custom_error_handler(self) -> None:
        def risky() -> float:
            raise ValueError("Invalid input")

        result = safe(
            {"try_": risky, "catch": fn[Exception, str](lambda e: "Error: " + str(e))}
        )
        assert result.is_err()


class TestTransformingResults:
    def test_map_and_and_then_chaining(self) -> None:
        result = (
            Ok[int, ValueError](2)
            .map(fn[int, int](lambda x: x * 2))
            .and_then(
                fn[int, Result[int, ValueError]](
                    lambda x: (
                        Ok[int, ValueError](x)
                        if x > 0
                        else Err[int, ValueError](ValueError("negative"))
                    )
                )
            )
        )
        assert result.is_ok()
        assert result.unwrap() == 4

    def test_standalone_map_data_first(self) -> None:
        result = Ok[int, ValueError](5)
        mapped = result_map(result, fn[int, int](lambda x: x + 1))
        assert mapped.is_ok()
        assert mapped.unwrap() == 6

    def test_standalone_map_data_last(self) -> None:
        result = Ok[int, ValueError](5)
        mapper = result_map(fn[int, int](lambda x: x + 1))
        mapped = mapper(result)
        assert mapped.is_ok()
        assert mapped.unwrap() == 6


class TestHandlingErrors:
    class TestMapErr:
        def test_transforms_error_value(self) -> None:
            err_result: Result[int, ValueError] = Result.err(ValueError("invalid"))
            transformed = err_result.map_err(
                fn[ValueError, RuntimeError](lambda e: RuntimeError(str(e)))
            )
            assert transformed.is_err()
            assert isinstance(transformed.unwrap_err(), RuntimeError)

    class TestRecovery:
        def test_recovers_from_specific_errors(self) -> None:
            def fetch_user(id: str) -> Result[dict[str, str], AppError]:
                if id == "valid":
                    return Result.ok({"name": "John", "id": id})
                if not id:
                    return Result.err(ValidationError("id"))
                return Result.err(NotFoundError(id))

            default_user = {"name": "Default User"}

            # Recover from NotFoundError, pass through other errors
            result = fetch_user("123").match(
                {
                    "ok": fn[dict[str, str], Result[dict[str, str], AppError]](
                        lambda user: Result.ok(user)
                    ),
                    "err": fn[AppError, Result[dict[str, str], AppError]](
                        lambda e: (
                            Result.ok(default_user)
                            if e.tag == "NotFoundError"
                            else Result.err(e)
                        )
                    ),
                }
            )
            assert result.is_ok()
            assert result.unwrap() == default_user

            # Test that ValidationError passes through
            result_validation = fetch_user("").match(
                {
                    "ok": fn[dict[str, str], Result[dict[str, str], AppError]](
                        lambda user: Result.ok(user)
                    ),
                    "err": fn[AppError, Result[dict[str, str], AppError]](
                        lambda e: (
                            Result.ok(default_user)
                            if e.tag == "NotFoundError"
                            else Result.err(e)
                        )
                    ),
                }
            )
            assert result_validation.is_err()
            assert isinstance(result_validation.unwrap_err(), ValidationError)


class TestExtractingValues:
    def test_unwrap(self) -> None:
        result_ok = Result.ok(42)
        value = unwrap(result_ok)
        assert value == 42
        value = result_ok.unwrap()
        assert value == 42

    def test_unwrap_or(self) -> None:
        result_err = Result.err(ValueError("invalid"))
        value = result_err.unwrap_or(0)
        assert value == 0

    def test_match_for_extraction(self) -> None:
        result_err = Result.err(ValueError("invalid"))
        value = result_err.match(
            {
                "ok": fn[int, int](lambda v: v),
                "err": fn[ValueError, int](lambda e: 0),
            }
        )
        assert value == 0


class TestPanic:
    def test_map_callback_throws_panic(self) -> None:
        try:
            Result.ok(1).map(fn[int, int](lambda x: 1 // 0))
            assert False, "Should have raised Panic"
        except Panic as p:
            assert "map" in p.message.lower()

    def test_catch_handler_throws_panic(self) -> None:
        try:
            safe(
                {
                    "try_": lambda: int("bad"),
                    "catch": fn[Exception, int](lambda e: 1 // 0),  # Bug in handler
                }
            )
            assert False, "Should have raised Panic"
        except Panic as p:
            assert "panic" in str(p).lower() or "safe" in str(p).lower()

    def test_and_then_callback_throws_panic(self) -> None:
        try:
            Result.ok(1).and_then(
                fn[int, Result[int, str]](
                    lambda x: Result.err("error") if False else Result.ok(1 // 0)
                )
            )
            assert False, "Should have raised Panic"
        except Panic:
            pass

    def test_match_handler_throws_panic(self) -> None:
        try:
            Result.ok(1).match(
                {"ok": fn[int, int](lambda x: 1 // 0), "err": fn[str, int](lambda e: 0)}
            )
            assert False, "Should have raised Panic"
        except Panic:
            pass


class TestUnhandledException:
    def test_automatic_unhandled_exception(self) -> None:
        def parse_json(input: str) -> dict[str, str]:
            return json.loads(input)

        # Note: safe without options returns Result with UnhandledException
        # Wrap in lambda to make it a thunk (no-arg callable)
        result: Result[dict[str, str], Exception] = safe(
            lambda: parse_json('{"key": "value"}')
        )
        assert result.is_ok()

    def test_custom_error_handler(self) -> None:
        class ParseError(TaggedError):
            TAG = "ParseError"

            def __init__(self, cause: Exception) -> None:
                super().__init__(f"Parse failed: {str(cause)}")

        def parse_json(input: str) -> dict[str, str]:
            return json.loads(input)

        result: Result[dict[str, str], ParseError] = safe(
            {
                "try_": lambda: parse_json('{"key": "value"}'),
                "catch": fn[Exception, ParseError](lambda e: ParseError(e)),
            }
        )
        assert result.is_ok()


class TestTaggedErrors:
    def test_exhaustive_matching(self) -> None:
        result_err = Result.err(ValidationError("name"))

        result_exhaustive = TaggedError.match(
            result_err.unwrap_err(),
            {
                ValidationError: fn[
                    ValidationError, Result[dict[str, str], ValidationError]
                ](lambda e: Result.ok({"message": f"Invalid: {e.field}"})),
                NotFoundError: fn[
                    NotFoundError, Result[dict[str, str], ValidationError]
                ](lambda e: Result.ok({"name": "Default User"})),
            },
        )
        assert result_exhaustive.is_ok()

    def test_partial_matching_with_fallback(self) -> None:
        result_err = Result.err(ValidationError("name"))

        result_partial = TaggedError.match_partial(
            result_err.unwrap_err(),
            {
                ValidationError: fn[
                    ValidationError, Result[dict[str, str], ValidationError]
                ](lambda e: Result.ok({"message": f"Invalid: {e.field}"})),
                NotFoundError: fn[
                    NotFoundError, Result[dict[str, str], ValidationError]
                ](lambda e: Result.ok({"name": "Default User"})),
            },
            otherwise=fn[TaggedError, Result[dict[str, str], ValidationError]](
                lambda e: Result.ok({"message": "Unknown error"})
            ),
        )
        assert result_partial.is_ok()


class TestSerialization:
    def test_serialize_and_hydrate_ok(self) -> None:
        original = Result.ok(42)
        serialized_dict = original.serialize()
        assert serialized_dict == {"status": "ok", "value": 42}

        serialized_json = json.dumps(serialized_dict)
        hydrated = Result.hydrate(json.loads(serialized_json))
        assert hydrated is not None
        assert hydrated.is_ok()

        # Type assertion needed because hydrate returns Result[object, object]
        # We know it's an int from the original, so we can safely unwrap and recreate
        value = hydrated.unwrap() if hydrated.is_ok() else None
        assert value is not None
        assert isinstance(value, int)
        hydrated_int: Result[int, object] = Result.ok(value)
        doubled = hydrated_int.map(fn[int, int](lambda x: x * 2))
        assert doubled.is_ok()
        assert doubled.unwrap() == 84

    def test_serialize_and_hydrate_err(self) -> None:
        err_result = Result.err(ValueError("failed"))
        err_json = json.dumps(err_result.serialize())
        rehydrated = Result.hydrate(json.loads(err_json))
        assert rehydrated is not None
        assert rehydrated.is_err()

    def test_typed_hydration_with_decoders(self) -> None:
        original = Result.ok(42)
        serialized_dict = original.serialize()
        serialized_json = json.dumps(serialized_dict)

        def decode_int(x: object) -> int:
            if isinstance(x, int):
                return x
            raise ValueError("expected int")

        def decode_error(x: object) -> ValueError:
            return ValueError(str(x))

        typed = Result.hydrate_as(
            json.loads(serialized_json),
            ok=decode_int,
            err=decode_error,
        )
        assert typed is not None
        assert typed.is_ok()
        assert typed.unwrap() == 42


class TestGeneratorComposition:
    def test_motivation_nested_callbacks(self) -> None:
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
        assert result.is_ok()
        assert result.unwrap() == 10.0

    def test_motivation_generator_composition(self) -> None:
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
            a: int = yield parse_number("10")
            b: int = yield parse_number("2")
            c: float = yield divide(a, b)
            d: float = yield Result.ok(c * 2)  # Another operation
            return Result.ok(d)

        result = Result.gen(compute)
        assert result.is_ok()
        assert result.unwrap() == 10.0

    def test_synchronous_composition(self) -> None:
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
        assert result.is_ok()
        assert result.unwrap() == 5.0

    def test_synchronous_composition_short_circuit(self) -> None:
        def parse_number(s: str) -> Result[int, str]:
            try:
                return Result.ok(int(s))
            except ValueError:
                return Result.err(f"Invalid number: {s}")

        def divide(a: int, b: int) -> Result[float, str]:
            if b == 0:
                return Result.err("Division by zero")
            return Result.ok(a / b)

        def compute_with_error() -> Do[float, str]:
            a: int = yield parse_number("10")
            b: int = yield parse_number("invalid")  # This will short-circuit
            c: float = yield divide(a, b)
            return Result.ok(c)

        result_err = Result.gen(compute_with_error)
        assert result_err.is_err()
        assert "Invalid number" in result_err.unwrap_err()

    @pytest.mark.asyncio
    async def test_async_composition(self) -> None:
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
        assert result is not None
        assert result.is_ok()
        data = result.unwrap()
        assert isinstance(data, dict)
        assert "user" in data
        assert "posts" in data
