from typing import Callable, TypeVar, Generic, overload

A = TypeVar("A")
B = TypeVar("B")


class fn(Generic[A, B]):
    """Creates a typed callable from a lambda or function.

    Allows explicit generic typing of anonymous functions using subscript
    syntax, providing a close semantic equivalent to a typed lambda.

    Args:
        f: A callable from ``A`` to ``B``.

    Returns:
        The same callable with its type fixed to ``Callable[[A], B]``.

    Example:
        >>> double = fn[int, int](lambda x: x * 2)
        >>> Ok(5).map(double)
        Ok(10)
    """

    @overload
    def __new__(cls, f: Callable[[A], B]) -> Callable[[A], B]: ...
    @overload
    def __new__(cls, f: Callable[..., B]) -> Callable[..., B]: ...

    def __new__(cls, f: Callable[..., object]) -> Callable[..., object]:
        return f
