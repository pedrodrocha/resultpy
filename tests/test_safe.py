import pytest
from resultpy import (
    safe,
    safe_async,
    UnhandledException,
)


class TestSafe:
    class TestSimpleThunk:
        def test_returns_ok_on_success(self) -> None:
            result = safe(lambda: 42)
            assert result.is_ok()
            assert result.unwrap() == 42

        def test_returns_err_on_exception(self) -> None:
            result = safe(lambda: int("bad"))
            assert result.is_err()
            error = result.unwrap_err()
            assert isinstance(error, UnhandledException)
            assert error.tag == "UnhandledException"

        def test_wraps_any_exception(self) -> None:
            def raise_custom() -> int:
                raise RuntimeError("Custom error")

            result = safe(raise_custom)
            assert result.is_err()
            err = result.unwrap_err()
            assert isinstance(err, UnhandledException)
            assert err.tag == "UnhandledException"
            assert str(err) == "Unhandled exception: Custom error"

    class TestWithOptions:
        def test_returns_ok_on_success(self) -> None:
            result = safe({"try_": lambda: 42, "catch": lambda e: str(e)})
            assert result.is_ok()
            assert result.unwrap() == 42

        def test_returns_custom_error(self) -> None:
            result = safe({"try_": lambda: int("bad"), "catch": lambda e: str(e)})
            assert result.is_err()
            assert "invalid literal" in result.unwrap_err()

        def test_maps_exception_to_custom_type(self) -> None:
            class MyError:
                def __init__(self, message: str) -> None:
                    self.message = message

            result = safe(
                {"try_": lambda: int("bad"), "catch": lambda e: MyError(str(e))}
            )
            assert result.is_err()
            err = result.unwrap_err()
            assert isinstance(err, MyError)
            assert "invalid literal" in err.message

    class TestWithRetry:
        def test_retries_on_failure(self) -> None:
            attempts = 0

            def flaky() -> int:
                nonlocal attempts
                attempts += 1
                if attempts < 3:
                    raise ValueError("Not yet")
                return 42

            result = safe(flaky, {"retry": {"times": 5}})
            assert result.is_ok()
            assert result.unwrap() == 42
            assert attempts == 3

        def test_returns_error_after_all_retries(self) -> None:
            attempts = 0

            def always_fails() -> int:
                nonlocal attempts
                attempts += 1
                raise ValueError("Always fails")

            result = safe(always_fails, {"retry": {"times": 3}})
            assert result.is_err()
            assert attempts == 4  # 1 initial + 3 retries

        def test_no_retry_when_success(self) -> None:
            attempts = 0

            def succeeds() -> int:
                nonlocal attempts
                attempts += 1
                return 42

            result = safe(succeeds, {"retry": {"times": 5}})
            assert result.is_ok()
            assert attempts == 1


class TestSafeAsync:
    class TestSimpleThunk:
        @pytest.mark.asyncio
        async def test_returns_ok_on_success(self) -> None:
            async def async_fn() -> int:
                return 42

            result = await safe_async(async_fn)
            assert result.is_ok()
            assert result.unwrap() == 42

        @pytest.mark.asyncio
        async def test_returns_err_on_exception(self) -> None:
            async def async_fn() -> int:
                raise ValueError("Async error")

            result = await safe_async(async_fn)
            assert result.is_err()
            error = result.unwrap_err()
            assert isinstance(error, UnhandledException)
            assert error.tag == "UnhandledException"
            assert str(error) == "Unhandled exception: Async error"

    class TestWithOptions:
        @pytest.mark.asyncio
        async def test_returns_ok_on_success(self) -> None:
            async def async_fn() -> int:
                return 42

            result = await safe_async({"try_": async_fn, "catch": lambda e: str(e)})
            assert result.is_ok()
            assert result.unwrap() == 42

        @pytest.mark.asyncio
        async def test_returns_custom_error(self) -> None:
            async def async_fn() -> int:
                raise ValueError("Async error")

            result = await safe_async(
                {"try_": async_fn, "catch": lambda e: f"Caught: {e}"}
            )
            assert result.is_err()
            assert result.unwrap_err() == "Caught: Async error"

    class TestWithRetry:
        @pytest.mark.asyncio
        async def test_retries_on_failure(self) -> None:
            attempts = 0

            async def flaky() -> int:
                nonlocal attempts
                attempts += 1
                if attempts < 3:
                    raise ValueError("Not yet")
                return 42

            result = await safe_async(flaky, {"retry": {"times": 5}})
            assert result.is_ok()
            assert result.unwrap() == 42
            assert attempts == 3

        @pytest.mark.asyncio
        async def test_returns_error_after_all_retries(self) -> None:
            attempts = 0

            async def always_fails() -> int:
                nonlocal attempts
                attempts += 1
                raise ValueError("Always fails")

            result = await safe_async(always_fails, {"retry": {"times": 3}})
            assert result.is_err()
            assert attempts == 4  # 1 initial + 3 retries

        @pytest.mark.asyncio
        async def test_with_delay(self) -> None:
            import time

            attempts = 0
            timestamps: list[float] = []

            async def flaky() -> int:
                nonlocal attempts
                attempts += 1
                timestamps.append(time.time())
                if attempts < 3:
                    raise ValueError("Not yet")
                return 42

            result = await safe_async(
                flaky,
                {"retry": {"times": 5, "delay_ms": 50, "backoff": "constant"}},
            )
            assert result.is_ok()
            assert attempts == 3

            # Check delays (should be ~50ms between each)
            if len(timestamps) >= 2:
                delay1 = timestamps[1] - timestamps[0]
                assert delay1 >= 0.04  # Allow some tolerance

        @pytest.mark.asyncio
        async def test_exponential_backoff(self) -> None:
            import time

            attempts = 0
            timestamps: list[float] = []

            async def always_fails() -> int:
                nonlocal attempts
                attempts += 1
                timestamps.append(time.time())
                raise ValueError("Always fails")

            result = await safe_async(
                always_fails,
                {"retry": {"times": 3, "delay_ms": 20, "backoff": "exponential"}},
            )
            assert result.is_err()
            assert attempts == 4

            if len(timestamps) >= 3:
                delay1 = timestamps[1] - timestamps[0]
                delay2 = timestamps[2] - timestamps[1]
                assert delay2 > delay1
