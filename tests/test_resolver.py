"""Tests for devpilot.modules.resolver — topological sort for install order."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from devpilot.modules.resolver import resolve_install_order


def _make_module(name: str, deps: list[str] | None = None) -> MagicMock:
    module = MagicMock()
    module.name = name
    module.dependencies = deps or []
    return module


class TestResolveInstallOrder:
    """Tests for resolve_install_order function."""

    def test_no_deps_returns_all_in_any_order(self):
        """With no dependencies, all modules are returned."""
        modules = {
            "git": _make_module("git"),
            "python": _make_module("python"),
            "node": _make_module("node"),
        }
        result = resolve_install_order(modules)
        assert len(result) == 3
        assert set(result) == {"git", "python", "node"}

    def test_dependency_comes_before_dependent(self):
        """A dependency is ordered before the module that needs it."""
        modules = {
            "python": _make_module("python", ["git"]),
            "git": _make_module("git"),
        }
        result = resolve_install_order(modules)
        assert result.index("git") < result.index("python")

    def test_multiple_dependencies_ordered_correctly(self):
        """Chain: node→python→git — all come in correct order."""
        modules = {
            "node": _make_module("node", ["python"]),
            "python": _make_module("python", ["git"]),
            "git": _make_module("git"),
        }
        result = resolve_install_order(modules)
        assert result.index("git") < result.index("python")
        assert result.index("python") < result.index("node")

    def test_circular_dependency_raises_value_error(self):
        """A circular dependency raises ValueError."""
        modules = {
            "a": _make_module("a", ["b"]),
            "b": _make_module("b", ["a"]),
        }
        with pytest.raises(ValueError, match="Circular dependency"):
            resolve_install_order(modules)

    def test_unknown_dependency_skipped_silently(self):
        """A dependency on an unknown module is ignored."""
        modules = {
            "python": _make_module("python", ["nonexistent"]),
            "git": _make_module("git"),
        }
        result = resolve_install_order(modules)
        assert set(result) == {"python", "git"}

    def test_diamond_dependency_resolves_correctly(self):
        """Diamond: c→a, c→b, b→a — all ordered correctly."""
        modules = {
            "a": _make_module("a"),
            "b": _make_module("b", ["a"]),
            "c": _make_module("c", ["a", "b"]),
        }
        result = resolve_install_order(modules)
        assert result.index("a") < result.index("b")
        assert result.index("a") < result.index("c")
        assert result.index("b") < result.index("c")
