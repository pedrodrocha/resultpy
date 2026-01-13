from typing import TypeVar, Generic, Literal
from abc import ABC

"""
Type variable for a generic type A
"""
A = TypeVar("A")

"""
Type variable for a transformed generic type B
"""
B = TypeVar("B")

"""
Type variable for a generic type E
"""
E = TypeVar("E")


class Result(Generic[A, E], ABC):
    __slots__ = ("status", "value")
    status: Literal["ok", "err"]

    @staticmethod
    def ok(value: A) -> "Ok[A, E]":
        return Ok(value)

    @staticmethod
    def err(value: E) -> "Err[A, E]":
        return Err(value)

    def is_ok(self) -> bool:
        return self.status == "ok"

    def is_err(self) -> bool:
        return self.status == "err"


class Ok(Result[A, E]):
    __slots__ = ("value",)
    __match_args__ = ("value",)

    status = "ok"

    def __init__(self, value: A) -> None:
        self.value: A = value

    def __repr__(self) -> str:
        return f"Ok({self.value!r})"


class Err(Result[A, E]):
    __slots__ = ("value",)
    __match_args__ = ("value",)

    status = "err"

    def __init__(self, value: E) -> None:
        self.value: E = value

    def __repr__(self) -> str:
        return f"Err({self.value!r})"
