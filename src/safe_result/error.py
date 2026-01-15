from abc import ABC, abstractmethod
from typing import Optional, TypeVar, Dict, Callable, Union

"""
Copied from src/pyresult/error.py to preserve full API
"""

A = TypeVar("A")
E = TypeVar("E", bound="TaggedError")
F = TypeVar("F", bound="TaggedError")

_NOT_SET = object()


class TaggedError(ABC, Exception):
    __slots__ = ("_message", "_non_exception_cause")

    _message: str
    _non_exception_cause: Optional[object]

    @property
    @abstractmethod
    def tag(self) -> str:
        ...

    @property
    def message(self) -> str:
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
        if name == "__cause__":
            try:
                non_exception_cause = object.__getattribute__(self, "_non_exception_cause")
                if non_exception_cause is not _NOT_SET:
                    return non_exception_cause
            except AttributeError:
                pass
        return object.__getattribute__(self, name)

    def __str__(self) -> str:
        return self._message

    @staticmethod
    def is_error(value: object) -> bool:
        return isinstance(value, Exception)

    @staticmethod
    def is_tagged_error(value: object) -> bool:
        return isinstance(value, Exception) and isinstance(value, TaggedError)

    @staticmethod
    def match[A](
        error: "TaggedError",
        handlers: Dict[str, Callable[..., A]],
    ) -> A:
        tag = error.tag
        handler = handlers.get(tag)
        if handler is None:
            raise ValueError(f"No handler for error tag: {tag}")
        return handler(error)

    @staticmethod
    def match_partial[A](
        error: "TaggedError",
        handlers: Dict[str, Callable[..., A]],
        otherwise: Callable[..., A],
    ) -> A:
        tag = error.tag
        handler = handlers.get(tag)
        if handler is None:
            return otherwise(error)
        return handler(error)


class UnhandledException(TaggedError):
    @property
    def tag(self) -> str:
        return "UnhandledException"

    def __init__(self, cause: object) -> None:
        message = f"Unhandled exception: {cause}"
        super().__init__(message, cause)
