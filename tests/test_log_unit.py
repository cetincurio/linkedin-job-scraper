import logging

import pytest

import ljs.log as log_module
from ljs.log import (
    bind_log_context,
    get_log_context,
    log_exception,
    set_log_context,
)


@pytest.fixture(autouse=True)
def _reset_log_context_between_tests():
    # `set_log_context()` is intentionally persistent; avoid leaking state.
    log_module._CTX.set(None)
    yield
    log_module._CTX.set(None)


def test_get_log_context_returns_copy_and_includes_bound_fields() -> None:
    assert get_log_context() == {}

    with bind_log_context(op="unit", country="DE"):
        ctx1 = get_log_context()
        assert ctx1["op"] == "unit"
        assert ctx1["country"] == "DE"

        # Ensure it's a copy: caller mutations should not affect future reads.
        ctx1["op"] = "mutated"
        ctx2 = get_log_context()
        assert ctx2["op"] == "unit"


def test_set_log_context_persists_fields() -> None:
    set_log_context(run_id="abc123")
    assert get_log_context()["run_id"] == "abc123"


def test_formatting_truncation_and_redaction_via_log_exception(
    caplog: pytest.LogCaptureFixture,
) -> None:
    logger = logging.getLogger("ljs.test.log_unit")
    logger.setLevel(logging.ERROR)

    long_value = "x" * 400
    with caplog.at_level(logging.ERROR, logger=logger.name):
        try:
            raise RuntimeError("boom")
        except RuntimeError:
            # Exercises:
            # - string truncation (long_value)
            # - None formatting (short_items includes None)
            # - list formatting (short list) and list formatting (len>_MAX_LIST_ITEMS)
            # - dict formatting
            # - repr formatting (object())
            # - sensitive key redaction (access_token)
            log_exception(
                logger,
                "event.test",
                access_token="secret",  # noqa: S106 (test redaction behavior)
                long_value=long_value,
                optional_field=None,
                items=[1, 2, 3, 4, 5],
                short_items=[1, None, "x"],
                meta={"a": 1},
                obj=object(),
            )

    assert len(caplog.records) == 1
    msg = caplog.records[0].message
    assert "event.test" in msg
    assert "access_token=***" in msg
    assert "long_value=" in msg and "..." in msg
    assert "items=[len=5]" in msg
    assert "short_items=[1,null,x]" in msg
    assert "meta={len=1}" in msg
    assert "obj=" in msg
    assert "optional_field=" not in msg


def test_log_exception_noop_when_error_level_disabled(caplog: pytest.LogCaptureFixture) -> None:
    logger = logging.getLogger("ljs.test.log_unit.disabled")
    logger.setLevel(logging.CRITICAL)  # ERROR disabled
    logger.propagate = False

    # Don't use `caplog.at_level(..., logger=logger.name)` here: it would temporarily
    # lower the logger level and defeat the early-return branch in `log_exception`.
    with caplog.at_level(logging.DEBUG):
        log_exception(logger, "event.should_not_log", error="x")

    assert caplog.records == []
