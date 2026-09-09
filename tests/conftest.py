"""Shared pytest fixtures."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]

# Make `generator` and `src` importable without packaging the project.
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def _load_yaml(relative_path: str) -> dict:
    """Load a YAML file relative to the repository root."""
    path = REPO_ROOT / relative_path
    assert path.exists(), f"missing file: {relative_path}"
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


@pytest.fixture(scope="session")
def repo_root() -> Path:
    """Absolute path to the repository root."""
    return REPO_ROOT


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
    """The raw list of station records from the roster."""
    return network["stations"]


@pytest.fixture(scope="session")
def world():
    """The static world, built from the frozen configuration."""
    from generator import world as world_module

    return world_module.build_world()