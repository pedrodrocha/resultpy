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
    Coroutine,
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
    def ok[T](value: T) -> "Ok[T, Never]":
        """
        Creates successful result.

        Examples
        --------
        >>> Result.ok(42)  # Ok(42)
        """
        return Ok(value)

    @staticmethod
    def err[U](value: U) -> "Err[Never, U]":
        """
        Creates error result.

        Examples
        --------
        >>> Result.err("failed")  # Err("failed")
        """
        return Err(value)

    @abstractmethod
    def is_ok(self) -> bool: ...

    @abstractmethod
    def is_err(self) -> bool: ...

    @abstractmethod
    def map(self, fn: Callable[[A], B]) -> "Result[B, E]": ...

    @abstractmethod
    def map_err(self, fn: Callable[[E], F]) -> "Result[A, F]": ...

    @abstractmethod
    def unwrap(self, message: Optional[str] = None) -> Union[A, object] | Never: ...

    @abstractmethod
    def unwrap_or(self, fallback: B) -> Union[A, B]: ...

    @abstractmethod
    def unwrap_err(self, message: Optional[str] = None) -> E: ...

    @abstractmethod
    def tap(self, fn: Callable[[A], None]) -> "Result[A, E]": ...

    @abstractmethod
    async def tap_async(
        self, fn: Callable[[A], Coroutine[None, None, None]]
    ) -> "Result[A, E]": ...

    @abstractmethod
    def and_then(self, fn: Callable[[A], "Result[B, E]"]) -> "Result[B, E]": ...

    @abstractmethod
    async def and_then_async(
        self, fn: Callable[[A], Coroutine[None, None, "Result[B, E]"]]
    ) -> "Result[B, E]": ...


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

    def map_err(self, fn: Callable[[E], F]) -> "Ok[A, F]":
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
        >>> ok.map_err(lambda e: str(e))  # Type changes E -> str
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

    def unwrap_or(self, fallback: object) -> A:
        """
        Unwraps the success value or returns the default value.

        Returns
        -------
        A
            Success value or default value.
        """
        return self.value

    def unwrap_err(self, message: Optional[str] = None) -> Never:
        """
        Raises because Ok has no error value.

        Raises
        ------
        Exception
            Always raises.

        Examples
        --------
        >>> ok = Ok(42)
        >>> ok.unwrap_err()  # raises Exception
        """
        raise Exception(message or f"unwrap_err called on Ok: {self.value!r}")

    def tap(self, fn: Callable[[A], None]) -> "Ok[A, E]":
        """
        Runs side effect, returns self.

        Parameters
        ----------
        fn : Callable[[A], None]
            Side effect function.

        Returns
        -------
        Ok[A, E]
            Self with side effect applied.
        """
        fn(self.value)
        return self

    async def tap_async(
        self, fn: Callable[[A], Coroutine[None, None, None]]
    ) -> "Ok[A, E]":
        """
        Runs async side effect, returns self.

        Parameters
        ----------
        fn : Callable[[A], Coroutine[None, None, None]]
            Async side effect function.
        """
        await fn(self.value)
        return self

    def and_then(self, fn: Callable[[A], Result[B, E]]) -> "Result[B, E]":
        """
        Chains another result-producing function.

        Parameters
        ----------
        fn : Callable[[A], Result[B, E]]
            Result-producing function.

        Returns
        -------
        Result[B, E]
            Result of the chained function.

        Examples
        --------
        >>> result = Ok(2).and_then(lambda x: Ok(x * 3))
        Ok(6)

        >>> result = Ok(2).and_then(lambda x: Err("Error"))
        Err("Error")
        """
        return fn(self.value)

    async def and_then_async(
        self, fn: Callable[[A], Coroutine[None, None, Result[B, E]]]
    ) -> "Result[B, E]":
        """
        Chains another result-producing function.

        Parameters
        ----------
        fn : Callable[[A], Coroutine[None, None, Result[B, E]]]
            Result-producing function.

        Returns
        -------
        Result[B, E]
            Result of the chained function.

        Examples
        --------
        >>> result = Ok(2).and_then_async(lambda x: asyncio.sleep(1))
        Ok(2)

        >>> result = Ok(2).and_then_async(lambda x: Err("Error"))
        Err("Error")
        """
        return await fn(self.value)

    def is_ok(self) -> bool:
        return True

    def is_err(self) -> bool:
        return False

    def __repr__(self) -> str:
        return f"Ok({self.value!r})"

    def __hash__(self) -> int:
        return hash(("ok", self.value))

    def __str__(self) -> str:
        return f"Ok({self.value!r})"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Ok):
            return False
        other_ok = cast("Ok[A, E]", other)
        return self.value == other_ok.value


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

    def map_err(self, fn: Callable[[E], F]) -> "Err[A, F]":
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
        >>> err.map_err(lambda e: e.upper())
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

    def unwrap_or(self, fallback: B) -> B:
        """
        Unwraps the error value or returns the default value.

        Returns
        -------
        B
            Error value or default value.
        """
        return fallback

    def unwrap_err(self, message: Optional[str] = None) -> E:
        """
        Extracts the error value.

        Parameters
        ----------
        message : Optional[str]
            Unused (for API symmetry with Ok.unwrap_err).

        Returns
        -------
        E
            The error value.

        Examples
        --------
        >>> err = Err("failed")
        >>> err.unwrap_err()
        'failed'
        """
        return self.value

    def tap(self, fn: Callable[[A], None]) -> "Err[A, E]":
        """
        No-op for Err. Returns self.

        Parameters
        ----------
        fn : Callable[[A], None]
            Side effect function (ignored, never called).

        Returns
        -------
        Err[A, E]
            Self unchanged.
        """
        return self

    async def tap_async(
        self, fn: Callable[[A], Coroutine[None, None, None]]
    ) -> "Err[A, E]":
        """
        No-op for Err. Returns self.

        Parameters
        ----------
        fn : Callable[[A], Coroutine[None, None, None]]
            Side effect function (ignored, never called).
        """
        return self

    def and_then(self, fn: Callable[[A], Result[B, E]]) -> "Err[A, E]":
        """
        No-op for Err. Returns self.
        """
        return cast("Err[A, E]", self)

    async def and_then_async(
        self, fn: Callable[[A], Coroutine[None, None, Result[B, E]]]
    ) -> "Err[A, E]":
        """
        No-op for Err. Returns self.
        """
        return cast("Err[A, E]", self)

    def is_ok(self) -> bool:
        return False

    def is_err(self) -> bool:
        return True

    def __repr__(self) -> str:
        return f"Err({self.value!r})"

    def __hash__(self) -> int:
        return hash(("err", self.value))

    def __str__(self) -> str:
        return f"Err({self.value!r})"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Err):
            return False
        other_err = cast("Err[A, E]", other)
        return self.value == other_err.value


# ------------------------------------------------------------
# Module-level methods
# ------------------------------------------------------------
@overload
def map(result: Result[A, E], fn: Callable[[A], B]) -> Result[B, E]: ...


@overload
def map(result: Callable[[A], B]) -> Callable[[Result[A, E]], Result[B, E]]: ...


def map(
    result: Result[A, E] | Callable[[A], B],
    fn: Callable[[A], B] | None = None,
) -> Result[B, E] | Callable[[Result[A, E]], Result[B, E]]:
    """
    Transforms success value, passes error through.

    Supports both DataFirst and DataLast calling patterns.

    Examples
    --------
    >>> map(Ok(2), lambda x: x * 2)  # Ok(4) - DataFirst
    >>> map(lambda x: x * 2)(Ok(2))  # Ok(4) - DataLast
    """
    if fn is None:
        _fn = cast(Callable[[A], B], result)
        return lambda r: r.map(_fn)
    return cast(Result[A, E], result).map(fn)


@overload
def map_err(result: Result[A, E], fn: Callable[[E], F]) -> Result[A, F]: ...


@overload
def map_err(result: Callable[[E], F]) -> Callable[[Result[A, E]], Result[A, F]]: ...


def map_err(
    result: Result[A, E] | Callable[[E], F],
    fn: Callable[[E], F] | None = None,
) -> Result[A, F] | Callable[[Result[A, E]], Result[A, F]]:
    """
    Transforms error value, passes success through.

    Supports both DataFirst and DataLast calling patterns.

    Examples
    --------
    >>> map_err(Err("fail"), lambda e: e.upper())  # Err("FAIL") - DataFirst
    >>> map_err(lambda e: e.upper())(Err("fail"))  # Err("FAIL") - DataLast
    """
    if fn is None:
        _fn = cast(Callable[[E], F], result)
        return lambda r: r.map_err(_fn)
    return cast(Result[A, E], result).map_err(fn)


@overload
def tap(result: Result[A, E], fn: Callable[[A], None]) -> Result[A, E]: ...


@overload
def tap(result: Callable[[A], None]) -> Callable[[Result[A, E]], Result[A, E]]: ...


def tap(
    result: Result[A, E] | Callable[[A], None],
    fn: Callable[[A], None] | None = None,
) -> Result[A, E] | Callable[[Result[A, E]], Result[A, E]]:
    """
    Runs side effect on success value, returns result unchanged.

    Supports both DataFirst and DataLast calling patterns.

    Examples
    --------
    >>> tap(Ok(2), print)  # prints 2, returns Ok(2) - DataFirst
    >>> tap(print)(Ok(2))  # prints 2, returns Ok(2) - DataLast
    """
    if fn is None:
        _fn = cast(Callable[[A], None], result)
        return lambda r: r.tap(_fn)
    return cast(Result[A, E], result).tap(fn)


@overload
def tap_async(
    result: Result[A, E], fn: Callable[[A], Coroutine[None, None, None]]
) -> Coroutine[None, None, Result[A, E]]: ...


@overload
def tap_async(
    result: Callable[[A], Coroutine[None, None, None]],
) -> Callable[[Result[A, E]], Coroutine[None, None, Result[A, E]]]: ...


def tap_async(
    result: Result[A, E] | Callable[[A], Coroutine[None, None, None]],
    fn: Callable[[A], Coroutine[None, None, None]] | None = None,
) -> (
    Coroutine[None, None, Result[A, E]]
    | Callable[[Result[A, E]], Coroutine[None, None, Result[A, E]]]
):
    """
    Runs async side effect on success value, returns result unchanged.

    Supports both DataFirst and DataLast calling patterns.

    Examples
    --------
    >>> await tap_async(Ok(2), async_log)  # DataFirst
    >>> await tap_async(async_log)(Ok(2))  # DataLast
    """
    if fn is None:
        _fn = cast(Callable[[A], Coroutine[None, None, None]], result)
        return lambda r: r.tap_async(_fn)
    return cast(Result[A, E], result).tap_async(fn)


def unwrap(result: Result[A, E], message: Optional[str] = None) -> A:
    """
    Extracts the success value or raises an exception.

    Parameters
    ----------
    result : Result[A, E]
        The result to unwrap.
    message : Optional[str]
        Custom error message if unwrapping fails.

    Returns
    -------
    A
        The success value.

    Raises
    ------
    Exception
        If the result is an Err.

    Examples
    --------
    >>> unwrap(Ok(42))  # 42
    >>> unwrap(Err("fail"))  # raises Exception
    """
    return cast(A, result.unwrap(message))
