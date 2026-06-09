"""Tests for devpilot.inspector.detector, checker, and installer."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from devpilot.inspector.checker import check_tools
from devpilot.inspector.detector import detect_stack
from devpilot.inspector.installer import MANUAL_INSTALL, install_missing


class TestDetector:
    """Tests for project stack detection."""

    def test_detects_python_via_pyproject_toml(self, tmp_path: Path):
        """A directory with pyproject.toml is detected as Python."""
        (tmp_path / "pyproject.toml").write_text("[project]\n", encoding="utf-8")
        results = detect_stack(str(tmp_path))
        assert any(r.name == "Python" for r in results)

    def test_detects_node_via_package_json(self, tmp_path: Path):
        """A directory with package.json is detected as Node.js."""
        (tmp_path / "package.json").write_text("{}", encoding="utf-8")
        results = detect_stack(str(tmp_path))
        assert any(r.name == "Node.js" for r in results)

    def test_detects_cpp_via_cmakelists(self, tmp_path: Path):
        """A directory with CMakeLists.txt is detected as C++ / CMake."""
        (tmp_path / "CMakeLists.txt").write_text(
            "cmake_minimum_required(VERSION 3.16)", encoding="utf-8"
        )
        results = detect_stack(str(tmp_path))
        assert any(r.name == "C++ / CMake" for r in results)

    def test_detects_rust_via_cargo_toml(self, tmp_path: Path):
        """A directory with Cargo.toml is detected as Rust."""
        (tmp_path / "Cargo.toml").write_text("[package]\n", encoding="utf-8")
        results = detect_stack(str(tmp_path))
        assert any(r.name == "Rust" for r in results)

    def test_detects_go_via_gomod(self, tmp_path: Path):
        """A directory with go.mod is detected as Go."""
        (tmp_path / "go.mod").write_text("module example\n", encoding="utf-8")
        results = detect_stack(str(tmp_path))
        assert any(r.name == "Go" for r in results)

    def test_detects_flutter_via_pubspec(self, tmp_path: Path):
        """A directory with pubspec.yaml is detected as Flutter."""
        (tmp_path / "pubspec.yaml").write_text("name: test\n", encoding="utf-8")
        results = detect_stack(str(tmp_path))
        assert any(r.name == "Flutter" for r in results)

    def test_detects_docker_via_dockerfile(self, tmp_path: Path):
        """A directory with Dockerfile is detected as Docker."""
        (tmp_path / "Dockerfile").write_text("FROM ubuntu:22.04\n", encoding="utf-8")
        results = detect_stack(str(tmp_path))
        assert any(r.name == "Docker" for r in results)

    def test_detects_github_actions(self, tmp_path: Path):
        """A directory with .github/workflows/*.yml is detected as GitHub Actions."""
        workflows_dir = tmp_path / ".github" / "workflows"
        workflows_dir.mkdir(parents=True)
        (workflows_dir / "ci.yml").write_text("name: CI\n", encoding="utf-8")
        results = detect_stack(str(tmp_path))
        assert any(r.name == "GitHub Actions" for r in results)

    def test_empty_directory_returns_empty(self, tmp_path: Path):
        """An empty directory returns an empty list."""
        results = detect_stack(str(tmp_path))
        assert results == []

    def test_confidence_is_definite_for_primary_match(self, tmp_path: Path):
        """A project.toml match has 'definite' confidence."""
        (tmp_path / "pyproject.toml").write_text("[project]\n", encoding="utf-8")
        results = detect_stack(str(tmp_path))
        python_result = next(r for r in results if r.name == "Python")
        assert python_result.confidence == "definite"

    def test_detects_cmake_files_with_likely_confidence(self, tmp_path: Path):
        """A *.cmake file alone gives 'likely' confidence."""
        (tmp_path / "project.cmake").write_text("set(VAR ON)", encoding="utf-8")
        results = detect_stack(str(tmp_path))
        cmake_result = next((r for r in results if r.name == "C++ / CMake"), None)
        assert cmake_result is not None
        assert cmake_result.confidence == "likely"


class TestChecker:
    """Tests for tool availability checking."""

    def test_check_tools_all_found(self):
        """check_tools returns True for all tools when which succeeds."""
        with patch("devpilot.inspector.checker.which", return_value=Path("/usr/bin/tool")):
            result = check_tools(["python3", "nodejs", "gcc"])
        assert result == {"python3": True, "nodejs": True, "gcc": True}

    def test_check_tools_all_missing(self):
        """check_tools returns False for all tools when which fails."""
        with patch("devpilot.inspector.checker.which", return_value=None):
            result = check_tools(["python3", "nodejs"])
        assert result == {"python3": False, "nodejs": False}

    def test_check_tools_mixed(self):
        """check_tools returns correct mix of True/False."""

        def fake_which(program: str) -> Path | None:
            return Path(f"/usr/bin/{program}") if program == "python3" else None

        with patch("devpilot.inspector.checker.which", side_effect=fake_which):
            result = check_tools(["python3", "nodejs"])
        assert result == {"python3": True, "nodejs": False}


class TestInstaller:
    """Tests for tool installation."""

    def test_install_missing_success(self):
        """install_missing returns True when apt-get succeeds."""
        with patch("devpilot.inspector.installer.run_command") as mock_run:
            mock_result = MagicMock()
            mock_result.returncode = 0
            mock_run.return_value = mock_result

            result = install_missing("cmake")

        assert result is True
        mock_run.assert_called_once()

    def test_install_missing_failure(self):
        """install_missing returns False when apt-get fails."""
        with patch("devpilot.inspector.installer.run_command") as mock_run:
            mock_result = MagicMock()
            mock_result.returncode = 1
            mock_run.return_value = mock_result

            result = install_missing("cmake")

        assert result is False

    def test_install_missing_manual_tool(self):
        """install_missing returns False for manual-install tools."""
        result = install_missing("flutter")
        assert result is False
        assert "flutter" in MANUAL_INSTALL

    def test_install_missing_unknown_tool(self):
        """install_missing returns False for unknown tools."""
        result = install_missing("nonexistent-tool-xyz")
        assert result is False
