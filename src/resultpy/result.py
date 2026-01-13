from typing import (
    TypeVar,
    Generic,
    Literal,
    Callable,
    cast,
    Never,
    overload,
    Optional,
    Union,
)
from abc import ABC, abstractmethod

"""
Type variable for a generic type A
"""
A = TypeVar("A")

"""
Type variable for a transformed generic type B
"""
B = TypeVar("B")

"""
Type variable for a generic error type E
"""
E = TypeVar("E")

"""
Type variable for a transformed generic error type F
"""
F = TypeVar("F")


class Result(Generic[A, E], ABC):
    """
    Base class and namespace for Result types.

    Use Result[A, E] in type annotations.
    Use Result.ok(), Result.err(), Result.map() for utilities.

    Examples
    --------
    >>> def parse(s: str) -> Result[int, str]:
    ...     try:
    ...         return Result.ok(int(s))
    ...     except:
    ...         return Result.err(f"Invalid: {s}")
    """

    __slots__ = ()

    @property
    @abstractmethod
    def status(self) -> Literal["ok", "err"]:
        """Returns 'ok' or 'err'."""
        ...

    @staticmethod
    def ok(value: A) -> "Ok[A, Never]":
        """
        Creates successful result.

        Examples
        --------
        >>> Result.ok(42)  # Ok(42)
        """
        return Ok(value)

    @staticmethod
    def err(value: E) -> "Err[Never, E]":
        """
        Creates error result.

        Examples
        --------
        >>> Result.err("failed")  # Err("failed")
        """
        return Err(value)

    @abstractmethod
    def is_ok(self) -> bool:
        """Returns True if this is an Ok result."""
        ...

    @abstractmethod
    def is_err(self) -> bool:
        """Returns True if this is an Err result."""
        ...

    @abstractmethod
    def unwrap(self, message: Optional[str] = None) -> Union[A, object] | Never:
        """
        Unwraps the success value.

        Returns
        -------
        A
            Success value.
        """
        ...

    @abstractmethod
    def unwrap_or(self, fallback: B) -> Union[A, B]:
        """
        Unwraps the success value or returns the default value.

        Returns
        -------
        A
            Success value or default value.
        """
        ...


class Ok(Result[A, E]):
    """
    Successful result variant.

    Parameters
    ----------
    A : TypeVar
        Success value type.
    E : TypeVar
        Error type (phantom - for type unification).

    Examples
    --------
    >>> result = Ok(42)
    >>> result.value  # 42
    >>> result.status  # "ok"
    """

    __slots__ = ("value",)
    __match_args__ = ("value",)

    def __init__(self, value: A) -> None:
        self.value: A = value

    @property
    def status(self) -> Literal["ok"]:
        return "ok"

    def map(self, fn: Callable[[A], B]) -> "Ok[B, E]":
        """
        Transforms success value.

        Parameters
        ----------
        fn : Callable[[A], B]
            Transformation function.

        Returns
        -------
        Ok[B, E]
            Ok with transformed value.

        Examples
        --------
        >>> ok = Ok(2)
        >>> ok.map(lambda x: x * 2)
        Ok(4)
        """
        return Ok(fn(self.value))

    def mapErr(self, fn: Callable[[E], F]) -> "Ok[A, F]":
        """
        No-op for Ok. Returns self with new phantom error type.

        The error type E is not used at runtime in Ok, so this
        operation only changes the type signature without executing fn.

        Parameters
        ----------
        fn : Callable[[E], F]
            Transformation function (ignored, never called).

        Returns
        -------
        Ok[A, F]
            Self with updated phantom error type F.

        Examples
        --------
        >>> ok = Ok(2)
        >>> ok.mapErr(lambda e: str(e))  # Type changes E -> str
        Ok(2)

        Notes
        -----
        This is a type-level operation only. The function fn is never
        invoked because Ok does not contain an error value.
        """
        # SAFETY: E is phantom on Ok (not used at runtime).
        return cast("Ok[A, F]", self)

    def unwrap(self, message: Optional[str] = None) -> A:
        """
        Unwraps the success value.

        Returns
        -------
        A
            Success value.
        """
        return self.value

    def unwrap_err(self, message: Optional[str] = None) -> Never:
        """
        Throws because Ok has no error value.

        Raises
        ------
        Exception
            Always raises.
        """
        raise Exception(message or f"Unwrap_err called on Ok: {self.value!r}")

    def unwrap_or(self, fallback: object) -> A:
        """
        Unwraps the success value or returns the default value.

        Returns
        -------
        A
            Success value or default value.
        """
        return self.value

    def is_ok(self) -> bool:
        return True

    def is_err(self) -> bool:
        return False

    def __repr__(self) -> str:
        return f"Ok({self.value!r})"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Ok):
            return False
        return self.value == other.value

    def __hash__(self) -> int:
        return hash(("ok", self.value))

    def __str__(self) -> str:
        return f"Ok({self.value!r})"


class Err(Result[A, E]):
    """
    Error result variant.

    Parameters
    ----------
    A : TypeVar
        Success type (phantom - for type unification with Ok).
    E : TypeVar
        Error value type.

    Examples
    --------
    >>> result = Err("failed")
    >>> result.value  # "failed"
    >>> result.status  # "err"
    """

    __slots__ = ("value",)
    __match_args__ = ("value",)

    def __init__(self, value: E) -> None:
        self.value: E = value

    @property
    def status(self) -> Literal["err"]:
        return "err"

    def map(self, fn: Callable[[A], B]) -> "Err[B, E]":
        """
        No-op for Err. Returns self with new phantom success type.

        The success type A is not used at runtime in Err, so this
        operation only changes the type signature without executing fn.

        Parameters
        ----------
        fn : Callable[[A], B]
            Transformation function (ignored, never called).

        Returns
        -------
        Err[B, E]
            Self with updated phantom success type B.

        Examples
        --------
        >>> err = Err("error")
        >>> err.map(lambda x: x * 2)  # Type changes A -> int
        Err('error')

        Notes
        -----
        This is a type-level operation only. The function fn is never
        invoked because Err does not contain a success value.
        """
        # SAFETY: A is phantom on Err (not used at runtime).
        return cast("Err[B, E]", self)

    def mapErr(self, fn: Callable[[E], F]) -> "Err[A, F]":
        """
        Transforms error value.

        Parameters
        ----------
        fn : Callable[[E], F]
            Transformation function.

        Returns
        -------
        Err[A, F]
            Err with transformed error value.

        Examples
        --------
        >>> err = Err("error")
        >>> err.mapErr(lambda e: e.upper())
        Err("ERROR")
        """
        return Err(fn(self.value))

    def unwrap(self, message: Optional[str] = None) -> Never:
        """
        Throws because Err has no success value.

        Raises
        ------
        Exception
            Always raises.
        """
        raise Exception(message or f"Unwrap called on Err: {self.value!r}")

    def unwrap_err(self, message: Optional[str] = None) -> E:
        """
        Unwraps the error value.

        Returns
        -------
        E
            Error value.
        """
        return self.value

    def unwrap_or(self, fallback: B) -> B:
        """
        Unwraps the error value or returns the default value.

        Returns
        -------
        B
            Error value or default value.
        """
        return fallback

    def is_ok(self) -> bool:
        return False

    def is_err(self) -> bool:
        return True

    def __repr__(self) -> str:
        return f"Err({self.value!r})"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Err):
            return False
        return self.value == other.value

    def __hash__(self) -> int:
        return hash(("err", self.value))

    def __str__(self) -> str:
        return f"Err({self.value!r})"


# Module-level dual functions for map and map_err
# These support both DataFirst and DataLast calling patterns:
#   map(result, fn)  -> DataFirst
#   map(fn)(result)  -> DataLast
@overload
def map(result: Result[A, E], fn: Callable[[A], B]) -> Result[B, E]: ...


@overload
def map(result: Callable[[A], B]) -> Callable[[Result[A, E]], Result[B, E]]: ...


def map(result, fn=None):
    """
    Transforms success value, passes error through.

    Supports both DataFirst and DataLast calling patterns.

    Examples
    --------
    >>> map(Ok(2), lambda x: x * 2)  # Ok(4) - DataFirst
    >>> map(lambda x: x * 2)(Ok(2))  # Ok(4) - DataLast
    """
    if fn is None:
        return lambda r: r.map(result)
    return result.map(fn)


@overload
def map_err(result: Result[A, E], fn: Callable[[E], F]) -> Result[A, F]: ...


@overload
def map_err(result: Callable[[E], F]) -> Callable[[Result[A, E]], Result[A, F]]: ...


def map_err(result, fn=None):
    """
    Transforms error value, passes success through.

    Supports both DataFirst and DataLast calling patterns.

    Examples
    --------
    >>> map_err(Err("fail"), lambda e: e.upper())  # Err("FAIL") - DataFirst
    >>> map_err(lambda e: e.upper())(Err("fail"))  # Err("FAIL") - DataLast
    """
    if fn is None:
        return lambda r: r.mapErr(result)
    return result.mapErr(fn)
