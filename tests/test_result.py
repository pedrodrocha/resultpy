from resultpy import Result, Ok, Err, map
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

        def test_standalone_function_data_first_pattern(self):
            result = Result.ok(2)
            mapped_result = map(result, lambda x: x * 3)
            assert mapped_result.unwrap() == 6

        def test_standalone_function_data_last_pattern(self):
            def double(x: int) -> int:
                return x * 2

            doubled = map(double)

            result = doubled(Result.ok(6))
            assert result.unwrap() == 12

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
