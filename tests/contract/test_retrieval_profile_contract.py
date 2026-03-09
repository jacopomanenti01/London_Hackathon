"""Contract tests for retrieval profile YAML configuration files.

Validates that the YAML configs in configs/retrieval_profiles/ are
well-formed and contain required keys.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml


PROFILES_DIR = Path("configs/retrieval_profiles")
REQUIRED_KEYS = {"profile_id", "name", "description", "retrievers", "contradiction_handling"}


@pytest.mark.contract
class TestRetrievalProfileConfigContract:
    """Ensure retrieval profile YAML files satisfy the expected contract."""

    def test_profiles_dir_exists(self) -> None:
        assert PROFILES_DIR.exists(), "configs/retrieval_profiles/ must exist"

    def test_at_least_one_profile(self) -> None:
        profiles = list(PROFILES_DIR.glob("*.yaml"))
        assert len(profiles) >= 1, "At least one retrieval profile must be defined"

    @pytest.mark.parametrize(
        "profile_file",
        list(PROFILES_DIR.glob("*.yaml")),
        ids=lambda p: p.stem,
    )
    def test_profile_valid_yaml(self, profile_file: Path) -> None:
        with open(profile_file) as f:
            data = yaml.safe_load(f)
        assert data is not None

    @pytest.mark.parametrize(
        "profile_file",
        list(PROFILES_DIR.glob("*.yaml")),
        ids=lambda p: p.stem,
    )
    def test_profile_required_keys(self, profile_file: Path) -> None:
        with open(profile_file) as f:
            data = yaml.safe_load(f)
        missing = REQUIRED_KEYS - set(data.keys())
        assert not missing, f"{profile_file.name} missing keys: {missing}"

    @pytest.mark.parametrize(
        "profile_file",
        list(PROFILES_DIR.glob("*.yaml")),
        ids=lambda p: p.stem,
    )
    def test_retrievers_non_empty(self, profile_file: Path) -> None:
        with open(profile_file) as f:
            data = yaml.safe_load(f)
        assert len(data.get("retrievers", [])) >= 1, (
            f"{profile_file.name} must have at least one retriever"
        )

    def test_graph_hybrid_expanded_exists(self) -> None:
        path = PROFILES_DIR / "graph_hybrid_expanded.yaml"
        assert path.exists(), "graph_hybrid_expanded.yaml must exist (default build profile)"

    def test_schema_aware_graph_hybrid_exists(self) -> None:
        path = PROFILES_DIR / "schema_aware_graph_hybrid.yaml"
        assert path.exists(), "schema_aware_graph_hybrid.yaml must exist (default chat profile)"
