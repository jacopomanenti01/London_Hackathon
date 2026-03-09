"""Integration tests for SurrealDB.

These tests require a running SurrealDB instance.
Run with: make test-integration  (after `make db-up`)
"""

from __future__ import annotations

import pytest

# All integration tests are skipped by default unless the marker is specified
pytestmark = [
    pytest.mark.integration,
    pytest.mark.skip(reason="Requires running SurrealDB — run with `make test-integration`"),
]


class TestSurrealDBConnection:
    """Integration tests for SurrealDB connectivity."""

    async def test_connect_and_query(self) -> None:
        """Verify we can connect and run a basic query."""
        # This test requires a running SurrealDB instance
        # and will be activated during integration test runs.
        from dd_platform.persistence.surreal.client import SurrealClient
        from dd_platform.settings import get_settings

        settings = get_settings()
        client = SurrealClient(settings.surrealdb)
        await client.connect()

        # Basic health query
        result = await client.query("INFO FOR DB;")
        assert result is not None

        await client.disconnect()


class TestCompanyRepositoryIntegration:
    """Integration tests for CompanyRepository with real DB."""

    async def test_create_and_retrieve_company(self) -> None:
        """Create a company and retrieve it back."""
        # Placeholder — requires SurrealDB instance
        pass


class TestMigrationsIntegration:
    """Integration tests for database migrations."""

    async def test_migrations_run_without_error(self) -> None:
        """Run migrations and verify no errors."""
        # Placeholder — requires SurrealDB instance
        pass
