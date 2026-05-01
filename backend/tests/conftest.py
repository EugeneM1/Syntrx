"""Shared fixtures."""

from __future__ import annotations

import os
import sys
from pathlib import Path

# Make `app.*` importable from anywhere
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# Force the deterministic LLM in every test
os.environ.setdefault("LLM_PROVIDER", "mock")
os.environ.setdefault("DATABASE_URL", "sqlite:///./test.db")

import pytest  # noqa: E402

from scripts.generate_sample_data import PROFILES, write_profile  # noqa: E402


@pytest.fixture(scope="session")
def sample_dir(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Generate every synthetic profile once per session into a tmp dir."""
    out = tmp_path_factory.mktemp("samples")
    for profile in PROFILES:
        write_profile(profile, out)
    return out


@pytest.fixture(scope="session")
def sample_files(sample_dir: Path) -> dict[str, Path]:
    return {p.name.replace("sample_", "").replace(".txt", ""):
            p for p in sorted(sample_dir.glob("sample_*.txt"))}
