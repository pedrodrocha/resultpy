from resultpy import Result, Ok, Err, map, map_err, tap, tap_async, unwrap
import pytest


class TestResult:
    class TestOk:
        def test_creates_ok_with_value(self):
            ok = Result.ok(42)

            assert ok.status == "ok"
            assert ok.unwrap() == 42
            assert isinstance(ok, Ok)

        def test_creates_ok_with_none(self):
            ok = Result.ok(None)

            assert ok.status == "ok"
            assert ok.unwrap() is None
            assert isinstance(ok, Ok)

    class TestErr:
        def test_creates_err_with_error(self):
            result = Result.err("An error occurred")
            assert result.status == "err"
            assert result.unwrap_err() == "An error occurred"
            assert isinstance(result, Err)

        def test_creates_err_with_error_object(self):
            error = ValueError("Invalid value")
            result = Result.err(error)
            assert result.status == "err"
            assert result.unwrap_err() == error
            assert isinstance(result, Err)

    class TestMapErr:
        def test_transforms_err_value(self):
            err = Result.err("Not found")
            new_err = err.mapErr(lambda e: f"Error: {e}")

            assert new_err == Err("Error: Not found")
            assert isinstance(new_err, Err)

        def test_transforms_with_error_object(self):
            err = Result.err(ValueError("Invalid input"))
            new_err = err.mapErr(lambda e: RuntimeError(f"Wrapped: {e}"))

            assert isinstance(new_err.unwrap_err(), RuntimeError)
            assert str(new_err.unwrap_err()) == "Wrapped: Invalid input"

        def test_passes_through_ok(self):
            ok = Result.ok(10)
            mapped = ok.mapErr(lambda e: f"Error: {e}")

            assert ok.is_ok() is True
            assert isinstance(mapped, Ok)
            assert mapped.unwrap() == 10

    class TestMap:
        def test_transforms_ok_value(self):
            ok = Result.ok(5)
            new_ok = ok.map(lambda x: x * 2)

            print(new_ok)
            print(ok)

            assert new_ok == Ok(10)
            assert isinstance(new_ok, Ok)

        def test_passes_through_err(self):
            result = Result.err("fail")
            mapped = result.map(lambda x: x * 3)

            assert result.is_err() is True
            assert isinstance(mapped, Err)
            assert mapped.unwrap_err() == "fail"

        def test_method_chaining(self):
            def double(x: int) -> int:
                return x * 2

            def add_one(x: int) -> int:
                return x + 1

            def to_string(x: int) -> str:
                return f"Result: {x}"

            result = Result.ok(5).map(double).map(add_one).map(to_string)

            assert result.unwrap() == "Result: 11"  # (5 * 2) + 1 = 11

    class TestIsOk:
        def test_returns_true_for_ok(self):
            ok = Result.ok(100)
            assert ok.is_ok() is True

        def test_returns_false_for_err(self):
            err = Result.err("Error")
            assert err.is_ok() is False

    class TestIsErr:
        def test_returns_true_for_err(self):
            err = Result.err("Error")
            assert err.is_err() is True

        def test_returns_false_for_ok(self):
            ok = Result.ok(100)
            assert ok.is_err() is False

    class TestUnwrap:
        def test_returns_value_for_ok(self):
            ok = Result.ok(100)
            assert ok.unwrap() == 100

        def test_raises_exception_for_err(self):
            err = Result.err("Error")
            with pytest.raises(Exception):
                err.unwrap()

        def test_raises_exception_for_err_with_message(self):
            err = Result.err("Error")
            with pytest.raises(Exception, match="Custom message"):
                err.unwrap("Custom message")

    class TestUnwrapOr:

        def test_returns_value_for_ok(self):
            ok = Result.ok(100)
            assert ok.unwrap_or(0) == 100

        def test_returns_fallback_for_err(self):
            err = Result.err("Error")
            assert err.unwrap_or(0) == 0

    class TestTap:
        def test_runs_side_effect_on_ok(self):
            captured = 0

            def capture(x: int) -> None:
                nonlocal captured
                captured = x

            result = Result.ok(100).tap(capture)
            assert captured == 100
            assert result.unwrap() == 100

        def test_skips_side_effect_on_err(self):
            captured = 0

            def capture(x: int) -> None:
                nonlocal captured
                captured = x

            result = Result.err("Error").tap(capture)
            assert captured == 0
            assert result.unwrap_err() == "Error"

    class TestTapAsync:
        @pytest.mark.asyncio
        async def test_runs_side_effect_on_ok(self):
            captured = 0

            async def capture(x: int) -> None:
                nonlocal captured
                captured = x

            result = await Result.ok(100).tap_async(capture)
            assert captured == 100
            assert result.unwrap() == 100

    class TestStandaloneMap:
        def test_data_first_transforms_ok_value(self):
            result = Result.ok(5)
            mapped = map(result, lambda x: x * 2)
            assert mapped.unwrap() == 10

        def test_data_last_transforms_ok_value(self):
            def double(x: int) -> int:
                return x * 2

            mapped = map(double)
            result = mapped(Result.ok(6))
            assert result.unwrap() == 12

    class TestStandaloneMapErr:
        def test_data_first_transforms_err_value(self):
            result = Result.err("Error")
            mapped = map_err(result, lambda e: f"Error: {e}")
            assert mapped.unwrap_err() == "Error: Error"

        def test_data_last_transforms_err_value(self):
            def error_to_string(e: str) -> str:
                return f"Error: {e}"

            mapped = map_err(error_to_string)
            result = mapped(Result.err("Error"))
            assert result.unwrap_err() == "Error: Error"

    class TestStandaloneTap:
        def test_data_first_runs_side_effect_on_ok(self):
            captured = 0

            def capture(x: int) -> None:
                nonlocal captured
                captured = x

            result = tap(Result.ok(100), capture)
            assert captured == 100
            assert result.unwrap() == 100

        def test_data_first_skips_side_effect_on_err(self):
            captured = 0

            def capture(x: int) -> None:
                nonlocal captured
                captured = x

            result = tap(Result.err("Error"), capture)
            assert captured == 0
            assert result.unwrap_err() == "Error"

        def test_data_last_runs_side_effect_on_ok(self):
            captured = 0

            def capture(x: int) -> None:
                nonlocal captured
                captured = x

            tapper = tap(capture)
            result = tapper(Result.ok(100))
            assert captured == 100
            assert result.unwrap() == 100

        def test_data_last_skips_side_effect_on_err(self):
            captured = 0

            def capture(x: int) -> None:
                nonlocal captured
                captured = x

            tapper = tap(capture)
            result = tapper(Result.err("Error"))
            assert captured == 0
            assert result.unwrap_err() == "Error"

    class TestStandaloneTapAsync:
        @pytest.mark.asyncio
        async def test_data_first_runs_side_effect_on_ok(self):
            captured = 0

            async def capture(x: int) -> None:
                nonlocal captured
                captured = x

            result = await tap_async(Result.ok(100), capture)
            assert captured == 100
            assert result.unwrap() == 100

        @pytest.mark.asyncio
        async def test_data_first_skips_side_effect_on_err(self):
            captured = 0

            async def capture(x: int) -> None:
                nonlocal captured
                captured = x

            result = await tap_async(Result.err("Error"), capture)
            assert captured == 0
            assert result.unwrap_err() == "Error"

        @pytest.mark.asyncio
        async def test_data_last_runs_side_effect_on_ok(self):
            captured = 0

            async def capture(x: int) -> None:
                nonlocal captured
                captured = x

            tapper = tap_async(capture)
            result = await tapper(Result.ok(100))
            assert captured == 100
            assert result.unwrap() == 100

        @pytest.mark.asyncio
        async def test_data_last_skips_side_effect_on_err(self):
            captured = 0

            async def capture(x: int) -> None:
                nonlocal captured
                captured = x

            tapper = tap_async(capture)
            result = await tapper(Result.err("Error"))
            assert captured == 0
            assert result.unwrap_err() == "Error"

    class TestStandaloneUnwrap:
        def test_returns_value_for_ok(self):
            result = Result.ok(42)
            assert unwrap(result) == 42

        def test_raises_exception_for_err(self):
            result = Result.err("Error")
            with pytest.raises(Exception):
                unwrap(result)

        def test_raises_exception_with_custom_message(self):
            result = Result.err("Error")
            with pytest.raises(Exception, match="Custom message"):
                unwrap(result, "Custom message")
