from abc import ABC, abstractmethod
from typing import Optional, TypeVar, Dict, Callable

"""
Type variable for a generic type A
"""
A = TypeVar("A")

"""
Type variable for a generic type E bounded to TaggedError
"""
E = TypeVar("E", bound="TaggedError")


class TaggedError(ABC, Exception):
    __slots__ = ("_message", "_cause")

    @property
    @abstractmethod
    def _tag(self) -> str: ...

    @property
    def message(self) -> str:
        return self.message

    def __init__(self, message: str, cause: Optional[Exception] = None) -> None:
        super().__init__(message)
        self._message = message
        self._cause = cause

    def __str__(self) -> str:
        if self._cause is not None:
            return f"{self._message}\nCaused by: {self._cause}"
        return self._message

    @staticmethod
    def is_error(value: object) -> bool:
        """
        Type guard for any Exception instance.

        Example:
            if TaggedError.is_error(value):
                print(value.message)
        """
        return isinstance(value, Exception)

    @staticmethod
    def is_tagged_error(value: object) -> bool:
        """
        Type guard for TaggedError instances.
        Example:
            if TaggedError.is_tagged_error(value):
                print(value._tag)
        """
        return (
            isinstance(value, Exception)
            and hasattr(value, "_tag")
            and isinstance(getattr(value, "_tag"), str)
        )

    @staticmethod
    def match(error: E, handlers: Dict[str, Callable[[E], A]]) -> A:
        """
        Exhaustive pattern match on tagged error union.
        Requires handlers for all _tag variants.

        Parameters
        ----------
        error : E
            Error to match.
        handlers : Dict[str, Callable[[E], T]]
            Dict mapping _tag to handler function.

        Returns
        -------
        T
            Result of matched handler.

        Examples
        --------
        >>> TaggedError.match(error, {
        ...     "NotFoundError": lambda e: f"Missing: {e.id}",
        ...     "ValidationError": lambda e: f"Invalid: {e.field}",
        ... })

        Raises
        ------
        ValueError
            If no handler exists for the error's _tag.
        """
        tag = error._tag
        handler = handlers.get(tag)
        if handler is None:
            raise ValueError(f"No handler for error tag: {tag}")
        return handler(error)

    @staticmethod
    def match_partial(
        error: E, handlers: Dict[str, Callable[[E], A]], otherwise: Callable[[E], A]
    ) -> A:
        """
        Partial pattern match on tagged error union.
        Requires handlers for all _tag variants.
        Returns the result of the handler or the otherwise function if no handler is found.

        Parameters
        ----------
        error : E
            Error to match.
        handlers : Dict[str, Callable[[E], A]]
            Dict mapping _tag to handler function.
        otherwise : Callable[[E], A]
            Function to call if no handler is found.

        Returns
        -------
        A
            Result of matched handler or otherwise function.

        Examples
        --------
        >>> TaggedError.match_partial(error, {
        ...     "NotFoundError": lambda e: f"Missing: {e.id}",
        ...     "ValidationError": lambda e: f"Invalid: {e.field}",
        ... }, lambda e: f"Unknown error: {e.message}")
        """
        tag = error._tag
        handler = handlers.get(tag)
        if handler is None:
            return otherwise(error)
        return handler(error)
