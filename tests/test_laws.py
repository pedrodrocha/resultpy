from safe_result import Result


def f(x: int) -> Result[int, str]:
    return Result.ok(x * 2)


def g(x: int) -> Result[int, str]:
    return Result.ok(x + 10)


class TestMonadLaws:
    """
    For a proper implementation of a Monad, we need to ensure that it satisfies the following laws:
        1. Left identity: return a >>= f  ≡  f a
        2. Right identity: m >>= return  ≡  m
        3. Associativity: (m >>= f) >>= g  ≡  m >>= (λx. f x >>= g)
    In Result terms:
        - result = Result.ok
        - >>= = and_then

    """

    class TestLeftIdentity:
        def test_it_holds_for_ok(self):
            a = 5
            left = Result.ok(a).and_then(f)
            right = f(a)
            assert left.unwrap() == right.unwrap()

    class TestRightIdentity:
        def test_it_holds_for_ok(self):
            m = Result.ok(42)

            result = m.and_then(Result.ok)

            assert result.unwrap() == m.unwrap()

        def test_it_holds_for_err(self):
            m = Result.err("error")

            result = m.and_then(Result.ok)

            assert result.is_err() is True

            if result.is_err():
                assert result.unwrap_err() == "error"

    class TestAssociativity:
        def test_it_holds_for_ok(self):
            m = Result.ok(5)

            left = m.and_then(f).and_then(g)
            right = m.and_then(lambda x: f(x).and_then(g))

            assert left.unwrap() == right.unwrap()
            assert left.unwrap() == 20  # (5 * 2) + 10 = 20

        def test_it_holds_for_err_short_circuiting(self):
            m = Result.err("error")

            left = m.and_then(f).and_then(g)
            right = m.and_then(lambda x: f(x).and_then(g))

            assert left.is_err() is True
            assert right.is_err() is True

            if left.is_err() and right.is_err():
                assert left.unwrap_err() == right.unwrap_err() == "error"

        def test_it_holds_when_f_returns_err(self):
            def f_err(x: int) -> Result[int, str]:
                return Result.err("f error")

            m = Result.ok(5)

            left = m.and_then(f_err).and_then(g)
            right = m.and_then(lambda x: f_err(x).and_then(g))

            assert left.is_err() is True
            assert right.is_err() is True

            if left.is_err() and right.is_err():
                assert left.unwrap_err() == right.unwrap_err() == "f error"


class TestFunctorLaws:
    """
    For a proper implementation of a Functor, we need to ensure that it satisfies the following laws:
        1. Identity: fmap id  ≡  id
        2. Composition: fmap (f . g)  ≡  fmap f . fmap g

    In Result terms:
        - fmap = map
        - id = lambda x: x
        - (f . g)(x) = f(g(x))

    """

    class TestIdentity:
        # m.map(x => x) ≡ m
        def test_it_holds_for_ok(self):
            m = Result.ok(42)
            result = m.map(lambda x: x)

            assert result.unwrap() == m.unwrap()

        def test_it_holds_for_err(self):
            m = Result.err("error")
            result = m.map(lambda x: x)

            assert result.is_err() is True

            if result.is_err():
                assert result.unwrap_err() == "error"

    class TestComposition:
        # m.map(f . g) ≡ m.map(g).map(f)
        def test_it_holds_for_ok(self):
            def f(x: int) -> int:
                return x * 2

            def g(x: int) -> int:
                return x + 10

            m = Result.ok(5)

            left = m.map(lambda x: f(g(x)))
            right = m.map(g).map(f)

            assert left.unwrap() == right.unwrap()
            assert left.unwrap() == 30  # (5 + 10) * 2 = 30

        def test_it_holds_for_err(self):
            def f(x: int) -> int:
                return x * 2

            def g(x: int) -> int:
                return x + 10

            m = Result.err("error")

            left = m.map(lambda x: f(g(x)))
            right = m.map(g).map(f)

            assert left.is_err() is True
            assert right.is_err() is True

            if left.is_err() and right.is_err():
                assert left.unwrap_err() == right.unwrap_err() == "error"
