from resultpy import TaggedError
from typing import TypeAlias, Union


class NotFoundError(TaggedError):
    __slots__ = ("id",)

    @property
    def tag(self) -> str:
        return "NotFoundError"

    def __init__(self, id: str) -> None:
        self.id = id
        super().__init__(f"Not found: {id}")


class ValidationError(TaggedError):
    __slots__ = ("field",)

    @property
    def tag(self) -> str:
        return "ValidationError"

    def __init__(self, field: str) -> None:
        self.field = field
        super().__init__(f"Invalid field: {field}")


class NetworkError(TaggedError):
    __slots__ = ("url",)

    @property
    def tag(self) -> str:
        return "NetworkError"

    def __init__(self, url: str) -> None:
        self.url = url
        super().__init__(f"Network error: {url}")


AppError: TypeAlias = Union[NotFoundError, ValidationError, NetworkError]


class TestTaggedError:
    class TestConstruction:
        def test_has_tag_descriminator(self) -> None:
            error = NotFoundError("123")
            assert error.tag == "NotFoundError"

            error = ValidationError("name")
            assert error.tag == "ValidationError"

            error = NetworkError("https://example.com")
            assert error.tag == "NetworkError"

        def test_sets_message(self) -> None:
            error = NotFoundError("123")
            assert error.message == "Not found: 123"

            error = ValidationError("name")
            assert error.message == "Invalid field: name"

            error = NetworkError("https://example.com")
            assert error.message == "Network error: https://example.com"

        def test_preserves_custom_properties(self) -> None:
            error = NotFoundError("123")
            assert error.id == "123"

            error = ValidationError("name")
            assert error.field == "name"

            error = NetworkError("https://example.com")
            assert error.url == "https://example.com"

        def test_chains_cause_via_dunder_cause(self) -> None:
            cause = ValueError("root cause")

            class ErrorWithCause(TaggedError):
                __slots__ = ()

                @property
                def tag(self) -> str:
                    return "ErrorWithCause"

                def __init__(self) -> None:
                    super().__init__("wrapper", cause)

            error = ErrorWithCause()
            assert error.__cause__ is cause
            assert str(error.__cause__) == "root cause"
            assert error.message == "wrapper"
