"""Unit tests for hashing utilities."""

from __future__ import annotations

from dd_platform.utils.hashing import content_hash, short_hash


class TestContentHash:
    """Tests for the content_hash function."""

    def test_deterministic(self) -> None:
        assert content_hash("hello") == content_hash("hello")

    def test_different_inputs_differ(self) -> None:
        assert content_hash("hello") != content_hash("world")

    def test_sha256_length(self) -> None:
        result = content_hash("test")
        assert len(result) == 64  # SHA256 hex digest length

    def test_empty_string(self) -> None:
        result = content_hash("")
        assert len(result) == 64


class TestShortHash:
    """Tests for the short_hash function."""

    def test_default_length(self) -> None:
        result = short_hash("test")
        assert len(result) == 12

    def test_custom_length(self) -> None:
        result = short_hash("test", length=8)
        assert len(result) == 8

    def test_deterministic(self) -> None:
        assert short_hash("hello") == short_hash("hello")

    def test_prefix_of_full_hash(self) -> None:
        full = content_hash("test")
        short = short_hash("test")
        assert full.startswith(short)
