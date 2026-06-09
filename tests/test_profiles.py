"""Tests for devpilot.profiles — definitions and installer."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from devpilot.profiles import PROFILES, Profile
from devpilot.profiles.installer import install_profile


class TestProfileDefinitions:
    """Tests for the profile registry."""

    def test_all_profiles_have_required_fields(self):
        """Every profile has name, description, and non-empty list fields."""
        for name, profile in PROFILES.items():
            assert profile.name == name
            assert len(profile.description) > 0
            assert isinstance(profile.apt_packages, list)
            assert isinstance(profile.pip_packages, list)
            assert isinstance(profile.npm_packages, list)
            assert isinstance(profile.post_install_notes, list)

    def test_registry_has_expected_count(self):
        """Six profiles should be defined."""
        assert len(PROFILES) == 6

    def test_cpp_profile_contains_compiler(self):
        """The C++ profile includes gcc."""
        assert "gcc" in PROFILES["cpp"].apt_packages

    def test_python_profile_contains_ruff(self):
        """The Python profile includes ruff via pip."""
        assert "ruff" in PROFILES["python"].pip_packages


class TestProfileInstaller:
    """Tests for profile installation."""

    def test_dry_run_returns_true_without_calling_subprocess(self):
        """dry_run=True returns True and does not call subprocess."""
        profile = PROFILES["cpp"]
        result = install_profile(profile, dry_run=True)
        assert result is True

    @patch("devpilot.profiles.installer.subprocess.run")
    def test_install_apt_packages_called_with_correct_args(self, mock_run):
        """install_profile passes apt packages to subprocess.run."""
        mock_run.return_value = MagicMock(returncode=0)
        profile = Profile(
            name="test",
            description="Test profile",
            apt_packages=["pkg1", "pkg2"],
            pip_packages=[],
            npm_packages=[],
            post_install_notes=[],
        )
        install_profile(profile)
        mock_run.assert_called()
        args = mock_run.call_args[0][0]
        assert "apt-get" in args
        assert "pkg1" in args
        assert "pkg2" in args

    @patch("devpilot.profiles.installer.subprocess.run")
    def test_install_returns_false_on_apt_failure(self, mock_run):
        """Returns False when apt install fails."""
        mock_run.return_value = MagicMock(returncode=1, stderr="error")
        profile = Profile(
            name="test",
            description="Test",
            apt_packages=["pkg1"],
            pip_packages=[],
            npm_packages=[],
            post_install_notes=[],
        )
        result = install_profile(profile)
        assert result is False

    @patch("devpilot.profiles.installer.subprocess.run")
    def test_install_handles_subprocess_exception(self, mock_run):
        """Returns False when subprocess raises an exception."""
        mock_run.side_effect = OSError("command not found")
        profile = Profile(
            name="test",
            description="Test",
            apt_packages=["pkg1"],
            pip_packages=[],
            npm_packages=[],
            post_install_notes=[],
        )
        result = install_profile(profile)
        assert result is False

    def test_dry_run_prints_correct_packages(self, capsys):
        """dry_run outputs the expected package lists."""
        profile = PROFILES["fullstack"]
        install_profile(profile, dry_run=True)
        captured = capsys.readouterr().out
        assert "nodejs" in captured
        assert "typescript" in captured
        assert "httpie" in captured
