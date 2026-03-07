"""Unit tests for time utilities."""

from __future__ import annotations

from datetime import datetime, timedelta

from dd_platform.utils.time import days_since, is_stale, utc_now


class TestUtcNow:
    """Tests for the utc_now function."""

    def test_returns_datetime(self) -> None:
        result = utc_now()
        assert isinstance(result, datetime)

    def test_roughly_now(self) -> None:
        before = datetime.utcnow()
        result = utc_now()
        after = datetime.utcnow()
        assert before <= result <= after


class TestIsStale:
    """Tests for the is_stale function."""

    def test_none_is_stale(self) -> None:
        assert is_stale(None, 90) is True

    def test_recent_is_not_stale(self) -> None:
        recent = utc_now() - timedelta(days=1)
        assert is_stale(recent, 90) is False

    def test_old_is_stale(self) -> None:
        old = utc_now() - timedelta(days=100)
        assert is_stale(old, 90) is True

    def test_exactly_at_ttl_boundary(self) -> None:
        # At exactly the TTL boundary, it should be considered stale
        boundary = utc_now() - timedelta(days=90, seconds=1)
        assert is_stale(boundary, 90) is True


class TestDaysSince:
    """Tests for the days_since function."""

    def test_none_returns_none(self) -> None:
        assert days_since(None) is None

    def test_today_is_zero(self) -> None:
        result = days_since(utc_now())
        assert result == 0

    def test_yesterday(self) -> None:
        yesterday = utc_now() - timedelta(days=1)
        result = days_since(yesterday)
        assert result == 1

    def test_last_week(self) -> None:
        last_week = utc_now() - timedelta(days=7)
        result = days_since(last_week)
        assert result == 7
