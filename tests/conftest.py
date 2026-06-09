"""Shared test fixtures for DevPilot."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest

from devpilot.config.manager import ConfigManager


@pytest.fixture
def temp_config_dir(tmp_path: Path) -> Path:
    """Temporary config directory for isolated ConfigManager tests."""
    return tmp_path / "config"


@pytest.fixture
def config_manager(temp_config_dir: Path) -> ConfigManager:
    """Return a ConfigManager pointed at a temp directory."""
    config_path = temp_config_dir / "config.yaml"
    return ConfigManager(config_path=config_path)


@pytest.fixture
def mock_run_command() -> MagicMock:
    """Return a mock for devpilot.utils.shell.run_command."""
    return MagicMock()


@pytest.fixture
def mock_subprocess_run(request: Any) -> MagicMock:
    """Mock subprocess.run using mocker fixture (must be used via mocker fixture)."""
    return MagicMock()
