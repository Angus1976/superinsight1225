"""
Unit tests for the shared LLM retry utility.

Tests exponential backoff, transient vs non-transient error classification,
and retry exhaustion behavior.
Validates: Requirements 2.5 (LLM retry with exponential backoff)
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from src.ai.retry import (
    MAX_RETRIES,
    _is_transient_error,
    retry_with_backoff,
)


# ---------------------------------------------------------------------------
# _is_transient_error
# ---------------------------------------------------------------------------

class TestIsTransientError:
    def test_value_error_not_transient(self):
        assert _is_transient_error(ValueError("bad")) is False

    def test_type_error_not_transient(self):
        assert _is_transient_error(TypeError("wrong type")) is False

    def test_key_error_not_transient(self):
        assert _is_transient_error(KeyError("missing")) is False

    def test_connection_error_is_transient(self):
        assert _is_transient_error(ConnectionError("refused")) is True

    def test_timeout_error_is_transient(self):
        assert _is_transient_error(TimeoutError("timed out")) is True

    def test_os_error_is_transient(self):
        assert _is_transient_error(OSError("network")) is True

    def test_runtime_error_is_transient(self):
        # Unknown errors default to transient
        assert _is_transient_error(RuntimeError("unknown")) is True

    def test_pydantic_validation_error_not_transient(self):
        """ValidationError (by class name) should not be retried."""
        class ValidationError(Exception):
            pass
        assert _is_transient_error(ValidationError("invalid")) is False


# ---------------------------------------------------------------------------
# retry_with_backoff
# ---------------------------------------------------------------------------

class TestRetryWithBackoff:
    @pytest.mark.asyncio
    async def test_succeeds_first_try(self):
        fn = AsyncMock(return_value="ok")

        with patch("src.ai.retry.asyncio.sleep", new_callable=AsyncMock):
            result = await retry_with_backoff(fn)

        assert result == "ok"
        assert fn.await_count == 1

    @pytest.mark.asyncio
    async def test_retries_on_transient_error(self):
        fn = AsyncMock(side_effect=[ConnectionError("fail"), "ok"])

        with patch("src.ai.retry.asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            result = await retry_with_backoff(fn, max_retries=3)

        assert result == "ok"
        assert fn.await_count == 2
        mock_sleep.assert_awaited_once_with(1.0)  # base_delay * 2^0

    @pytest.mark.asyncio
    async def test_exponential_backoff_delays(self):
        fn = AsyncMock(side_effect=[
            TimeoutError("t1"),
            TimeoutError("t2"),
            TimeoutError("t3"),
            "ok",
        ])

        with patch("src.ai.retry.asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            result = await retry_with_backoff(fn, max_retries=3, base_delay=1.0)

        assert result == "ok"
        assert fn.await_count == 4
        delays = [call.args[0] for call in mock_sleep.await_args_list]
        assert delays == [1.0, 2.0, 4.0]  # 1*2^0, 1*2^1, 1*2^2

    @pytest.mark.asyncio
    async def test_raises_after_all_retries_exhausted(self):
        fn = AsyncMock(side_effect=ConnectionError("always fails"))

        with patch("src.ai.retry.asyncio.sleep", new_callable=AsyncMock):
            with pytest.raises(ConnectionError, match="always fails"):
                await retry_with_backoff(fn, max_retries=3)

        assert fn.await_count == 4  # 1 initial + 3 retries

    @pytest.mark.asyncio
    async def test_no_retry_on_non_transient_error(self):
        fn = AsyncMock(side_effect=ValueError("bad input"))

        with patch("src.ai.retry.asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            with pytest.raises(ValueError, match="bad input"):
                await retry_with_backoff(fn, max_retries=3)

        assert fn.await_count == 1
        mock_sleep.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_custom_base_delay(self):
        fn = AsyncMock(side_effect=[OSError("net"), "ok"])

        with patch("src.ai.retry.asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            await retry_with_backoff(fn, max_retries=2, base_delay=0.5)

        mock_sleep.assert_awaited_once_with(0.5)

    @pytest.mark.asyncio
    async def test_forwards_args_and_kwargs(self):
        fn = AsyncMock(return_value="result")

        with patch("src.ai.retry.asyncio.sleep", new_callable=AsyncMock):
            result = await retry_with_backoff(fn, "a", "b", key="val")

        fn.assert_awaited_once_with("a", "b", key="val")
        assert result == "result"

    @pytest.mark.asyncio
    async def test_max_retries_default_is_three(self):
        assert MAX_RETRIES == 3
