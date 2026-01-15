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
Copied from src/pyresult/result.py to preserve full API
"""

T = TypeVar("T")
A = TypeVar("A", covariant=True)
B = TypeVar("B")
E = TypeVar("E", covariant=True)
U = TypeVar("U")
G = TypeVar("G", contravariant=True)
F = TypeVar("F")


class Matcher(TypedDict, Generic[A, B, E, F]):
    ok: Callable[[A], B]
    err: Callable[[E], F]


class SerializedOk(TypedDict, Generic[A]):
    status: Literal["ok"]
    value: A


class SerializedErr(TypedDict, Generic[E]):
    status: Literal["err"]
    value: E


SerializedResult: TypeAlias = Union[SerializedOk[A], SerializedErr[E]]


class Result(Generic[A, E], ABC):
    __slots__ = ()

    @property
    @abstractmethod
    def status(self) -> Literal["ok", "err"]:
        ...

    @staticmethod
    def ok(value: T) -> "Ok[T, Never]":
        return Ok(value)

    @staticmethod
    def err(value: U) -> "Err[Never, U]":
        return Err(value)

    @abstractmethod
    def is_ok(self) -> bool:
        ...

    @abstractmethod
    def is_err(self) -> bool:
        ...

    @abstractmethod
    def map(self, fn: Callable[[A], B]) -> "Result[B, E]":
        ...

    @abstractmethod
    def map_err(self, fn: Callable[[E], F]) -> "Result[A, F]":
        ...

    @abstractmethod
    def unwrap(self, message: Optional[str] = None) -> Union[A, object] | Never:
        ...

    @abstractmethod
    def unwrap_or(self, fallback: B) -> Union[A, B]:
        ...

    @abstractmethod
    def unwrap_err(self, message: Optional[str] = None) -> E:
        ...

    @abstractmethod
    def tap(self, fn: Callable[[A], None]) -> "Result[A, E]":
        ...

    @abstractmethod
    async def tap_async(
        self, fn: Callable[[A], Coroutine[None, None, None]]
    ) -> "Result[A, E]":
        ...

    @abstractmethod
    def and_then(self, fn: Callable[[A], "Result[B, F]"]) -> "Result[B, E | F]":
        ...

    @abstractmethod
    async def and_then_async(
        self, fn: Callable[[A], Coroutine[None, None, "Result[B, E]"]]
    ) -> "Result[B, E]":
        ...

    @abstractmethod
    def match(self, cases: Matcher[A, B, E, F]) -> B | F:
        ...

    @abstractmethod
    def serialize(self) -> SerializedResult[A, E]:
        ...

    @staticmethod
    def hydrate(data: object) -> "Result[object, object] | None":
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


class Ok(Result[A, E]):
    __slots__ = ("value",)
    __match_args__ = ("value",)

    def __init__(self, value: A) -> None:
        self.value: A = value

    @property
    def status(self) -> Literal["ok"]:
        return "ok"

    def map(self, fn: Callable[[A], B]) -> "Ok[B, E]":
        return Ok(fn(self.value))

    def map_err(self, fn: Callable[[E], F]) -> "Ok[A, F]":
        return cast("Ok[A, F]", self)

    def unwrap(self, message: Optional[str] = None) -> A:
        return self.value

    def unwrap_or(self, fallback: object) -> A:
        return self.value

    def unwrap_err(self, message: Optional[str] = None) -> Never:
        raise Exception(message or f"unwrap_err called on Ok: {self.value!r}")

    def tap(self, fn: Callable[[A], None]) -> "Ok[A, E]":
        fn(self.value)
        return self

    async def tap_async(
        self, fn: Callable[[A], Coroutine[None, None, None]]
    ) -> "Ok[A, E]":
        await fn(self.value)
        return self

    def and_then(self, fn: Callable[[A], "Result[B, F]"]) -> "Result[B, E | F]":
        return fn(self.value)

    async def and_then_async(
        self, fn: Callable[[A], Coroutine[None, None, Result[B, F]]]
    ) -> "Result[B, E | F]":
        return await fn(self.value)

    def match(self, cases: Matcher[A, B, E, F]) -> B | F:
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
    __slots__ = ("value",)
    __match_args__ = ("value",)

    def __init__(self, value: E) -> None:
        self.value: E = value

    @property
    def status(self) -> Literal["err"]:
        return "err"

    def map(self, fn: Callable[[A], B]) -> "Err[B, E]":
        return cast("Err[B, E]", self)

    def map_err(self, fn: Callable[[E], F]) -> "Err[A, F]":
        return Err(fn(self.value))

    def unwrap(self, message: Optional[str] = None) -> Never:
        raise Exception(message or f"Unwrap called on Err: {self.value!r}")

    def unwrap_or(self, fallback: B) -> B:
        return fallback

    def unwrap_err(self, message: Optional[str] = None) -> E:
        return self.value

    def tap(self, fn: Callable[[A], None]) -> "Err[A, E]":
        return self

    async def tap_async(
        self, fn: Callable[[A], Coroutine[None, None, None]]
    ) -> "Err[A, E]":
        return self

    def and_then(self, fn: Callable[[A], Result[B, F]]) -> "Err[A, E]":
        return cast("Err[A, E]", self)

    async def and_then_async(
        self, fn: Callable[[A], Coroutine[None, None, Result[B, F]]]
    ) -> "Err[A, E]":
        return cast("Err[A, E]", self)

    def match(self, cases: Matcher[A, B, E, F]) -> B | F:
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


@overload
def map(result: Result[A, E], fn: Callable[[A], B]) -> Result[B, E]: ...


@overload
def map(result: Callable[[A], B]) -> Callable[[Result[A, E]], Result[B, E]]: ...


def map(
    result: Result[A, E] | Callable[[A], B],
    fn: Callable[[A], B] | None = None,
) -> Result[B, E] | Callable[[Result[A, E]], Result[B, E]]:
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
    if fn is None:
        _fn = cast(Callable[[A], Coroutine[None, None, None]], result)
        return lambda r: r.tap_async(_fn)
    return cast(Result[A, E], result).tap_async(fn)


def unwrap(result: Result[A, E], message: Optional[str] = None) -> A:
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
    if handlers is None:
        _handlers = cast(Matcher[A, B, E, B], result)
        return lambda r: r.match(_handlers)
    return cast(Result[A, E], result).match(handlers)
