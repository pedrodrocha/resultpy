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
    TypedDict,
    TypeAlias,
)
from abc import ABC, abstractmethod

"""
Type variable for method parameters
"""
T = TypeVar("T")

"""
Type variable for a generic type A
"""
A = TypeVar("A", covariant=True)

"""
Type variable for a transformed generic type B
"""
B = TypeVar("B")

"""
Type variable for a generic error type E
"""
E = TypeVar("E", covariant=True)

"""
Type variable for method error parameter U
"""
U = TypeVar("U")

"""
Type variable for a generic type G, contravariant
"""
G = TypeVar("G", contravariant=True)

"""
Type variable for a transformed generic error type F
"""
F = TypeVar("F")


class Matcher(TypedDict, Generic[A, B, E, F]):
    """
    TypedDict for matching Result variants.

    Keys
    ----
    ok : Callable[[A], B]
        Function to call if the result is Ok.
    err : Callable[[E], F]
        Function to call if the result is Err.
    """

    ok: Callable[[A], B]
    err: Callable[[E], F]


class SerializedOk(TypedDict, Generic[A]):
    """
    Serialized representation of an Ok result.

    Keys
    ----
    status : Literal["ok"]
        Indicates the result is Ok.
    value : A
        The success value.
    """

    status: Literal["ok"]
    value: A


class SerializedErr(TypedDict, Generic[E]):
    """
    Serialized representation of an Err result.

    Keys
    ----
    status : Literal["err"]
        Indicates the result is Err.
    value : E
        The error value.
    """

    status: Literal["err"]
    value: E


SerializedResult: TypeAlias = Union[SerializedOk[A], SerializedErr[E]]


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
        """
        Returns the status of the result.

        Returns
        -------
        Literal["ok", "err"]
            'ok' for successful results, 'err' for error results.
        """
        ...

    @staticmethod
    def ok(value: T) -> "Ok[T, Never]":
        """
        Creates a successful result.

        Parameters
        ----------
        value : T
            The success value.

        Returns
        -------
        Ok[T, Never]
            A successful result containing the value.

        Examples
        --------
        >>> Result.ok(42)
        Ok(42)
        """
        return Ok(value)

    @staticmethod
    def err(value: U) -> "Err[Never, U]":
        """
        Creates an error result.

        Parameters
        ----------
        value : U
            The error value.

        Returns
        -------
        Err[Never, U]
            An error result containing the error value.

        Examples
        --------
        >>> Result.err(ValueError("failed"))
        Err(ValueError('failed'))
        """
        return Err(value)

    @abstractmethod
    def is_ok(self) -> bool:
        """
        Checks if the result is Ok.

        Returns
        -------
        bool
            True if the result is Ok, False if it is Err.

        Examples
        --------
        >>> Result.ok(42).is_ok()
        True
        >>> Result.err("error").is_ok()
        False
        """
        ...

    @abstractmethod
    def is_err(self) -> bool:
        """
        Checks if the result is Err.

        Returns
        -------
        bool
            True if the result is Err, False if it is Ok.

        Examples
        --------
        >>> Result.err("error").is_err()
        True
        >>> Result.ok(42).is_err()
        False
        """
        ...

    @abstractmethod
    def map(self, fn: Callable[[A], B]) -> "Result[B, E]":
        """
        Transforms the success value if Ok, passes through if Err.

        Parameters
        ----------
        fn : Callable[[A], B]
            Transformation function to apply to the success value.

        Returns
        -------
        Result[B, E]
            Ok with transformed value if Ok, Err unchanged if Err.

        Examples
        --------
        >>> Ok(2).map(lambda x: x * 2)
        Ok(4)
        >>> Err("error").map(lambda x: x * 2)
        Err('error')
        """
        ...

    @abstractmethod
    def map_err(self, fn: Callable[[E], F]) -> "Result[A, F]":
        """
        Transforms the error value if Err, passes through if Ok.

        Parameters
        ----------
        fn : Callable[[E], F]
            Transformation function to apply to the error value.

        Returns
        -------
        Result[A, F]
            Err with transformed error if Err, Ok unchanged if Ok.

        Examples
        --------
        >>> Err(ValueError("invalid")).map_err(lambda e: RuntimeError(str(e)))
        Err(RuntimeError('invalid'))
        >>> Ok(42).map_err(lambda e: str(e))
        Ok(42)
        """
        ...

    @abstractmethod
    def unwrap(self, message: Optional[str] = None) -> Union[A, object] | Never:
        """
        Extracts the success value or raises an exception.

        Parameters
        ----------
        message : Optional[str], default None
            Custom error message to use if unwrapping fails.

        Returns
        -------
        A
            The success value if Ok.

        Raises
        ------
        Exception
            If the result is Err.

        Examples
        --------
        >>> Result.ok(42).unwrap()
        42
        >>> Result.err("error").unwrap()  # raises Exception
        """
        ...

    @abstractmethod
    def unwrap_or(self, fallback: B) -> Union[A, B]:
        """
        Extracts the success value or returns a fallback.

        Parameters
        ----------
        fallback : B
            Value to return if the result is Err.

        Returns
        -------
        A | B
            The success value if Ok, otherwise the fallback.

        Examples
        --------
        >>> Result.ok(42).unwrap_or(0)
        42
        >>> Result.err("error").unwrap_or(0)
        0
        """
        ...

    @abstractmethod
    def unwrap_err(self, message: Optional[str] = None) -> E:
        """
        Extracts the error value or raises an exception.

        Parameters
        ----------
        message : Optional[str], default None
            Custom error message to use if unwrapping fails.

        Returns
        -------
        E
            The error value if Err.

        Raises
        ------
        Exception
            If the result is Ok.

        Examples
        --------
        >>> Result.err("failed").unwrap_err()
        'failed'
        >>> Result.ok(42).unwrap_err()  # raises Exception
        """
        ...

    @abstractmethod
    def tap(self, fn: Callable[[A], None]) -> "Result[A, E]":
        """
        Runs a side effect on the success value and returns the result unchanged.

        Parameters
        ----------
        fn : Callable[[A], None]
            Side effect function to call with the success value.

        Returns
        -------
        Result[A, E]
            The original result unchanged.

        Examples
        --------
        >>> Ok(42).tap(print)  # prints 42, returns Ok(42)
        Ok(42)
        >>> Err("error").tap(print)  # does nothing, returns Err('error')
        Err('error')
        """
        ...

    @abstractmethod
    async def tap_async(
        self, fn: Callable[[A], Coroutine[None, None, None]]
    ) -> "Result[A, E]":
        """
        Runs an async side effect on the success value and returns the result unchanged.

        Parameters
        ----------
        fn : Callable[[A], Coroutine[None, None, None]]
            Async side effect function to call with the success value.

        Returns
        -------
        Result[A, E]
            The original result unchanged.

        Examples
        --------
        >>> async def log_value(x): print(x)
        >>> await Ok(42).tap_async(log_value)  # prints 42, returns Ok(42)
        Ok(42)
        """
        ...

    @abstractmethod
    def and_then(self, fn: Callable[[A], "Result[B, F]"]) -> "Result[B, E | F]":
        """
        Chains another result-producing function.

        Parameters
        ----------
        fn : Callable[[A], Result[B, F]]
            Function that takes the success value and returns a Result.

        Returns
        -------
        Result[B, E]
            The result of the chained function if Ok, otherwise the original Err.

        Examples
        --------
        >>> Ok(2).and_then(lambda x: Ok(x * 3))
        Ok(6)
        >>> Ok(2).and_then(lambda x: Err("error") if x < 0 else Ok(x))
        Ok(2)
        >>> Err("error").and_then(lambda x: Ok(x * 3))
        Err('error')
        """
        ...

    @abstractmethod
    async def and_then_async(
        self, fn: Callable[[A], Coroutine[None, None, "Result[B, E]"]]
    ) -> "Result[B, E]":
        """
        Chains another async result-producing function.

        Parameters
        ----------
        fn : Callable[[A], Coroutine[None, None, Result[B, E]]]
            Async function that takes the success value and returns a Result.

        Returns
        -------
        Result[B, E]
            The result of the chained function if Ok, otherwise the original Err.

        Examples
        --------
        >>> async def async_double(x): return Ok(x * 2)
        >>> await Ok(2).and_then_async(async_double)
        Ok(4)
        """
        ...

    @abstractmethod
    def match(self, cases: Matcher[A, B, E, F]) -> B | F:
        """
        Pattern matches on the result, handling both Ok and Err cases.

        Parameters
        ----------
        cases : Matcher[A, B, E, F]
            Dictionary with 'ok' and 'err' handler functions.

        Returns
        -------
        B | F
            The result of the appropriate handler function.

        Examples
        --------
        >>> Ok(42).match({"ok": lambda x: x * 2, "err": lambda e: 0})
        84
        >>> Err("error").match({"ok": lambda x: x * 2, "err": lambda e: f"Failed: {e}"})
        'Failed: error'
        """
        ...

    @abstractmethod
    def serialize(self) -> SerializedResult[A, E]:
        """
        Serializes the Result into a dictionary representation.

        Returns
        -------
        SerializedResult[A, E]
            A dictionary representing the Result.

        Examples
        --------
        >>> Result.ok(42).serialize()
        {'status': 'ok', 'value': 42}
        >>> Result.err("error").serialize()
        {'status': 'err', 'value': 'error'}
        """
        ...

    @staticmethod
    def hydrate(data: object) -> "Result[object, object] | None":
        """
        Dynamic deserialization of a dictionary into a Result instance.

        Reconstructs a Result from its serialized form without type information.
        This is the inverse of serialize(): it takes a serialized Result and
        returns the appropriate Ok or Err instance with the raw values.

        Parameters
        ----------
        data : object
            The serialized data. Must be a dict with keys 'status' and 'value',
            where 'status' is either 'ok' or 'err'.

        Returns
        -------
        Result[object, object] | None
            Ok(value) or Err(value) if the shape is valid, otherwise None.
        """

        def is_serialized_result(d: object) -> bool:
            if not isinstance(d, dict):
                return False
            if "status" not in d or "value" not in d:
                return False
            if d["status"] not in ("ok", "err"):
                return False
            return True

        if not is_serialized_result(data):
            return None

        serialized = cast(dict[str, object], data)
        if serialized["status"] == "ok":
            return Result.ok(serialized["value"])
        else:  # status == "err"
            return Result.err(serialized["value"])

    @staticmethod
    def hydrate_as[T, U](
        data: object,
        *,
        ok: Callable[[object], T],
        err: Callable[[object], U],
    ) -> "Result[T, U] | None":
        """
        Typed deserialization of a dictionary into a Result instance.

        Takes a serialized Result dictionary and applies decoder functions
        to the value, enabling strongly-typed deserialization. This follows
        Rust's Serde pattern where decoders transform raw object data into
        properly-typed values.

        Parameters
        ----------
        data : object
            The data to deserialize. Should be a dictionary with 'status'
            and 'value' keys, where 'status' is either 'ok' or 'err'.
        ok : Callable[[object], T]
            Decoder function that transforms the raw value into type T
            when status is 'ok'. Should raise an exception if decoding fails.
        err : Callable[[object], U]
            Decoder function that transforms the raw value into type U
            when status is 'err'. Should raise an exception if decoding fails.

        Returns
        -------
        Result[T, U] | None
            A strongly-typed Result instance if the data is valid and decoders
            succeed, None if validation fails or a decoder raises an exception.

        Examples
        --------
        >>> def decode_int(x: object) -> int:
        ...     if isinstance(x, int):
        ...         return x
        ...     raise ValueError(f"Expected int, got {type(x)}")
        >>> Result.hydrate_as(
        ...     {'status': 'ok', 'value': 42},
        ...     ok=decode_int,
        ...     err=str,
        ... )
        Ok(42)
        >>> Result.hydrate_as(
        ...     {'status': 'err', 'value': 'error'},
        ...     ok=decode_int,
        ...     err=str,
        ... )
        Err('error')
        """

        def is_result(d: object) -> bool:
            if not isinstance(d, dict):
                return False
            if "status" not in d or "value" not in d:
                return False
            if d["status"] not in ("ok", "err"):
                return False
            return True

        if not is_result(data):
            return None

        serialized = cast(dict[str, object], data)

        try:
            if serialized["status"] == "ok":
                decoded_value = ok(serialized["value"])
                return Result.ok(decoded_value)
            else:  # status == "err"
                decoded_error = err(serialized["value"])
                return Result.err(decoded_error)
        except Exception as e:
            # Panic - deserialization failed
            return Result.err(cast(U, e))


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

        Parameters
        ----------
        message : Optional[str], default None
            Unused (for API symmetry with Err.unwrap).

        Returns
        -------
        A
            The success value.

        Examples
        --------
        >>> Ok(42).unwrap()
        42
        """
        return self.value

    def unwrap_or(self, fallback: object) -> A:
        """
        Unwraps the success value (fallback is unused for Ok).

        Parameters
        ----------
        fallback : object
            Unused (for API symmetry with Err.unwrap_or).

        Returns
        -------
        A
            The success value.

        Examples
        --------
        >>> Ok(42).unwrap_or(0)
        42
        """
        return self.value

    def unwrap_err(self, message: Optional[str] = None) -> Never:
        """
        Raises an exception because Ok has no error value.

        Parameters
        ----------
        message : Optional[str], default None
            Custom error message, or default message if None.

        Raises
        ------
        Exception
            Always raises when called on Ok.

        Examples
        --------
        >>> Ok(42).unwrap_err()  # raises Exception
        """
        raise Exception(message or f"unwrap_err called on Ok: {self.value!r}")

    def tap(self, fn: Callable[[A], None]) -> "Ok[A, E]":
        """
        Runs a side effect on the success value and returns the result unchanged.

        Parameters
        ----------
        fn : Callable[[A], None]
            Side effect function to call with the success value.

        Returns
        -------
        Ok[A, E]
            Self unchanged.

        Examples
        --------
        >>> Ok(42).tap(print)  # prints 42, returns Ok(42)
        Ok(42)
        """
        fn(self.value)
        return self

    async def tap_async(
        self, fn: Callable[[A], Coroutine[None, None, None]]
    ) -> "Ok[A, E]":
        """
        Runs an async side effect on the success value and returns the result unchanged.

        Parameters
        ----------
        fn : Callable[[A], Coroutine[None, None, None]]
            Async side effect function to call with the success value.

        Returns
        -------
        Ok[A, E]
            Self unchanged.

        Examples
        --------
        >>> async def log_value(x): print(x)
        >>> await Ok(42).tap_async(log_value)  # prints 42, returns Ok(42)
        Ok(42)
        """
        await fn(self.value)
        return self

    def and_then(self, fn: Callable[[A], "Result[B, F]"]) -> "Result[B, E | F]":
        """
        Chains another result-producing function.

        Parameters
        ----------
        fn : Callable[[A], Result[B, F]]
            Function that takes the success value and returns a Result.

        Returns
        -------
        Result[B, E | F]
            The result of the chained function.

        Examples
        --------
        >>> Ok(2).and_then(lambda x: Ok(x * 3))
        Ok(6)
        >>> Ok(2).and_then(lambda x: Err(ValueError("Error")) if x < 0 else Ok(x))
        Ok(2)
        """
        return fn(self.value)

    async def and_then_async(
        self, fn: Callable[[A], Coroutine[None, None, Result[B, F]]]
    ) -> "Result[B, E | F]":
        """
        Chains another async result-producing function.

        Parameters
        ----------
        fn : Callable[[A], Coroutine[None, None, Result[B, F]]]
            Async function that takes the success value and returns a Result.

        Returns
        -------
        Result[B, E | F]
            The result of the chained function.

        Examples
        --------
        >>> async def async_double(x): return Ok(x * 2)
        >>> await Ok(2).and_then_async(async_double)
        Ok(4)
        """
        return await fn(self.value)

    def match(self, cases: Matcher[A, B, E, F]) -> B | F:
        """
        Pattern matches on the result, handling both Ok and Err cases.

        Parameters
        ----------
        cases : Matcher[A, B, E, F]
            Dictionary with 'ok' and 'err' handler functions.

        Returns
        -------
        B | F
            The result of the appropriate handler function.

        Examples
        --------
        >>> Ok(42).match({"ok": lambda x: x * 2, "err": lambda e: 0})
        84
        >>> Ok(42).match({"ok": lambda x: f"Got {x}", "err": lambda e: f"Failed: {e}"})
        'Got 42'
        """
        return cases["ok"](self.value)

    def serialize(self) -> SerializedOk[A]:
        return SerializedOk(status="ok", value=self.value)

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
        Raises an exception because Err has no success value.

        Parameters
        ----------
        message : Optional[str], default None
            Custom error message, or default message if None.

        Raises
        ------
        Exception
            Always raises when called on Err.

        Examples
        --------
        >>> Err("error").unwrap()  # raises Exception
        """
        raise Exception(message or f"Unwrap called on Err: {self.value!r}")

    def unwrap_or(self, fallback: B) -> B:
        """
        Returns the fallback value because Err has no success value.

        Parameters
        ----------
        fallback : B
            Value to return.

        Returns
        -------
        B
            The fallback value.

        Examples
        --------
        >>> Err("error").unwrap_or(0)
        0
        """
        return fallback

    def unwrap_err(self, message: Optional[str] = None) -> E:
        """
        Extracts the error value.

        Parameters
        ----------
        message : Optional[str], default None
            Unused (for API symmetry with Ok.unwrap_err).

        Returns
        -------
        E
            The error value.

        Examples
        --------
        >>> Err("failed").unwrap_err()
        'failed'
        >>> Err(ValueError("invalid")).unwrap_err()
        ValueError('invalid')
        """
        return self.value

    def tap(self, fn: Callable[[A], None]) -> "Err[A, E]":
        """
        No-op for Err. Returns self unchanged.

        Parameters
        ----------
        fn : Callable[[A], None]
            Side effect function (ignored, never called).

        Returns
        -------
        Err[A, E]
            Self unchanged.

        Examples
        --------
        >>> Err("error").tap(print)  # does nothing, returns Err('error')
        Err('error')
        """
        return self

    async def tap_async(
        self, fn: Callable[[A], Coroutine[None, None, None]]
    ) -> "Err[A, E]":
        """
        No-op for Err. Returns self unchanged.

        Parameters
        ----------
        fn : Callable[[A], Coroutine[None, None, None]]
            Side effect function (ignored, never called).

        Returns
        -------
        Err[A, E]
            Self unchanged.

        Examples
        --------
        >>> async def log_value(x): print(x)
        >>> await Err("error").tap_async(log_value)  # does nothing, returns Err('error')
        Err('error')
        """
        return self

    def and_then(self, fn: Callable[[A], Result[B, F]]) -> "Err[A, E]":
        """
        No-op for Err. Returns self unchanged.

        Parameters
        ----------
        fn : Callable[[A], Result[B, F]]
            Function (ignored, never called).

        Returns
        -------
        Err[A, E]
            Self unchanged.

        Examples
        --------
        >>> Err("error").and_then(lambda x: Ok(x * 2))
        Err('error')
        """
        return cast("Err[A, E]", self)

    async def and_then_async(
        self, fn: Callable[[A], Coroutine[None, None, Result[B, F]]]
    ) -> "Err[A, E]":
        """
        No-op for Err. Returns self unchanged.

        Parameters
        ----------
        fn : Callable[[A], Coroutine[None, None, Result[B, F]]]
            Async function (ignored, never called).

        Returns
        -------
        Err[A, E]
            Self unchanged.

        Examples
        --------
        >>> async def async_double(x): return Ok(x * 2)
        >>> await Err("error").and_then_async(async_double)
        Err('error')
        """
        return cast("Err[A, E]", self)

    def match(self, cases: Matcher[A, B, E, F]) -> B | F:
        """
        Pattern matches on the result, handling both Ok and Err cases.

        Parameters
        ----------
        cases : Matcher[A, B, E, F]
            Dictionary with 'ok' and 'err' handler functions.

        Returns
        -------
        B | F
            The result of the appropriate handler function.

        Examples
        --------
        >>> Err("error").match({"ok": lambda x: x * 2, "err": lambda e: f"Failed: {e}"})
        'Failed: error'
        >>> Err(ValueError("invalid")).match({"ok": lambda x: x, "err": lambda e: str(e)})
        'invalid'
        """
        return cases["err"](self.value)

    def serialize(self) -> SerializedErr[E]:
        value = str(self.value) if isinstance(self.value, Exception) else self.value
        return SerializedErr(status="err", value=value)

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
    Transforms the success value if Ok, passes through if Err.

    Supports both data-first and data-last calling patterns.

    Parameters
    ----------
    result : Result[A, E] | Callable[[A], B]
        Either a Result to transform, or a function for data-last style.
    fn : Callable[[A], B] | None, default None
        Transformation function (required for data-first style).

    Returns
    -------
    Result[B, E] | Callable[[Result[A, E]], Result[B, E]]
        Transformed result, or a function for data-last style.

    Examples
    --------
    >>> map(Ok(2), lambda x: x * 2)  # Data-first: Ok(4)
    Ok(4)
    >>> map(lambda x: x + 1)(Ok(2))  # Data-last: Ok(3)
    Ok(3)
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
    Transforms the error value if Err, passes through if Ok.

    Supports both data-first and data-last calling patterns.

    Parameters
    ----------
    result : Result[A, E] | Callable[[E], F]
        Either a Result to transform, or a function for data-last style.
    fn : Callable[[E], F] | None, default None
        Transformation function (required for data-first style).

    Returns
    -------
    Result[A, F] | Callable[[Result[A, E]], Result[A, F]]
        Transformed result, or a function for data-last style.

    Examples
    --------
    >>> map_err(Err(ValueError("invalid")), lambda e: RuntimeError(str(e)))  # Data-first
    Err(RuntimeError('invalid'))
    >>> map_err(lambda e: RuntimeError(str(e)))(Err(ValueError("invalid")))  # Data-last
    Err(RuntimeError('invalid'))
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
    Runs a side effect on the success value and returns the result unchanged.

    Supports both data-first and data-last calling patterns.

    Parameters
    ----------
    result : Result[A, E] | Callable[[A], None]
        Either a Result to tap, or a function for data-last style.
    fn : Callable[[A], None] | None, default None
        Side effect function (required for data-first style).

    Returns
    -------
    Result[A, E] | Callable[[Result[A, E]], Result[A, E]]
        The original result unchanged, or a function for data-last style.

    Examples
    --------
    >>> tap(Ok(2), print)  # Data-first: prints 2, returns Ok(2)
    Ok(2)
    >>> tap(print)(Ok(2))  # Data-last: prints 2, returns Ok(2)
    Ok(2)
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
    Runs an async side effect on the success value and returns the result unchanged.

    Supports both data-first and data-last calling patterns.

    Parameters
    ----------
    result : Result[A, E] | Callable[[A], Coroutine[None, None, None]]
        Either a Result to tap, or a function for data-last style.
    fn : Callable[[A], Coroutine[None, None, None]] | None, default None
        Async side effect function (required for data-first style).

    Returns
    -------
    Coroutine[None, None, Result[A, E]] | Callable[[Result[A, E]], Coroutine[None, None, Result[A, E]]]
        The original result unchanged, or a function for data-last style.

    Examples
    --------
    >>> async def log_value(x): print(x)
    >>> await tap_async(Ok(2), log_value)  # Data-first: prints 2, returns Ok(2)
    Ok(2)
    >>> await tap_async(log_value)(Ok(2))  # Data-last: prints 2, returns Ok(2)
    Ok(2)
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
    message : Optional[str], default None
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
    >>> unwrap(Ok(42))
    42
    >>> unwrap(Ok(42), "custom message")  # returns 42
    42
    >>> unwrap(Err("fail"))  # raises Exception
    """
    return cast(A, result.unwrap(message))


@overload
def and_then(
    result: Result[A, E], fn: Callable[[A], Result[B, F]]
) -> Result[B, E | F]: ...


@overload
def and_then(
    result: Callable[[A], Result[B, F]],
) -> Callable[[Result[A, E]], Result[B, E | F]]: ...


def and_then(
    result: Result[A, E] | Callable[[A], Result[B, F]],
    fn: Callable[[A], Result[B, F]] | None = None,
) -> Result[B, E | F] | Callable[[Result[A, E]], Result[B, E | F]]:
    """
    Chains another result-producing function.

    Supports both data-first and data-last calling patterns.

    Parameters
    ----------
    result : Result[A, E] | Callable[[A], Result[B, F]]
        Either a Result to chain, or a function for data-last style.
    fn : Callable[[A], Result[B, F]] | None, default None
        Function that takes the success value and returns a Result (required for data-first style).

    Returns
    -------
    Result[B, E | F] | Callable[[Result[A, E]], Result[B, E | F]]
        The result of the chained function, or a function for data-last style.

    Examples
    --------
    >>> and_then(Ok(2), lambda x: Ok(x * 3))  # Data-first: Ok(6)
    Ok(6)
    >>> and_then(lambda x: Ok(x * 3))(Ok(2))  # Data-last: Ok(6)
    Ok(6)
    """
    if fn is None:
        _fn = cast(Callable[[A], Result[B, F]], result)
        return lambda r: cast(
            Result[B, E | F], r.and_then(cast(Callable[[A], Result[B, E]], _fn))
        )
    return cast(
        Result[B, E | F],
        cast(Result[A, E], result).and_then(cast(Callable[[A], Result[B, E]], fn)),
    )


@overload
def and_then_async(
    result: Result[A, E], fn: Callable[[A], Coroutine[None, None, Result[B, F]]]
) -> Coroutine[None, None, Result[B, E | F]]: ...


@overload
def and_then_async(
    result: Callable[[A], Coroutine[None, None, Result[B, F]]],
) -> Callable[[Result[A, E]], Coroutine[None, None, Result[B, E | F]]]: ...


def and_then_async(
    result: Result[A, E] | Callable[[A], Coroutine[None, None, Result[B, F]]],
    fn: Callable[[A], Coroutine[None, None, Result[B, F]]] | None = None,
) -> (
    Coroutine[None, None, Result[B, E | F]]
    | Callable[[Result[A, E]], Coroutine[None, None, Result[B, E | F]]]
):
    """
    Chains another async result-producing function.

    Supports both data-first and data-last calling patterns.

    Parameters
    ----------
    result : Result[A, E] | Callable[[A], Coroutine[None, None, Result[B, F]]]
        Either a Result to chain, or a function for data-last style.
    fn : Callable[[A], Coroutine[None, None, Result[B, F]]] | None, default None
        Async function that takes the success value and returns a Result (required for data-first style).

    Returns
    -------
    Coroutine[None, None, Result[B, E | F]] | Callable[[Result[A, E]], Coroutine[None, None, Result[B, E | F]]]
        The result of the chained function, or a function for data-last style.

    Examples
    --------
    >>> async def async_double(x): return Ok(x * 2)
    >>> await and_then_async(Ok(2), async_double)  # Data-first: Ok(4)
    Ok(4)
    >>> await and_then_async(async_double)(Ok(2))  # Data-last: Ok(4)
    Ok(4)
    """
    if fn is None:
        _fn = cast(Callable[[A], Coroutine[None, None, Result[B, F]]], result)
        return lambda r: cast(
            Coroutine[None, None, Result[B, E | F]],
            r.and_then_async(
                cast(Callable[[A], Coroutine[None, None, Result[B, E]]], _fn)
            ),
        )
    return cast(
        Coroutine[None, None, Result[B, E | F]],
        cast(Result[A, E], result).and_then_async(
            cast(Callable[[A], Coroutine[None, None, Result[B, E]]], fn)
        ),
    )


@overload
def match(result: Result[A, E], handlers: Matcher[A, B, E, B]) -> B: ...


@overload
def match(
    result: Matcher[A, B, E, B],
) -> Callable[[Result[A, E]], B]: ...


def match(
    result: Result[A, E] | Matcher[A, B, E, B],
    handlers: Matcher[A, B, E, B] | None = None,
) -> B | Callable[[Result[A, E]], B]:
    """
    Pattern matches on a Result, handling both Ok and Err cases.

    Supports both data-first and data-last calling patterns.

    Parameters
    ----------
    result : Result[A, E] | Matcher[A, B, E, B]
        Either a Result to match, or a Matcher for data-last style.
    handlers : Matcher[A, B, E, B] | None, default None
        Dictionary with 'ok' and 'err' handler functions (required for data-first style).

    Returns
    -------
    B | Callable[[Result[A, E]], B]
        The result of the appropriate handler, or a function for data-last style.

    Examples
    --------
    >>> match(Ok(2), {"ok": lambda x: x * 2, "err": lambda e: 0})  # Data-first: 4
    4
    >>> match({"ok": lambda x: f"Got {x}", "err": lambda e: f"Failed: {e}"})(Ok(2))  # Data-last
    'Got 2'
    """
    if handlers is None:
        _handlers = cast(Matcher[A, B, E, B], result)
        return lambda r: r.match(_handlers)
    return cast(Result[A, E], result).match(handlers)
