"""Shared pytest fixtures."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]


def _load_yaml(relative_path: str) -> dict:
    """Load a YAML file relative to the repository root."""
    path = REPO_ROOT / relative_path
    assert path.exists(), f"missing file: {relative_path}"
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


@pytest.fixture(scope="session")
def config() -> dict:
    """The frozen world configuration."""
    return _load_yaml("generator/config.yml")


@pytest.fixture(scope="session")
def network() -> dict:
    """The frozen station roster."""
    return _load_yaml("generator/network.yml")


@pytest.fixture(scope="session")
def stations(network: dict) -> list[dict]:
    """The list of station records."""
    return network["stations"]