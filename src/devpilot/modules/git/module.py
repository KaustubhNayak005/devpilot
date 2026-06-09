"""Git module — installs git and configures global user.name/user.email."""

import logging

from devpilot.modules.base import BaseModule, CheckResult
from devpilot.utils.shell import apt_install, run_command, which

logger = logging.getLogger("devpilot")


class GitModule(BaseModule):
    """Installs git and ensures global user identity is configured."""

    name: str = "git"
    dependencies: list[str] = []

    def install(self) -> bool:
        """Install git via apt and prompt for global config if missing.

        Returns:
            True if git is available and config is set, False otherwise.
        """
        if not which("git"):
            if not apt_install(["git"]):
                logger.error("Failed to install git via apt.")
                return False
            logger.info("git installed successfully.")

        git_path = which("git")
        if not git_path:
            logger.error("git not found after installation.")
            return False

        name = self._get_git_config("user.name")
        if not name:
            try:
                name = input("Enter your full name for git [user.name]: ").strip()
            except (EOFError, KeyboardInterrupt):
                logger.warning("No git user.name configured.")
            if name:
                run_command(["git", "config", "--global", "user.name", name], check=False)
                logger.info(f"git user.name set to '{name}'.")

        email = self._get_git_config("user.email")
        if not email:
            try:
                email = input("Enter your email for git [user.email]: ").strip()
            except (EOFError, KeyboardInterrupt):
                logger.warning("No git user.email configured.")
            if email:
                run_command(["git", "config", "--global", "user.email", email], check=False)
                logger.info(f"git user.email set to '{email}'.")

        return True

    def verify(self) -> list[CheckResult]:
        """Verify git is installed and global identity is configured.

        Returns:
            List of CheckResult objects.
        """
        results: list[CheckResult] = []

        git_path = which("git")
        if git_path:
            version = run_command(["git", "--version"], capture=True, check=False)
            results.append(
                CheckResult(
                    name="git installed",
                    passed=True,
                    message=version.stdout.strip() if version.stdout else f"Found at {git_path}",
                )
            )
        else:
            results.append(
                CheckResult(
                    name="git installed",
                    passed=False,
                    message="git not found in PATH.",
                    fix="Run: sudo apt install git",
                )
            )

        name = self._get_git_config("user.name")
        results.append(
            CheckResult(
                name="git user.name",
                passed=bool(name),
                message=f"Configured as '{name}'" if name else "Not set.",
                fix=None if name else "Run: git config --global user.name 'Your Name'",
            )
        )

        email = self._get_git_config("user.email")
        results.append(
            CheckResult(
                name="git user.email",
                passed=bool(email),
                message=f"Configured as '{email}'" if email else "Not set.",
                fix=None if email else "Run: git config --global user.email 'your@email.com'",
            )
        )

        return results

    def doctor(self) -> list[CheckResult]:
        """Run comprehensive health checks for git.

        Returns:
            List of CheckResult objects (delegates to verify).
        """
        return self.verify()

    def _get_git_config(self, key: str) -> str:
        """Return the value of a git global config key, or empty string."""
        result = run_command(["git", "config", "--global", key], capture=True, check=False)
        return result.stdout.strip() if result.returncode == 0 and result.stdout else ""
