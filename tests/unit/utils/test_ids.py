"""Unit tests for ID generation utilities."""

from __future__ import annotations

from dd_platform.utils.ids import generate_id, generate_run_id, generate_snapshot_id


class TestGenerateId:
    """Tests for the generate_id function."""

    def test_returns_string(self) -> None:
        result = generate_id()
        assert isinstance(result, str)

    def test_unique(self) -> None:
        ids = {generate_id() for _ in range(100)}
        assert len(ids) == 100, "IDs should be unique"

    def test_with_prefix(self) -> None:
        result = generate_id("evidence")
        assert result.startswith("evidence:")

    def test_without_prefix(self) -> None:
        result = generate_id()
        assert ":" not in result


class TestGenerateRunId:
    """Tests for the generate_run_id function."""

    def test_starts_with_run_prefix(self) -> None:
        result = generate_run_id()
        assert result.startswith("run:")

    def test_unique(self) -> None:
        ids = {generate_run_id() for _ in range(50)}
        assert len(ids) == 50


class TestGenerateSnapshotId:
    """Tests for the generate_snapshot_id function."""

    def test_starts_with_snapshot_prefix(self) -> None:
        result = generate_snapshot_id("company:test")
        assert result.startswith("snapshot:")

    def test_unique(self) -> None:
        ids = {generate_snapshot_id("company:test") for _ in range(50)}
        assert len(ids) == 50
