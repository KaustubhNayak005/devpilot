"""Tests for devpilot.config.manager.ConfigManager."""

from __future__ import annotations

from devpilot.config.manager import ConfigManager


def test_load_defaults_when_file_missing(config_manager: ConfigManager) -> None:
    """Loading a missing config returns defaults."""
    data = config_manager.load()
    assert data == {"installed_modules": [], "preferences": {}}


def test_save_and_load_roundtrip(config_manager: ConfigManager) -> None:
    """Saving and loading produces identical data."""
    data = {
        "installed_modules": ["git", "python"],
        "preferences": {"default_editor": "code"},
    }
    config_manager.save(data)
    loaded = config_manager.load()
    assert loaded == data


def test_mark_installed(config_manager: ConfigManager) -> None:
    """Marking a module as installed adds it to the list."""
    assert config_manager.get_installed_modules() == []
    config_manager.mark_installed("git")
    assert config_manager.get_installed_modules() == ["git"]
    # Mark again — no duplicate
    config_manager.mark_installed("git")
    assert config_manager.get_installed_modules() == ["git"]
    config_manager.mark_installed("python")
    assert config_manager.get_installed_modules() == ["git", "python"]


def test_get_preference_with_default(config_manager: ConfigManager) -> None:
    """get_preference returns the default when key is missing."""
    assert config_manager.get_preference("nonexistent", "fallback") == "fallback"


def test_get_and_set_preference(config_manager: ConfigManager) -> None:
    """Setting a preference and reading it back works."""
    config_manager.set_preference("default_editor", "nvim")
    assert config_manager.get_preference("default_editor") == "nvim"


def test_load_corrupted_yaml_returns_defaults(config_manager: ConfigManager) -> None:
    """A corrupted YAML file returns defaults."""
    config_manager.config_path.parent.mkdir(parents=True, exist_ok=True)
    config_manager.config_path.write_text("{ this is not valid yaml: [")
    data = config_manager.load()
    assert data == {"installed_modules": [], "preferences": {}}
