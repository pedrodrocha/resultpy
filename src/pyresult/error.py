from abc import ABC, abstractmethod
from typing import Optional, TypeVar, Dict, Callable, Union

"""
Type variable for a generic result type A
"""
A = TypeVar("A")

"""
Type variable for a generic error type E bounded to TaggedError
"""
E = TypeVar("E", bound="TaggedError")

"""
Type variable for an alternative generic error type F bounded to TaggedError
"""
F = TypeVar("F", bound="TaggedError")

"""
Sentinel value for indicating that a non-exception cause has not been set
"""
_NOT_SET = object()


class TaggedError(ABC, Exception):
    __slots__ = ("_message", "_non_exception_cause")

    _message: str
    _non_exception_cause: Optional[object]

    @property
    @abstractmethod
    def tag(self) -> str:
        """
        Returns the error tag for pattern matching.

        Returns
        -------
        str
            A unique string identifier for this error type.

        Examples
        --------
        >>> class NotFoundError(TaggedError):
        ...     @property
        ...     def tag(self) -> str: return "NotFoundError"
        ...     def __init__(self, id: str):
        ...         super().__init__(f"Not found: {id}")
        ...         self.id = id
        >>> error = NotFoundError("123")
        >>> error.tag
        'NotFoundError'
        """
        ...

    @property
    def message(self) -> str:
        """
        Returns the error message.

        Returns
        -------
        str
            The error message.

        Examples
        --------
        >>> class TestError(TaggedError):
        ...     @property
        ...     def tag(self) -> str: return "TestError"
        ...     def __init__(self, msg: str):
        ...         super().__init__(msg)
        >>> error = TestError("Something went wrong")
        >>> error.message
        'Something went wrong'
        """
        return self._message

    def __init__(self, message: str, cause: Optional[object] = None) -> None:
        super().__init__(message)
        self._message = message
        if isinstance(cause, BaseException):
            self._non_exception_cause = _NOT_SET
            self.__cause__ = cause  # Python's built-in cause chaining
        else:
            self._non_exception_cause = "None" if cause is None else cause
            self.__cause__ = None

    def __getattribute__(self, name: str) -> Union[BaseException, None, object]:
        """
        Override __getattribute__ to handle non-exception causes.
        """
        if name == "__cause__":
            try:
                non_exception_cause = object.__getattribute__(
                    self, "_non_exception_cause"
                )
                if non_exception_cause is not _NOT_SET:
                    return non_exception_cause
            except AttributeError:
                pass
        return object.__getattribute__(self, name)

    def __str__(self) -> str:
        return self._message

    @staticmethod
    def is_error(value: object) -> bool:
        """
        Type guard for any Exception instance.

        Parameters
        ----------
        value : object
            Value to check.

        Returns
        -------
        bool
            True if the value is an Exception instance, False otherwise.

        Examples
        --------
        >>> if TaggedError.is_error(value):
        ...     print(value.message)
        """
        return isinstance(value, Exception)

    @staticmethod
    def is_tagged_error(value: object) -> bool:
        """
        Type guard for TaggedError instances.

        Parameters
        ----------
        value : object
            Value to check.

        Returns
        -------
        bool
            True if the value is a TaggedError instance, False otherwise.

        Examples
        --------
        >>> if TaggedError.is_tagged_error(value):
        ...     print(value.tag)
        """
        return isinstance(value, Exception) and isinstance(value, TaggedError)

    @staticmethod
    def match[A](
        error: "TaggedError",
        handlers: Dict[str, Callable[..., A]],
    ) -> A:
        """
        Exhaustive pattern match on tagged error by tag string.

        Handlers can accept the specific error type (e.g., NotFoundError)
        and will receive an instance of that type at runtime.

        Parameters
        ----------
        error : TaggedError
            Error to match.
        handlers : Dict[str, Callable[..., A]]
            Dictionary mapping tag string to handler function.
            Handlers can accept the specific error type (e.g., NotFoundError)
            and will receive an instance of that type at runtime.

        Returns
        -------
        A
            Result of the matched handler function.

        Raises
        ------
        ValueError
            If no handler is found for the error's tag.

        Examples
        --------
        >>> class NotFoundError(TaggedError):
        ...     @property
        ...     def tag(self) -> str: return "NotFoundError"
        ...     def __init__(self, id: str):
        ...         super().__init__(f"Not found: {id}")
        ...         self.id = id
        >>> def handle_not_found(e: NotFoundError) -> str:
        ...     return f"Missing: {e.id}"
        >>> TaggedError.match(NotFoundError("123"), {"NotFoundError": handle_not_found})
        'Missing: 123'
        """
        tag = error.tag
        handler = handlers.get(tag)
        if handler is None:
            raise ValueError(f"No handler for error tag: {tag}")
        # Callable[..., A] accepts any arguments, so we can pass error directly
        # The runtime guarantee ensures the handler receives the correct type
        return handler(error)

    @staticmethod
    def match_partial[A](
        error: "TaggedError",
        handlers: Dict[str, Callable[..., A]],
        otherwise: Callable[..., A],
    ) -> A:
        """
        Partial pattern match on tagged error union.

        Returns the result of the handler or the otherwise function if no handler is found.

        Parameters
        ----------
        error : TaggedError
            Error to match.
        handlers : Dict[str, Callable[..., A]]
            Dictionary mapping tag string to handler function.
            Handlers can accept the specific error type (e.g., NotFoundError)
            and will receive an instance of that type at runtime.
        otherwise : Callable[..., A]
            Function to call if no handler is found for the error's tag.

        Returns
        -------
        A
            Result of matched handler or otherwise function.

        Examples
        --------
        >>> class NotFoundError(TaggedError):
        ...     @property
        ...     def tag(self) -> str: return "NotFoundError"
        ...     def __init__(self, id: str):
        ...         super().__init__(f"Not found: {id}")
        ...         self.id = id
        >>> class ValidationError(TaggedError):
        ...     @property
        ...     def tag(self) -> str: return "ValidationError"
        ...     def __init__(self, field: str):
        ...         super().__init__(f"Invalid: {field}")
        ...         self.field = field
        >>> error = ValidationError("name")
        >>> TaggedError.match_partial(error, {
        ...     "NotFoundError": lambda e: f"Missing: {e.id}",
        ...     "ValidationError": lambda e: f"Invalid: {e.field}",
        ... }, lambda e: f"Unknown error: {e.message}")
        'Invalid: name'
        """
        tag = error.tag
        handler = handlers.get(tag)
        if handler is None:
            return otherwise(error)
        # Callable[..., A] accepts any arguments, so we can pass error directly
        # The runtime guarantee ensures the handler receives the correct type
        return handler(error)


class UnhandledException(TaggedError):
    @property
    def tag(self) -> str:
        return "UnhandledException"

    def __init__(self, cause: object) -> None:
        message = f"Unhandled exception: {cause}"
        super().__init__(message, cause)
