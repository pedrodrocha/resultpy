from resultpy import Result, Ok, Err, map, map_err, tap, tap_async, unwrap
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
