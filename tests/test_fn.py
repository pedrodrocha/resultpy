from okresult import fn, map, map_err, Result


class TestFn:
    class TestBasicFunctionality:
        def test_returns_same_function(self) -> None:
            def original(x: int) -> int:
                return x * 2

            wrapped = fn[int, int](original)

            assert wrapped is original
            assert wrapped(5) == 10

        def test_preserves_function_behavior(self) -> None:
            add_one = fn[int, int](lambda x: x + 1)

            assert add_one(5) == 6
            assert add_one(10) == 11

    class TestTypeInference:
        def test_infers_types_from_lambda(self) -> None:
            double = fn[int, int](lambda x: x * 2)

            # Should work with int
            assert double(5) == 10
            assert double(7) == 14

        def test_works_with_string_transformations(self) -> None:
            upper = fn[str, str](lambda s: s.upper())

            assert upper("hello") == "HELLO"
            assert upper("world") == "WORLD"

        def test_works_with_type_conversions(self) -> None:
            to_string = fn[object, str](lambda x: str(x))

            assert to_string(42) == "42"
            assert to_string(True) == "True"

    class TestExplicitTyping:
        def test_works_with_explicitly_typed_functions(self) -> None:
            def double_func(x: int) -> int:
                return x * 2

            typed_double = fn[int, int](double_func)

            assert typed_double(5) == 10
            assert typed_double(7) == 14

        def test_works_with_string_typed_functions(self) -> None:
            def format_error(e: str) -> str:
                return f"Error: {e}"

            formatter = fn[str, str](format_error)

            assert formatter("not found") == "Error: not found"
            assert formatter("invalid") == "Error: invalid"

    class TestWithResultMap:
        def test_works_with_result_map(self) -> None:
            double = fn[int, int](lambda x: x * 2)
            result = Result.ok(5).map(double)

            assert result.is_ok()
            assert result.unwrap() == 10

        def test_works_with_result_map_chaining(self) -> None:
            double = fn[int, int](lambda x: x * 2)
            add_one = fn[int, int](lambda x: x + 1)

            result = Result.ok(5).map(double).map(add_one)

            assert result.is_ok()
            assert result.unwrap() == 11  # (5 * 2) + 1

        def test_passes_through_err_with_map(self) -> None:
            double = fn[int, int](lambda x: x * 2)
            err_result = Result.err("error")
            mapped = err_result.map(double)

            assert mapped.is_err()
            assert mapped.unwrap_err() == "error"

    class TestWithResultMapErr:
        def test_works_with_result_map_err(self) -> None:
            format_error = fn[str, str](lambda e: f"Error: {e}")
            result = Result.err("not found").map_err(format_error)

            assert result.is_err()
            assert result.unwrap_err() == "Error: not found"

        def test_works_with_error_object_transformation(self) -> None:
            def wrap_error(e: ValueError) -> RuntimeError:
                return RuntimeError(f"Wrapped: {e}")

            wrapper = fn[ValueError, RuntimeError](wrap_error)
            err = Result.err(ValueError("Invalid input"))
            mapped = err.map_err(wrapper)

            assert mapped.is_err()
            error_value = mapped.unwrap_err()
            assert isinstance(error_value, RuntimeError)
            assert "Wrapped: Invalid input" in str(error_value)

        def test_passes_through_ok_with_map_err(self) -> None:
            ok_result = Result.ok(42)
            mapped = ok_result.map_err(fn[str, str](lambda e: f"Error: {e}"))

            assert mapped.is_ok()
            assert mapped.unwrap() == 42

    class TestWithStandaloneMap:
        def test_works_with_standalone_map(self) -> None:
            result = map(Result.ok(5), fn[int, int](lambda x: x * 2))

            assert result.is_ok()
            assert result.unwrap() == 10

        def test_works_with_standalone_map_err(self) -> None:
            result = map_err(
                Result.err("failed"), fn[str, str](lambda e: f"Error: {e}")
            )

            assert result.is_err()
            assert result.unwrap_err() == "Error: failed"

    class TestComplexScenarios:
        def test_works_with_nested_structures(self) -> None:
            user: dict[str, str | int] = {"name": "Alice", "age": 30}
            assert (
                fn[dict[str, str | int], str | int](lambda user: user["name"])(user)
                == "Alice"
            )

        def test_works_with_multiple_parameters_via_closure(self) -> None:
            multiplier = 3
            assert fn[int, int](lambda x: x * multiplier)(5) == 15
            assert fn[int, int](lambda x: x * multiplier)(7) == 21

        def test_works_in_functional_pipeline(self) -> None:
            result = (
                Result.ok(5)
                .map(fn[int, int](lambda x: x * 2))
                .map(fn[int, str](lambda x: str(x)))
                .map(fn[str, str](lambda s: f"Result: {s}"))
            )

            assert result.is_ok()
            assert result.unwrap() == "Result: 10"

    class TestEdgeCases:
        def test_works_with_none(self) -> None:
            identity = fn[object, object](lambda x: x)
            result = identity(None)

            assert result is None

        def test_works_with_empty_string(self) -> None:
            upper = fn[str, str](lambda s: s.upper())

            assert upper("") == ""

        def test_works_with_zero(self) -> None:
            double = fn[int, int](lambda x: x * 2)

            assert double(0) == 0

        def test_works_with_boolean(self) -> None:
            negate = fn[bool, bool](lambda x: not x)

            assert negate(True) is False
            assert negate(False) is True
