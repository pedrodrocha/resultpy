from resultpy import Result, Ok, Err


class TestResult:
    class TestOk:
        def test_creates_ok_with_value(self):
            ok = Result.ok(42)

            assert ok.status == "ok"
            assert ok.value == 42
            assert isinstance(ok, Ok)

        def test_creates_ok_with_none(self):
            ok = Result.ok(None)

            assert ok.status == "ok"
            assert ok.value is None
            assert isinstance(ok, Ok)

    class TestErr:
        def test_creates_err_with_error(self):
            result = Result.err("An error occurred")
            assert result.status == "err"
            assert result.value == "An error occurred"
            assert isinstance(result, Err)

        def test_creates_err_with_error_object(self):
            error = ValueError("Invalid value")
            result = Result.err(error)
            assert result.status == "err"
            assert result.value == error
            assert isinstance(result, Err)

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
