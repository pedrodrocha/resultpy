from typing import Union, get_args, get_origin

import pytest

from resultpy.result import A, E, Err, Ok, Res, Result


class TestOk:
    def test_stores_value_and_repr(self) -> None:
        ok = Ok(123)
        assert ok.value == 123
        assert ok.status == "ok"
        assert repr(ok) == "Ok(123)"


class TestErr:
    def test_stores_value_and_repr(self) -> None:
        err = Err("boom")
        assert err.value == "boom"
        assert err.status == "err"
        assert repr(err) == "Err('boom')"


class TestResultHelpers:
    def test_ok_and_err_helpers(self) -> None:
        ok = Result.ok("done")
        err = Result.err(ValueError("fail"))
        assert isinstance(ok, Ok)
        assert ok.value == "done"
        assert isinstance(err, Err)
        assert isinstance(err.value, ValueError)

    def test_match_on_ok_and_err(self) -> None:
        ok = Result.ok(1)
        err = Result.err("fail")

        match ok:
            case Ok(v):
                assert v == 1
            case _:
                pytest.fail("match failed for Ok")

        match err:
            case Err(v):
                assert v == "fail"
            case _:
                pytest.fail("match failed for Err")


class TestResAlias:
    def test_res_type_alias_is_union_of_ok_and_err(self) -> None:
        origin = get_origin(Res)
        args = get_args(Res)

        assert origin is Union
        assert len(args) == 2
        ok_arg, err_arg = args
        assert getattr(ok_arg, "__origin__", ok_arg) is Ok
        assert getattr(err_arg, "__origin__", err_arg) is Err
