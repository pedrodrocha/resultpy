from typing import Never
from okresult import (
    Result,
    Ok,
    Err,
    map,
    map_err,
    tap,
    tap_async,
    unwrap,
    and_then,
    and_then_async,
    match,
    Panic,
)
import pytest


class TestResult:
    class TestOk:
        def test_creates_ok_with_value(self) -> None:
            ok = Result.ok(42)

            assert ok.status == "ok"
            assert ok.unwrap() == 42
            assert isinstance(ok, Ok)

        def test_creates_ok_with_none(self) -> None:
            ok = Result.ok(None)

            assert ok.status == "ok"
            assert ok.unwrap() is None
            assert isinstance(ok, Ok)

    class TestErr:
        def test_creates_err_with_error(self) -> None:
            result = Result.err("An error occurred")
            assert result.status == "err"
            assert isinstance(result, Err)

        def test_creates_err_with_error_object(self) -> None:
            error = ValueError("Invalid value")
            result = Result.err(error)
            assert result.status == "err"
            assert isinstance(result, Err)

    class TestMapErr:
        def test_transforms_err_value(self) -> None:
            err = Result.err("Not found")
            new_err = err.map_err(lambda e: f"Error: {e}")

            assert new_err == Err("Error: Not found")
            assert isinstance(new_err, Err)

        def test_transforms_with_error_object(self) -> None:
            err = Result.err(ValueError("Invalid input"))
            new_err = err.map_err(lambda e: RuntimeError(f"Wrapped: {e}"))

            assert isinstance(new_err, Err)
            assert isinstance(new_err.value, RuntimeError)
            assert str(new_err.value) == "Wrapped: Invalid input"

        def test_passes_through_ok(self) -> None:
            ok = Result.ok(10)
            mapped = ok.map_err(lambda e: f"Error: {e}")

            assert ok.is_ok() is True
            assert isinstance(mapped, Ok)
            assert mapped.unwrap() == 10

    class TestMap:
        def test_transforms_ok_value(self) -> None:
            ok = Result.ok(5)
            new_ok = ok.map(lambda x: x * 2)

            assert new_ok == Ok(10)
            assert isinstance(new_ok, Ok)

        def test_passes_through_err(self) -> None:
            result = Result.err("fail")
            mapped = result.map(lambda x: x * 3)

            assert result.is_err() is True
            assert isinstance(mapped, Err)

        def test_method_chaining(self) -> None:
            def double(x: int) -> int:
                return x * 2

            def add_one(x: int) -> int:
                return x + 1

            def to_string(x: int) -> str:
                return f"Result: {x}"

            result = Result.ok(5).map(double).map(add_one).map(to_string)

            assert result.unwrap() == "Result: 11"  # (5 * 2) + 1 = 11

    class TestIsOk:
        def test_returns_true_for_ok(self) -> None:
            ok = Result.ok(100)
            assert ok.is_ok() is True

        def test_returns_false_for_err(self) -> None:
            err = Result.err("Error")
            assert err.is_ok() is False

    class TestIsErr:
        def test_returns_true_for_err(self) -> None:
            err = Result.err("Error")
            assert err.is_err() is True

        def test_returns_false_for_ok(self) -> None:
            ok = Result.ok(100)
            assert ok.is_err() is False

    class TestUnwrap:
        def test_returns_value_for_ok(self) -> None:
            ok = Result.ok(100)
            assert ok.unwrap() == 100

        def test_raises_exception_for_err(self) -> None:
            err = Result.err("Error")
            with pytest.raises(Exception):
                err.unwrap()

        def test_raises_exception_for_err_with_message(self) -> None:
            err = Result.err("Error")
            with pytest.raises(Exception, match="Custom message"):
                err.unwrap("Custom message")

    class TestUnwrapOr:

        def test_returns_value_for_ok(self) -> None:
            ok = Result.ok(100)
            assert ok.unwrap_or(0) == 100

        def test_returns_fallback_for_err(self) -> None:
            err = Result.err("Error")
            assert err.unwrap_or(0) == 0

    class TestTap:
        def test_runs_side_effect_on_ok(self) -> None:
            captured = 0

            def capture(x: int) -> None:
                nonlocal captured
                captured = x

            result = Result.ok(100).tap(capture)
            assert captured == 100
            assert result.unwrap() == 100

        def test_skips_side_effect_on_err(self) -> None:
            captured = 0

            def capture(x: int) -> None:
                nonlocal captured
                captured = x

            _result = Result.err("Error").tap(capture)
            assert captured == 0

    class TestTapAsync:
        @pytest.mark.asyncio
        async def test_runs_side_effect_on_ok(self) -> None:
            captured = 0

            async def capture(x: int) -> None:
                nonlocal captured
                captured = x

            result = await Result.ok(100).tap_async(capture)
            assert captured == 100
            assert result.unwrap() == 100

    class TestStandaloneMap:
        def test_data_first_transforms_ok_value(self) -> None:
            result = Result.ok(5)
            mapped = map(result, lambda x: x * 2)
            assert mapped.unwrap() == 10

        def test_data_last_transforms_ok_value(self) -> None:
            def double(x: int) -> int:
                return x * 2

            mapper = map(double)
            result = mapper(Result.ok(6))
            assert result.unwrap() == 12

        def test_data_first_catches_callback_error(self) -> None:
            def failing_callback(x: int) -> int:
                raise ValueError("Callback failed")

            result = Result.ok(5)
            with pytest.raises(Panic) as exc_info:
                map(result, failing_callback)
            assert "map failed" in str(exc_info.value)

        def test_data_last_catches_callback_error(self) -> None:
            def failing_callback(x: int) -> int:
                raise ValueError("Callback failed")

            mapper = map(failing_callback)
            result = Result.ok(5)
            with pytest.raises(Panic) as exc_info:
                mapper(result)
            assert "map failed" in str(exc_info.value)

    class TestStandaloneMapErr:
        def test_data_first_transforms_err_value(self) -> None:
            result = Result.err("Error")
            mapped = map_err(result, lambda e: f"Error: {e}")
            assert mapped == Err("Error: Error")
            assert isinstance(mapped, Err)

        def test_data_last_transforms_err_value(self) -> None:
            def error_to_string(e: str) -> str:
                return f"Error: {e}"

            mapper = map_err(error_to_string)
            result = mapper(Result.err("Error"))
            assert result == Err("Error: Error")
            assert isinstance(result, Err)

        def test_data_first_catches_callback_error(self) -> None:
            def failing_callback(e: str) -> str:
                raise ValueError("Callback failed")

            result = Result.err("error")
            with pytest.raises(Panic) as exc_info:
                map_err(result, failing_callback)
            assert "map_err failed" in str(exc_info.value)

        def test_data_last_catches_callback_error(self) -> None:
            def failing_callback(e: str) -> str:
                raise ValueError("Callback failed")

            mapper = map_err(failing_callback)
            result = Result.err("error")
            with pytest.raises(Panic) as exc_info:
                mapper(result)
            assert "map_err failed" in str(exc_info.value)

    class TestStandaloneTap:
        def test_data_first_runs_side_effect_on_ok(self) -> None:
            captured = 0

            def capture(x: int) -> None:
                nonlocal captured
                captured = x

            result = tap(Result.ok(100), capture)
            assert captured == 100
            assert result.unwrap() == 100

        def test_data_first_skips_side_effect_on_err(self) -> None:
            captured = 0

            def capture(x: int) -> None:
                nonlocal captured
                captured = x

            result = tap(Result.err("Error"), capture)
            assert captured == 0
            assert result == Err("Error")
            assert isinstance(result, Err)

        def test_data_last_runs_side_effect_on_ok(self) -> None:
            captured = 0

            def capture(x: int) -> None:
                nonlocal captured
                captured = x

            tapper = tap(capture)
            result = tapper(Result.ok(100))
            assert captured == 100
            assert result.unwrap() == 100

        def test_data_last_skips_side_effect_on_err(self) -> None:
            captured = 0

            def capture(x: int) -> None:
                nonlocal captured
                captured = x

            tapper = tap(capture)
            err: Err[int, str] = Err("Error")
            result = tapper(err)
            assert captured == 0
            assert result == Err("Error")
            assert isinstance(result, Err)

        def test_data_first_catches_callback_error(self) -> None:
            def failing_callback(x: int) -> None:
                raise ValueError("Callback failed")

            result = Result.ok(5)
            with pytest.raises(Panic) as exc_info:
                tap(result, failing_callback)
            assert "tap failed" in str(exc_info.value)

        def test_data_last_catches_callback_error(self) -> None:
            def failing_callback(x: int) -> None:
                raise ValueError("Callback failed")

            tapper = tap(failing_callback)
            result = Result.ok(5)
            with pytest.raises(Panic) as exc_info:
                tapper(result)
            assert "tap failed" in str(exc_info.value)

    class TestStandaloneTapAsync:
        @pytest.mark.asyncio
        async def test_data_first_runs_side_effect_on_ok(self) -> None:
            captured = 0

            async def capture(x: int) -> None:
                nonlocal captured
                captured = x

            result = await tap_async(Result.ok(100), capture)
            assert captured == 100
            assert result.unwrap() == 100

        @pytest.mark.asyncio
        async def test_data_first_skips_side_effect_on_err(self) -> None:
            captured = 0

            async def capture(x: int) -> None:
                nonlocal captured
                captured = x

            _result = await tap_async(Result.err("Error"), capture)
            assert captured == 0

        @pytest.mark.asyncio
        async def test_data_last_runs_side_effect_on_ok(self) -> None:
            captured = 0

            async def capture(x: int) -> None:
                nonlocal captured
                captured = x

            tapper = tap_async(capture)
            result = await tapper(Result.ok(100))
            assert captured == 100
            assert result.unwrap() == 100

        @pytest.mark.asyncio
        async def test_data_last_skips_side_effect_on_err(self) -> None:
            captured = 0

            async def capture(x: int) -> None:
                nonlocal captured
                captured = x

            tapper = tap_async(capture)
            err: Err[int, str] = Err("Error")
            _result = await tapper(err)
            assert captured == 0

        @pytest.mark.asyncio
        async def test_data_first_catches_callback_error(self) -> None:
            async def failing_callback(x: int) -> None:
                raise ValueError("Callback failed")

            result = Result.ok(5)
            with pytest.raises(Panic) as exc_info:
                await tap_async(result, failing_callback)
            assert "tap_async failed" in str(exc_info.value)

        @pytest.mark.asyncio
        async def test_data_last_catches_callback_error(self) -> None:
            async def failing_callback(x: int) -> None:
                raise ValueError("Callback failed")

            tapper = tap_async(failing_callback)
            result = Result.ok(5)
            with pytest.raises(Panic) as exc_info:
                await tapper(result)
            assert "tap_async failed" in str(exc_info.value)

    class TestStandaloneUnwrap:
        def test_returns_value_for_ok(self) -> None:
            result = Result.ok(42)
            assert unwrap(result) == 42

        def test_raises_exception_for_err(self) -> None:
            result = Result.err("Error")
            with pytest.raises(Exception):
                unwrap(result)

        def test_raises_exception_with_custom_message(self) -> None:
            result = Result.err("Error")
            with pytest.raises(Exception, match="Custom message"):
                unwrap(result, "Custom message")

    class TestAndThen:
        def test_chains_ok_to_ok(self) -> None:
            ok: Ok[int, str] = Ok(2)

            def triple(x: int) -> Ok[int, str]:
                return Ok(x * 3)

            result = ok.and_then(triple)
            assert result.unwrap() == 6

        def test_chains_ok_to_err(self) -> None:
            ok: Ok[int, str] = Ok(2)

            def to_err(x: int) -> Err[int, str]:
                return Err("Error")

            result = ok.and_then(to_err)

            assert result.is_err()
            assert isinstance(result, Err)
            assert result.value == "Error"

        def test_short_circuits_on_err(self) -> None:
            called = False

            def side_effect(x: int) -> Result[int, str]:
                nonlocal called
                called = True
                return Ok(x * 2)

            err: Err[int, str] = Err("Initial Error")
            result = err.and_then(side_effect)
            assert (
                called is False
            )  # Function should NOT be called when starting with Err
            assert result.is_err()

    class TestAndThenAsync:
        @pytest.mark.asyncio
        async def test_chains_ok_to_ok(self) -> None:
            ok: Ok[int, str] = Ok(2)

            async def async_triple(x: int) -> Ok[int, str]:
                return Ok(x * 3)

            result = await ok.and_then_async(async_triple)
            assert result.unwrap() == 6

        @pytest.mark.asyncio
        async def test_chains_ok_to_err(self) -> None:
            ok: Ok[int, str] = Ok(2)

            async def async_to_err(x: int) -> Err[int, str]:
                return Err("Error")

            result = await ok.and_then_async(async_to_err)

            assert result.is_err()
            assert isinstance(result, Err)
            assert result.value == "Error"

        @pytest.mark.asyncio
        async def test_short_circuits_on_err(self) -> None:
            called = False

            async def side_effect(x: int) -> Result[int, str]:
                nonlocal called
                called = True
                return Ok(x * 2)

            err: Err[int, str] = Err("Initial Error")
            result = await err.and_then_async(side_effect)
            assert (
                called is False
            )  # Function should NOT be called when starting with Err
            assert result.is_err()

    class TestUnwrapErr:
        def test_returns_error_for_err(self) -> None:
            err: Err[int, str] = Err("Error message")
            assert err.unwrap_err() == "Error message"

        def test_raises_exception_for_ok(self) -> None:
            ok: Ok[int, str] = Ok(42)
            with pytest.raises(Exception):
                ok.unwrap_err()

        def test_raises_exception_for_ok_with_message(self) -> None:
            ok: Ok[int, str] = Ok(42)
            with pytest.raises(Exception, match="Expected an error"):
                ok.unwrap_err("Expected an error")

    class TestAndThenTopLevel:
        def test_data_first_chains_ok_to_ok(self) -> None:
            def double(x: int) -> Result[int, str]:
                return Ok(x * 2)

            ok: Ok[int, str] = Ok(5)
            result = and_then(ok, double)
            assert result.unwrap() == 10

        def test_data_first_chains_ok_to_err(self) -> None:
            def fail(x: int) -> Result[int, str]:
                return Err("Failed")

            ok: Ok[int, str] = Ok(5)
            result = and_then(ok, fail)
            assert result.is_err()
            assert result.unwrap_err() == "Failed"

        def test_data_first_short_circuits_on_err(self) -> None:
            called = False

            def side_effect(x: int) -> Result[int, str]:
                nonlocal called
                called = True
                return Ok(x * 2)

            err: Err[int, str] = Err("Initial Error")
            result = and_then(err, side_effect)
            assert called is False
            assert result.is_err()

        def test_data_last_returns_callable(self) -> None:
            def double(x: int) -> Result[int, str]:
                return Ok(x * 2)

            doubler = and_then(double)
            ok: Ok[int, str] = Ok(5)
            result = doubler(ok)
            assert result.unwrap() == 10

        def test_data_last_chains_ok_to_err(self) -> None:
            def fail(x: int) -> Result[int, str]:
                return Err("Failed")

            failer = and_then(fail)
            ok: Ok[int, str] = Ok(5)
            result = failer(ok)
            assert result.is_err()
            assert result.unwrap_err() == "Failed"

        def test_data_last_short_circuits_on_err(self) -> None:
            called = False

            def side_effect(x: int) -> Result[int, str]:
                nonlocal called
                called = True
                return Ok(x * 2)

            transformer = and_then(side_effect)
            err: Err[int, str] = Err("Initial Error")
            result = transformer(err)
            assert called is False
            assert result.is_err()

        def test_error_union_type(self) -> None:
            """Test that errors can be of different types (E | F)."""

            def validate(x: int) -> Result[int, ValueError]:
                if x < 0:
                    return Err(ValueError("Negative"))
                return Ok(x)

            initial: Result[int, str] = Ok(5)
            result = and_then(initial, validate)
            assert result.unwrap() == 5

            initial_err: Result[int, str] = Err("String error")
            result2 = and_then(initial_err, validate)
            assert result2.is_err()

        def test_data_first_catches_callback_error(self) -> None:
            def failing_callback(x: int) -> Result[int, str]:
                raise ValueError("Callback failed")

            result = Result.ok(5)
            with pytest.raises(Panic) as exc_info:
                and_then(result, failing_callback)
            assert "and_then failed" in str(exc_info.value)

        def test_data_last_catches_callback_error(self) -> None:
            def failing_callback(x: int) -> Result[int, str]:
                raise ValueError("Callback failed")

            chainer = and_then(failing_callback)
            result = Result.ok(5)
            with pytest.raises(Panic) as exc_info:
                chainer(result)
            assert "and_then failed" in str(exc_info.value)

    class TestAndThenAsyncTopLevel:
        @pytest.mark.asyncio
        async def test_data_first_chains_ok_to_ok(self) -> None:
            async def async_double(x: int) -> Result[int, str]:
                return Ok(x * 2)

            ok: Ok[int, str] = Ok(5)
            result = await and_then_async(ok, async_double)
            assert result.unwrap() == 10

        @pytest.mark.asyncio
        async def test_data_first_chains_ok_to_err(self) -> None:
            async def async_fail(x: int) -> Result[int, str]:
                return Err("Async Failed")

            ok: Ok[int, str] = Ok(5)
            result = await and_then_async(ok, async_fail)
            assert result.is_err()
            assert result.unwrap_err() == "Async Failed"

        @pytest.mark.asyncio
        async def test_data_first_short_circuits_on_err(self) -> None:
            called = False

            async def async_side_effect(x: int) -> Result[int, str]:
                nonlocal called
                called = True
                return Ok(x * 2)

            err: Err[int, str] = Err("Initial Error")
            result = await and_then_async(err, async_side_effect)
            assert called is False
            assert result.is_err()

        @pytest.mark.asyncio
        async def test_data_last_returns_callable(self) -> None:
            async def async_double(x: int) -> Result[int, str]:
                return Ok(x * 2)

            doubler = and_then_async(async_double)
            ok: Ok[int, str] = Ok(5)
            result = await doubler(ok)
            assert result.unwrap() == 10

        @pytest.mark.asyncio
        async def test_data_last_chains_ok_to_err(self) -> None:
            async def async_fail(x: int) -> Result[int, str]:
                return Err("Async Failed")

            failer = and_then_async(async_fail)
            ok: Ok[int, str] = Ok(5)
            result = await failer(ok)
            assert result.is_err()
            assert result.unwrap_err() == "Async Failed"

        @pytest.mark.asyncio
        async def test_data_last_short_circuits_on_err(self) -> None:
            called = False

            async def async_side_effect(x: int) -> Result[int, str]:
                nonlocal called
                called = True
                return Ok(x * 2)

            transformer = and_then_async(async_side_effect)
            err: Err[int, str] = Err("Initial Error")
            result = await transformer(err)
            assert called is False
            assert result.is_err()

        @pytest.mark.asyncio
        async def test_data_first_catches_callback_error(self) -> None:
            async def failing_callback(x: int) -> Result[int, str]:
                raise ValueError("Callback failed")

            result = Result.ok(5)
            with pytest.raises(Panic) as exc_info:
                await and_then_async(result, failing_callback)
            assert "and_then_async failed" in str(exc_info.value)

        @pytest.mark.asyncio
        async def test_data_last_catches_callback_error(self) -> None:
            async def failing_callback(x: int) -> Result[int, str]:
                raise ValueError("Callback failed")

            chainer = and_then_async(failing_callback)
            result = Result.ok(5)
            with pytest.raises(Panic) as exc_info:
                await chainer(result)
            assert "and_then_async failed" in str(exc_info.value)

    class TestMatch:
        def test_matches_ok(self) -> None:

            result = Ok[int, Never](42).match(
                {"ok": lambda x: x * 2, "err": lambda e: e.upper()}
            )
            assert result == 84

        def test_matches_err(self) -> None:
            result = Err[Never, str]("error").match(
                {"ok": lambda x: x * 2, "err": lambda e: e.upper()}
            )
            assert result == "ERROR"

        def test_throws_panic_when_ok_handler_throws(self) -> None:
            ok: Ok[int, str] = Ok(42)
            with pytest.raises(Panic) as exc_info:
                ok.match({"ok": lambda x: 1 // 0, "err": lambda e: 0})
            assert "match" in str(exc_info.value)

        def test_throws_panic_when_err_handler_throws(self) -> None:
            err: Err[int, str] = Err("error")
            with pytest.raises(Panic) as exc_info:
                err.match({"ok": lambda x: 0, "err": lambda e: 1 // 0})
            assert "match" in str(exc_info.value)

    class TestMatchTopLevel:
        def test_data_first_matches_ok(self) -> None:
            ok: Ok[int, str] = Ok(42)
            result = match(ok, {"ok": lambda x: x * 2, "err": lambda e: 0})
            assert result == 84

        def test_data_first_matches_err(self) -> None:
            err: Err[int, str] = Err("error")
            result = match(err, {"ok": lambda x: 0, "err": lambda e: len(e)})
            assert result == 5

        def test_data_first_matches_error_object(self) -> None:
            err: Err[int, ValueError] = Err(ValueError("error"))
            result = match(err, {"ok": lambda x: "", "err": lambda e: str(e).upper()})
            assert result == "ERROR"

        def test_data_last_returns_callable(self) -> None:
            def double(x: int) -> int:
                return x * 2

            def default(e: str) -> int:
                return 0

            matcher = match({"ok": double, "err": default})
            ok: Ok[int, str] = Ok(21)
            result = matcher(ok)
            assert result == 42

        def test_data_last_matches_err(self) -> None:
            def default(x: int) -> int:
                return 0

            def err_len(e: str) -> int:
                return len(e)

            matcher = match({"ok": default, "err": err_len})
            err: Err[int, str] = Err("hello")
            result = matcher(err)
            assert result == 5

        def test_both_handlers_return_same_type(self) -> None:
            ok: Ok[int, str] = Ok(10)
            err: Err[int, str] = Err("error")

            result_ok = match(ok, {"ok": lambda x: str(x), "err": lambda e: e})
            result_err = match(err, {"ok": lambda x: str(x), "err": lambda e: e})

            assert result_ok == "10"
            assert result_err == "error"

        def test_data_first_throws_panic_when_ok_handler_throws(self) -> None:
            ok: Ok[int, str] = Ok(42)
            with pytest.raises(Panic) as exc_info:
                match(ok, {"ok": lambda x: 1 // 0, "err": lambda e: 0})
            assert "match" in str(exc_info.value)

        def test_data_first_throws_panic_when_err_handler_throws(self) -> None:
            err: Err[int, str] = Err("error")
            with pytest.raises(Panic) as exc_info:
                match(err, {"ok": lambda x: 0, "err": lambda e: 1 // 0})
            assert "match" in str(exc_info.value)

        def test_data_last_throws_panic_when_ok_handler_throws(self) -> None:
            def ok_handler(x: int) -> int:
                return 1 // 0

            def err_handler(e: str) -> int:
                return 0

            matcher = match({"ok": ok_handler, "err": err_handler})
            ok: Ok[int, str] = Ok(42)
            with pytest.raises(Panic) as exc_info:
                matcher(ok)
            assert "match" in str(exc_info.value)

        def test_data_last_throws_panic_when_err_handler_throws(self) -> None:
            def ok_handler(x: int) -> int:
                return 0

            def err_handler(e: str) -> int:
                return 1 // 0

            matcher = match({"ok": ok_handler, "err": err_handler})
            err: Err[int, str] = Err("error")
            with pytest.raises(Panic) as exc_info:
                matcher(err)
            assert "match" in str(exc_info.value)

    class TestSerialize:
        def test_ok_serialization(self) -> None:
            ok = Result.ok({"key": "value", "number": 42})
            serialized = ok.serialize()
            assert serialized == {
                "status": "ok",
                "value": {"key": "value", "number": 42},
            }

        def test_err_serialization(self) -> None:
            err = Result.err("An error occurred")
            serialized = err.serialize()
            assert serialized == {"status": "err", "value": "An error occurred"}

        def test_err_serialization_with_object(self) -> None:
            error = ValueError("Invalid value")
            err = Result.err(error)
            serialized = err.serialize()
            assert serialized == {"status": "err", "value": str(error)}

    class TestHydrate:
        def test_hydrates_serialized_ok(self) -> None:
            serialized = {"status": "ok", "value": 42}
            result = Result.hydrate(serialized)
            assert result is not None
            assert result.is_ok()
            assert result.unwrap() == 42

        def test_hydrates_serialized_err(self) -> None:
            serialized = {"status": "err", "value": "fail"}
            result = Result.hydrate(serialized)
            assert result is not None
            assert result.is_err()
            assert result.unwrap_err() == "fail"

        def test_returns_none_for_invalid_data(self) -> None:
            assert Result.hydrate({"foo": "bar"}) is None
            assert Result.hydrate(None) is None
            assert Result.hydrate(42) is None
            assert Result.hydrate({"status": "ok"}) is None
            assert Result.hydrate({"value": 42}) is None

    class TestHydrateAs:
        def test_hydrates_as_ok_with_decoder(self) -> None:
            def decode_int(x: object) -> int:
                if isinstance(x, int):
                    return x
                raise ValueError(f"Expected int, got {type(x)}")

            serialized = {"status": "ok", "value": 42}
            result: Result[int, str] | None = Result.hydrate_as(
                serialized,
                ok=decode_int,
                err=str,
            )
            assert result is not None
            assert isinstance(result, Ok)
            assert result.unwrap() == 42

        def test_hydrates_as_err_with_decoder(self) -> None:
            def decode_error(x: object) -> str:
                return f"Error: {x}"

            def decode_int(x: object) -> int:
                if isinstance(x, int):
                    return x
                raise ValueError(f"Expected int, got {type(x)}")

            serialized = {"status": "err", "value": "something failed"}
            result: Result[int, str] | None = Result.hydrate_as(
                serialized,
                ok=decode_int,
                err=decode_error,
            )
            assert result is not None
            assert isinstance(result, Err)
            assert result.unwrap_err() == "Error: something failed"

        def test_returns_none_for_invalid_data(self) -> None:
            def decode_int(x: object) -> int:
                if isinstance(x, int):
                    return x
                raise ValueError(f"Expected int, got {type(x)}")

            assert (
                Result.hydrate_as(
                    {"foo": "bar"},
                    ok=decode_int,
                    err=str,
                )
                is None
            )
            assert Result.hydrate_as(None, ok=decode_int, err=str) is None

            assert Result.hydrate_as(42, ok=decode_int, err=str) is None

        def test_returns_err_when_decoder_fails(self) -> None:
            def strict_int(x: object) -> int:
                if isinstance(x, int):
                    return x
                raise ValueError("Not an int")

            serialized = {"status": "ok", "value": "not_an_int"}
            result = Result.hydrate_as(
                serialized,
                ok=strict_int,
                err=str,
            )
            assert result is not None
            assert result.is_err()
            error = result.unwrap_err()
            assert isinstance(error, ValueError)
            assert str(error) == "Not an int"
