from typing import (
    Any,
    Awaitable,
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
    NoReturn,
    Generator,
)
from abc import ABC, abstractmethod

from .error import panic

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
Type variable for a method error parameter U
"""
U = TypeVar("U")

"""
Type variable for a generic type G, contravariant
"""
G = TypeVar("G", contravariant=True)

# Type variables for Result.do
A_do = TypeVar("A_do")
E_do = TypeVar("E_do")

"""
Type variable for a transformed generic error type F
"""
F = TypeVar("F")


class Matcher(TypedDict, Generic[A, B, E, F]):
    """ "
    TypedDict for pattern matching on Result variants
    """

    ok: Callable[[A], B]
    err: Callable[[E], F]


class SerializedOk(TypedDict, Generic[A]):
    """
    A serialized representation of an Ok result
    """

    status: Literal["ok"]
    value: A


class SerializedErr(TypedDict, Generic[E]):
    """
    A serialized representation of an Err result
    """

    status: Literal["err"]
    value: E


SerializedResult: TypeAlias = Union[SerializedOk[A], SerializedErr[E]]


class Result(Generic[A, E], ABC):
    """Discriminated union representing operation success or failure.

    Result[A, E] is either Ok[A, E] (success with value) or Err[A, E] (failure with error).

    Example:
        >>> result: Result[int, str] = Ok(42)
        >>> result.map(lambda x: x * 2)
        Ok(84)
    """

    __slots__ = ()

    @property
    @abstractmethod
    def status(self) -> Literal["ok", "err"]: ...

    @staticmethod
    def ok(value: T) -> "Ok[T, Never]":
        """Creates successful result.

        Args:
            value: Success value.

        Returns:
            Ok instance.

        Example:
            >>> Result.ok(42)
            Ok(42)
        """
        return Ok(value)

    @staticmethod
    def err(value: U) -> "Err[Never, U]":
        """Creates error result.

        Args:
            value: Error value.

        Returns:
            Err instance.

        Example:
            >>> Result.err("failed")
            Err('failed')
        """
        return Err(value)

    @staticmethod
    def gen(
        fn: Callable[[], Generator["Result[Any, E]", Any, "Result[A, E]"]],
    ) -> "Result[A, E]":
        gen = fn()

        try:
            # Prime the generator
            yielded = gen.send(None)

            while True:
                if yielded.is_err():
                    # short-circuit immediately
                    return cast("Err[Never, E]", yielded)

                # unwrap Ok and send value back
                yielded = gen.send(yielded.unwrap())

        except StopIteration as stop:
            returned = stop.value
            if not isinstance(returned, Result):
                panic("Generator function must return a Result")
            return cast("Result[A, E]", returned)
        except BaseException as e:
            # Generator body threw - this is a programming error
            panic("Exception in generator", e)

    def is_ok(self) -> bool:
        """Returns True if result is Ok.

        Returns:
            True if Ok, False otherwise.

        Example:
            >>> Ok(42).is_ok()
            True
            >>> Err("fail").is_ok()
            False
        """
        return self.status == "ok"

    def is_err(self) -> bool:
        """Returns True if result is Err.

        Returns:
            True if Err, False otherwise.

        Example:
            >>> Ok(42).is_err()
            False
            >>> Err("fail").is_err()
            True
        """
        return self.status == "err"

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
    async def tap_async(self, fn: Callable[[A], Awaitable[None]]) -> "Result[A, E]": ...

    @abstractmethod
    def and_then(self, fn: Callable[[A], "Result[B, F]"]) -> "Result[B, E | F]": ...

    @abstractmethod
    async def and_then_async(
        self, fn: Callable[[A], Awaitable["Result[B, F]"]]
    ) -> "Result[B, E | F]": ...

    @abstractmethod
    def match(self, cases: Matcher[A, B, E, F]) -> B | F: ...

    @abstractmethod
    def serialize(self) -> SerializedResult[A, E]: ...

    @staticmethod
    def hydrate(data: object) -> "Result[object, object] | None":
        """Rehydrates serialized Result from plain dict back into Ok/Err instances.

        Returns None if not a serialized Result.

        Args:
            data: Serialized result dict.

        Returns:
            Result instance or None.

        Example:
            >>> Result.hydrate({"status": "ok", "value": 42})
            Ok(42)
            >>> Result.hydrate({"status": "err", "value": "fail"})
            Err('fail')
            >>> Result.hydrate({"invalid": "data"})
            None
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
        else:
            return Result.err(serialized["value"])

    @staticmethod
    def hydrate_as[T, U](
        data: object,
        *,
        ok: Callable[[object], T],
        err: Callable[[object], U],
    ) -> "Result[T, U] | None":
        """Rehydrates serialized Result with custom decoders for values.

        Returns None if not a serialized Result. If decoders throw, returns Err with the exception.

        Args:
            data: Serialized result dict.
            ok: Decoder for success values.
            err: Decoder for error values.

        Returns:
            Result instance or None.

        Example:
            >>> def decode_int(x): return int(x)
            >>> Result.hydrate_as({"status": "ok", "value": "42"}, ok=decode_int, err=str)
            Ok(42)
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
            else:
                decoded_error = err(serialized["value"])
                return Result.err(decoded_error)
        except Exception as e:
            return Result.err(cast(U, e))


"""
Type alias for generator-based Result composition.

Use this type to annotate generator functions that work with Result.gen() for
do-notation style error handling.

Type Parameters:
    T: The success value type of the final returned Result
    E: The error type that can be yielded or returned throughout the computation

Note: The yield and send types are internally typed as Any because generator
functions can yield Results of different success types (e.g., Result[int, E],
Result[str, E]) and receive different unwrapped values in the same computation.

Example:
    >>> def compute() -> Do[int, str]:
    ...     x: int = yield Ok(5)
    ...     y: int = yield Ok(10)
    ...     return Ok(x + y)
    >>> Result.gen(compute).unwrap()
    15
"""
type Do[T, E] = Generator[Result[Any, E], Any, Result[T, E]]


class Ok(Result[A, E]):
    """Successful result variant.

    Args:
        value: Success value.

    Example:
        >>> result = Ok(42)
        >>> result.value
        42
        >>> result.status
        'ok'
    """

    __slots__ = ("value",)
    __match_args__ = ("value",)

    def __init__(self, value: A) -> None:
        self.value: A = value

    @property
    def status(self) -> Literal["ok"]:
        return "ok"

    def map(self, fn: Callable[[A], B]) -> "Ok[B, E]":
        """Transforms success value.

        Args:
            fn: Transformation function.

        Returns:
            Ok with transformed value.

        Raises:
            Panic: If fn throws.

        Example:
            >>> Ok(2).map(lambda x: x * 3)
            Ok(6)
        """
        return try_or_panic(lambda: Ok(fn(self.value)), "Ok.map failed")

    def map_err(self, fn: Callable[[E], F]) -> "Ok[A, F]":
        """No-op on Ok, returns self with new phantom error type.

        Args:
            fn: Ignored.

        Returns:
            Self with updated phantom E type.
        """
        return cast("Ok[A, F]", self)

    def unwrap(self, message: Optional[str] = None) -> A:
        """Extracts value.

        Args:
            message: Ignored.

        Returns:
            The value.

        Example:
            >>> Ok(42).unwrap()
            42
        """
        return self.value

    def unwrap_or(self, fallback: object) -> A:
        """Returns value, ignoring fallback.

        Args:
            fallback: Ignored.

        Returns:
            The value.

        Example:
            >>> Ok(42).unwrap_or(0)
            42
        """
        return self.value

    def unwrap_err(self, message: Optional[str] = None) -> NoReturn:
        """Panics with optional message.

        Args:
            message: Error message.

        Raises:
            Panic: Always panics.

        Example:
            >>> Ok(42).unwrap_err()
            Panic: unwrap_err called on Ok: 42
        """
        panic(message or f"unwrap_err called on Ok: {self.value!r}")

    def tap(self, fn: Callable[[A], None]) -> "Ok[A, E]":
        """Runs side effect, returns self.

        Args:
            fn: Side effect function.

        Returns:
            Self.

        Raises:
            Panic: If fn throws.

        Example:
            >>> Ok(2).tap(print).map(lambda x: x * 2)
            2
            Ok(4)
        """
        fn(self.value)
        return self

    async def tap_async(self, fn: Callable[[A], Awaitable[None]]) -> "Ok[A, E]":
        """Runs async side effect, returns self.

        Args:
            fn: Async side effect function.

        Returns:
            Self.

        Raises:
            Panic: If fn throws or rejects.

        Example:
            >>> await Ok(2).tap_async(async_log)
            Ok(2)
        """
        await fn(self.value)
        return self

    def and_then(self, fn: Callable[[A], "Result[B, F]"]) -> "Result[B, E | F]":
        """Chains Result-returning function.

        Args:
            fn: Function returning Result.

        Returns:
            Result from fn.

        Raises:
            Panic: If fn throws.

        Example:
            >>> Ok(2).and_then(lambda x: Ok(x * 2) if x > 0 else Err("negative"))
            Ok(4)
        """
        return try_or_panic(lambda: fn(self.value), "Ok.and_then failed")

    async def and_then_async(
        self, fn: Callable[[A], Awaitable[Result[B, F]]]
    ) -> "Result[B, E | F]":
        """Chains async Result-returning function.

        Args:
            fn: Async function returning Result.

        Returns:
            Result from fn.

        Raises:
            Panic: If fn throws or rejects.

        Example:
            >>> await Ok(1).and_then_async(async_fetch_data)
            Ok(...)
        """
        return await try_or_panic_async(
            lambda: fn(self.value), "Ok.and_then_async failed"
        )

    def match(self, cases: Matcher[A, B, E, F]) -> B | F:
        """Pattern matches on Result.

        Args:
            cases: Ok and err handlers.

        Returns:
            Result of ok handler.

        Raises:
            Panic: If handler throws.

        Example:
            >>> Ok(2).match({"ok": lambda x: x * 2, "err": lambda e: 0})
            4
        """

        def call_handler() -> B | F:
            return cases["ok"](self.value)

        return try_or_panic(call_handler, "Ok.match failed")

    def serialize(self) -> SerializedOk[A]:
        """Converts to plain dict for serialization.

        Returns:
            Dict with status and value.

        Example:
            >>> Ok(42).serialize()
            {'status': 'ok', 'value': 42}
        """
        return SerializedOk(status="ok", value=self.value)

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
    """Error result variant.

    Args:
        value: Error value.

    Example:
        >>> result = Err("failed")
        >>> result.value
        'failed'
        >>> result.status
        'err'
    """

    __slots__ = ("value",)
    __match_args__ = ("value",)

    def __init__(self, value: E) -> None:
        self.value: E = value

    @property
    def status(self) -> Literal["err"]:
        return "err"

    def map(self, fn: Callable[[A], B]) -> "Err[B, E]":
        """No-op on Err, returns self with new phantom T.

        Args:
            fn: Ignored.

        Returns:
            Self.
        """
        return cast("Err[B, E]", self)

    def map_err(self, fn: Callable[[E], F]) -> "Err[A, F]":
        """Transforms error value.

        Args:
            fn: Transformation function.

        Returns:
            Err with transformed error.

        Raises:
            Panic: If fn throws.

        Example:
            >>> Err("fail").map_err(lambda e: f"Error: {e}")
            Err("Error: fail")
        """
        return try_or_panic(lambda: Err(fn(self.value)), "Err.map_err failed")

    def unwrap(self, message: Optional[str] = None) -> NoReturn:
        """Panics with optional message.

        Args:
            message: Error message.

        Raises:
            Panic: Always panics.

        Example:
            >>> Err("fail").unwrap()
            Panic: unwrap called on Err: 'fail'
        """
        panic(message or f"unwrap called on Err: {self.value!r}")

    def unwrap_or(self, fallback: B) -> B:
        """Returns fallback value.

        Args:
            fallback: Fallback value.

        Returns:
            Fallback.

        Example:
            >>> Err("fail").unwrap_or(42)
            42
        """
        return fallback

    def unwrap_err(self, message: Optional[str] = None) -> E:
        """Extracts error value.

        Args:
            message: Ignored.

        Returns:
            The error value.

        Example:
            >>> Err("fail").unwrap_err()
            'fail'
        """
        return self.value

    def tap(self, fn: Callable[[A], None]) -> "Err[A, E]":
        """No-op on Err, returns self.

        Args:
            fn: Ignored.

        Returns:
            Self.
        """
        return self

    async def tap_async(self, fn: Callable[[A], Awaitable[None]]) -> "Err[A, E]":
        """No-op on Err, returns Promise of self.

        Args:
            fn: Ignored.

        Returns:
            Self.
        """
        return self

    def and_then(self, fn: Callable[[A], Result[B, F]]) -> "Err[A, E]":
        """No-op on Err, returns self with widened error type.

        Args:
            fn: Ignored.

        Returns:
            Self.
        """
        return try_or_panic(lambda: cast("Err[A, E]", self), "Err.and_then failed")

    async def and_then_async(
        self, fn: Callable[[A], Awaitable[Result[B, F]]]
    ) -> "Err[A, E]":
        """No-op on Err, returns self with widened error type.

        Args:
            fn: Ignored.

        Returns:
            Self.
        """
        return try_or_panic(
            lambda: cast("Err[A, E]", self), "Err.and_then_async failed"
        )

    def match(self, cases: Matcher[A, B, E, F]) -> B | F:
        """Pattern matches on Result.

        Args:
            cases: Ok and err handlers.

        Returns:
            Result of err handler.

        Raises:
            Panic: If handler throws.

        Example:
            >>> Err("fail").match({"ok": lambda x: x, "err": lambda e: len(e)})
            4
        """

        def call_handler() -> B | F:
            return cases["err"](self.value)

        return try_or_panic(call_handler, "Err.match failed")

    def serialize(self) -> SerializedErr[E]:
        """Converts to plain dict for serialization.

        Returns:
            Dict with status and error.

        Example:
            >>> Err("fail").serialize()
            {'status': 'err', 'value': 'fail'}
        """
        value = str(self.value) if isinstance(self.value, Exception) else self.value
        return SerializedErr(status="err", value=value)

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


@overload
def map(result: Result[A, E], fn: Callable[[A], B]) -> Result[B, E]: ...


@overload
def map(result: Callable[[A], B]) -> Callable[[Result[A, E]], Result[B, E]]: ...


def map(
    result: Result[A, E] | Callable[[A], B],
    fn: Callable[[A], B] | None = None,
) -> Result[B, E] | Callable[[Result[A, E]], Result[B, E]]:
    """Transforms success value, passes error through.

    Supports data-first and data-last styles.

    Args:
        result: Result or transformation function.
        fn: Transformation function (data-first) or None (data-last).

    Returns:
        Transformed Result or curried function.

    Example:
        >>> map(Ok(2), lambda x: x * 2)
        Ok(4)
        >>> mapper = map(lambda x: x * 2)
        >>> mapper(Ok(2))
        Ok(4)
    """
    if fn is None:
        _fn = cast(Callable[[A], B], result)
        return lambda r: try_or_panic(lambda: r.map(_fn), "map failed")
    return try_or_panic(lambda: cast(Result[A, E], result).map(fn), "map failed")


@overload
def map_err(result: Result[A, E], fn: Callable[[E], F]) -> Result[A, F]: ...


@overload
def map_err(result: Callable[[E], F]) -> Callable[[Result[A, E]], Result[A, F]]: ...


def map_err(
    result: Result[A, E] | Callable[[E], F],
    fn: Callable[[E], F] | None = None,
) -> Result[A, F] | Callable[[Result[A, E]], Result[A, F]]:
    """Transforms error value, passes success through.

    Supports data-first and data-last styles.

    Args:
        result: Result or transformation function.
        fn: Transformation function (data-first) or None (data-last).

    Returns:
        Transformed Result or curried function.

    Example:
        >>> map_err(Err("fail"), lambda e: f"Error: {e}")
        Err("Error: fail")
    """
    if fn is None:
        _fn = cast(Callable[[E], F], result)
        return lambda r: try_or_panic(lambda: r.map_err(_fn), "map_err failed")
    return try_or_panic(
        lambda: cast(Result[A, E], result).map_err(fn), "map_err failed"
    )


@overload
def tap(result: Result[A, E], fn: Callable[[A], None]) -> Result[A, E]: ...


@overload
def tap(result: Callable[[A], None]) -> Callable[[Result[A, E]], Result[A, E]]: ...


def tap(
    result: Result[A, E] | Callable[[A], None],
    fn: Callable[[A], None] | None = None,
) -> Result[A, E] | Callable[[Result[A, E]], Result[A, E]]:
    """Runs side effect on success value, returns original result.

    Supports data-first and data-last styles.

    Args:
        result: Result or side effect function.
        fn: Side effect function (data-first) or None (data-last).

    Returns:
        Original Result or curried function.

    Example:
        >>> tap(Ok(2), print)
        2
        Ok(2)
    """
    if fn is None:
        _fn = cast(Callable[[A], None], result)
        return lambda r: try_or_panic(lambda: r.tap(_fn), "tap failed")
    return try_or_panic(lambda: cast(Result[A, E], result).tap(fn), "tap failed")


@overload
def tap_async(
    result: Result[A, E], fn: Callable[[A], Awaitable[None]]
) -> Coroutine[None, None, Result[A, E]]: ...


@overload
def tap_async(
    result: Callable[[A], Awaitable[None]],
) -> Callable[[Result[A, E]], Coroutine[None, None, Result[A, E]]]: ...


def tap_async(
    result: Result[A, E] | Callable[[A], Awaitable[None]],
    fn: Callable[[A], Awaitable[None]] | None = None,
) -> (
    Coroutine[None, None, Result[A, E]]
    | Callable[[Result[A, E]], Coroutine[None, None, Result[A, E]]]
):
    """Runs async side effect on success value, returns original result.

    Supports data-first and data-last styles.

    Args:
        result: Result or async side effect function.
        fn: Async side effect function (data-first) or None (data-last).

    Returns:
        Promise of original Result or curried function.

    Example:
        >>> await tap_async(Ok(2), async_log)
        Ok(2)
    """
    if fn is None:
        _fn = cast(Callable[[A], Awaitable[None]], result)
        return lambda r: try_or_panic_async(
            lambda: r.tap_async(_fn), "tap_async failed"
        )
    return try_or_panic_async(
        lambda: cast(Result[A, E], result).tap_async(fn), "tap_async failed"
    )


def unwrap(result: Result[A, E], message: Optional[str] = None) -> A:
    """Extracts value or panics.

    Args:
        result: Result to unwrap.
        message: Optional panic message.

    Returns:
        The value.

    Raises:
        Panic: If result is Err.

    Example:
        >>> unwrap(Ok(42))
        42
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
    """Chains Result-returning function on success.

    Supports data-first and data-last styles.

    Args:
        result: Result or chaining function.
        fn: Chaining function (data-first) or None (data-last).

    Returns:
        Chained Result or curried function.

    Example:
        >>> and_then(Ok(2), lambda x: Ok(x * 2) if x > 0 else Err("neg"))
        Ok(4)
    """
    if fn is None:
        _fn = cast(Callable[[A], Result[B, F]], result)
        return lambda r: cast(
            Result[B, E | F],
            try_or_panic(
                lambda: r.and_then(cast(Callable[[A], Result[B, E]], _fn)),
                "and_then failed",
            ),
        )
    return cast(
        Result[B, E | F],
        try_or_panic(
            lambda: cast(Result[A, E], result).and_then(
                cast(Callable[[A], Result[B, E]], fn)
            ),
            "and_then failed",
        ),
    )


@overload
def and_then_async(
    result: Result[A, E], fn: Callable[[A], Awaitable[Result[B, F]]]
) -> Coroutine[None, None, Result[B, E | F]]: ...


@overload
def and_then_async(
    result: Callable[[A], Awaitable[Result[B, F]]],
) -> Callable[[Result[A, E]], Coroutine[None, None, Result[B, E | F]]]: ...


def and_then_async(
    result: Result[A, E] | Callable[[A], Awaitable[Result[B, F]]],
    fn: Callable[[A], Awaitable[Result[B, F]]] | None = None,
) -> (
    Coroutine[None, None, Result[B, E | F]]
    | Callable[[Result[A, E]], Coroutine[None, None, Result[B, E | F]]]
):
    """Chains async Result-returning function on success.

    Supports data-first and data-last styles.

    Args:
        result: Result or async chaining function.
        fn: Async chaining function (data-first) or None (data-last).

    Returns:
        Promise of chained Result or curried function.

    Example:
        >>> await and_then_async(Ok(1), async_fetch_data)
        Ok(...)
    """
    if fn is None:
        _fn = cast(Callable[[A], Awaitable[Result[B, F]]], result)
        return lambda r: cast(
            Coroutine[None, None, Result[B, E | F]],
            try_or_panic_async(
                lambda: r.and_then_async(
                    cast(Callable[[A], Awaitable[Result[B, E]]], _fn)
                ),
                "and_then_async failed",
            ),
        )
    return cast(
        Coroutine[None, None, Result[B, E | F]],
        try_or_panic_async(
            lambda: cast(Result[A, E], result).and_then_async(
                cast(Callable[[A], Awaitable[Result[B, E]]], fn)
            ),
            "and_then_async failed",
        ),
    )


@overload
def match(
    result: Matcher[A, B, E, B],
) -> Callable[[Result[A, E]], B]: ...


@overload
def match(result: Result[A, E], handlers: Matcher[A, B, E, B]) -> B: ...


def match(
    result: Result[A, E] | Matcher[A, B, E, B],
    handlers: Matcher[A, B, E, B] | None = None,
) -> B | Callable[[Result[A, E]], B]:
    """Pattern matches on Result.

    Supports data-first and data-last styles.

    Args:
        result: Result or handlers dict.
        handlers: Handlers dict (data-first) or None (data-last).

    Returns:
        Result of matched handler or curried function.

    Example:
        >>> match(Ok(2), {"ok": lambda x: x * 2, "err": lambda e: 0})
        4
    """
    if handlers is None:
        _handlers = cast(Matcher[A, B, E, B], result)

        def apply_match(r: Result[A, E]) -> B:
            return try_or_panic(lambda: r.match(_handlers), "match failed")

        return apply_match

    def apply_handlers() -> B:
        return try_or_panic(
            lambda: cast(Result[A, E], result).match(handlers), "match failed"
        )

    return apply_handlers()


def try_or_panic(fn: Callable[[], A], message: str) -> A:
    """Executes fn, panics if it throws.

    Args:
        fn: Function to execute.
        message: Panic message.

    Returns:
        Result of fn.

    Raises:
        Panic: If fn throws.
    """
    try:
        return fn()
    except Exception as e:
        panic(message, e)


async def try_or_panic_async(fn: Callable[[], Awaitable[A]], message: str) -> A:
    """Async version of try_or_panic.

    Args:
        fn: Async function to execute.
        message: Panic message.

    Returns:
        Result of fn.

    Raises:
        Panic: If fn throws or rejects.
    """
    try:
        return await fn()
    except Exception as e:
        panic(message, e)
