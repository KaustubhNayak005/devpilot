"""Docker module — installs the Docker engine and configures group access."""

import logging
import os

from devpilot.modules.base import BaseModule, CheckResult
from devpilot.utils.shell import apt_install, run_command, which

logger = logging.getLogger("devpilot")


class DockerModule(BaseModule):
    """Installs docker.io, adds the user to the docker group, starts the service."""

    name: str = "docker"
    dependencies: list[str] = []

    def install(self) -> bool:
        """Install Docker engine, configure group access, and start the daemon.

        Returns:
            True if the docker CLI is available afterwards, False otherwise.
        """
        if not which("docker"):
            if not apt_install(["docker.io"]):
                logger.error("Failed to install docker.io via apt.")
                return False
            logger.info("Docker engine installed.")

        if not which("docker"):
            logger.error("docker not found after installation.")
            return False

        user = os.environ.get("USER", "")
        if user:
            result = run_command(
                ["sudo", "usermod", "-aG", "docker", user],
                capture=True,
                check=False,
            )
            if result.returncode == 0:
                logger.info(
                    f"Added {user} to the docker group — log out and back in to apply."
                )
            else:
                logger.warning("Could not add user to the docker group.")

        # WSL2 distros often lack systemd; `service` works either way.
        run_command(["sudo", "service", "docker", "start"], capture=True, check=False)
        return True

    def verify(self) -> list[CheckResult]:
        """Verify docker CLI, daemon reachability, and group membership.

        Returns:
            List of CheckResult objects.
        """
        results: list[CheckResult] = []

        docker_path = which("docker")
        if docker_path:
            ver = run_command(["docker", "--version"], capture=True, check=False)
            results.append(
                CheckResult(
                    name="docker installed",
                    passed=True,
                    message=(ver.stdout or "").strip() or f"Found at {docker_path}",
                )
            )
        else:
            results.append(
                CheckResult(
                    name="docker installed",
                    passed=False,
                    message="docker not found in PATH.",
                    fix="Run: devpilot setup docker",
                )
            )
            return results

        info = run_command(["docker", "info"], capture=True, check=False, timeout=15)
        daemon_up = info.returncode == 0
        results.append(
            CheckResult(
                name="docker daemon",
                passed=daemon_up,
                message=(
                    "Daemon is running"
                    if daemon_up
                    else "Daemon not reachable — is the service started?"
                ),
                fix=None if daemon_up else "Run: sudo service docker start",
            )
        )

        groups = run_command(["id", "-nG"], capture=True, check=False)
        in_group = "docker" in (groups.stdout or "").split()
        results.append(
            CheckResult(
                name="docker group",
                passed=in_group,
                message=(
                    "User is in the docker group"
                    if in_group
                    else "User is not in the docker group (docker needs sudo)."
                ),
                fix=(
                    None
                    if in_group
                    else "Run: sudo usermod -aG docker $USER (then log out and back in)"
                ),
            )
        )

        return results

    def doctor(self) -> list[CheckResult]:
        """Run comprehensive health checks for Docker.

        Returns:
            List of CheckResult objects (delegates to verify).
        """
        return self.verify()
