"""Configuration manager for DevPilot.

Reads and writes ~/.config/devpilot/config.yaml to track installed modules
and user preferences.
"""

from pathlib import Path
from typing import Any

import yaml

DEFAULT_CONFIG_PATH: Path = Path.home() / ".config" / "devpilot" / "config.yaml"


class ConfigManager:
    """Manages persistent DevPilot configuration via YAML file."""

    def __init__(self, config_path: Path | None = None) -> None:
        """Initialize the config manager.

        Args:
            config_path: Override the default config file location.
        """
        self.config_path = config_path or DEFAULT_CONFIG_PATH

    def load(self) -> dict[str, Any]:
        """Load the configuration from disk.

        Returns:
            Dictionary with keys 'installed_modules' (list) and
            'preferences' (dict). Returns defaults if the file does not exist.
        """
        if not self.config_path.exists():
            return {"installed_modules": [], "preferences": {}}
        try:
            data = self.config_path.read_text(encoding="utf-8")
            loaded = yaml.safe_load(data)
            if not isinstance(loaded, dict):
                return {"installed_modules": [], "preferences": {}}
            loaded.setdefault("installed_modules", [])
            loaded.setdefault("preferences", {})
            return loaded
        except (yaml.YAMLError, OSError):
            return {"installed_modules": [], "preferences": {}}

    def save(self, data: dict[str, Any]) -> None:
        """Save configuration to disk, creating parent directories as needed.

        Args:
            data: Configuration dictionary to persist.
        """
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        text = yaml.safe_dump(data, default_flow_style=False)
        self.config_path.write_text(text, encoding="utf-8")

    def get_installed_modules(self) -> list[str]:
        """Return the list of module names that have been installed."""
        return list(self.load().get("installed_modules", []))

    def mark_installed(self, module_name: str) -> None:
        """Record a module as installed.

        Args:
            module_name: The module name to add.
        """
        data = self.load()
        modules: list[str] = data.setdefault("installed_modules", [])
        if module_name not in modules:
            modules.append(module_name)
            self.save(data)

    def get_preference(self, key: str, default: str = "") -> str:
        """Retrieve a preference value by key.

        Args:
            key: Preference key.
            default: Fallback value if the key is not set.

        Returns:
            The preference value, or default.
        """
        prefs = self.load().get("preferences", {})
        return str(prefs.get(key, default))

    def set_preference(self, key: str, value: str) -> None:
        """Set a preference value.

        Args:
            key: Preference key.
            value: Value to store.
        """
        data = self.load()
        data.setdefault("preferences", {})[key] = value
        self.save(data)
