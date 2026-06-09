"""Node.js module — installs Node.js LTS and TypeScript globally."""

import logging
import tempfile
from pathlib import Path

from devpilot.modules.base import BaseModule, CheckResult
from devpilot.utils.shell import apt_install, run_command, which

logger = logging.getLogger("devpilot")


class NodeModule(BaseModule):
    """Installs Node.js LTS via NodeSource and TypeScript globally."""

    name: str = "node"

    def install(self) -> bool:
        """Install Node.js LTS and TypeScript.

        Returns:
            True if node and npm are available, False otherwise.
        """
        if not which("node"):
            logger.info("Adding NodeSource LTS repository...")
            run_command(
                ["sudo", "apt-get", "update"],
                capture=True,
                check=False,
                timeout=120,
            )
            # Use NodeSource setup script
            curl_result = run_command(
                ["curl", "-fsSL", "https://deb.nodesource.com/setup_lts.x"],
                capture=True,
                check=False,
                timeout=120,
            )
            if curl_result.returncode != 0:
                logger.error("Failed to fetch NodeSource setup script.")
                return False

            # Write NodeSource setup script to a temp file and execute it
            tmp_file = tempfile.NamedTemporaryFile(suffix=".sh", mode="w", delete=False)
            script_path = Path(tmp_file.name)
            tmp_file.write(curl_result.stdout)
            tmp_file.close()
            try:
                run_command(
                    ["sudo", "bash", str(script_path)],
                    capture=True,
                    check=False,
                    timeout=120,
                )
            finally:
                script_path.unlink(missing_ok=True)

            if not apt_install(["nodejs"]):
                logger.error("Failed to install nodejs.")
                return False
            logger.info("Node.js installed successfully.")

        if not which("node"):
            logger.error("node not found after installation.")
            return False

        if not which("tsc"):
            logger.info("Installing TypeScript globally...")
            result = run_command(
                ["sudo", "npm", "install", "-g", "typescript"],
                capture=True,
                check=False,
                timeout=300,
            )
            if result.returncode != 0:
                logger.warning("TypeScript installation failed — non-fatal.")
            else:
                logger.info("TypeScript installed globally.")

        return True

    def verify(self) -> list[CheckResult]:
        """Verify Node.js, npm, and TypeScript are available.

        Returns:
            List of CheckResult objects.
        """
        results: list[CheckResult] = []

        node = which("node")
        if node:
            ver = run_command(["node", "--version"], capture=True, check=False)
            results.append(
                CheckResult(
                    name="node installed",
                    passed=True,
                    message=ver.stdout.strip() if ver.stdout else f"Found at {node}",
                )
            )
        else:
            results.append(
                CheckResult(
                    name="node installed",
                    passed=False,
                    message="node not found.",
                    fix="Run: devpilot setup node",
                )
            )

        npm = which("npm")
        if npm:
            ver = run_command(["npm", "--version"], capture=True, check=False)
            results.append(
                CheckResult(
                    name="npm installed",
                    passed=True,
                    message=ver.stdout.strip() if ver.stdout else f"Found at {npm}",
                )
            )
        else:
            results.append(
                CheckResult(
                    name="npm installed",
                    passed=False,
                    message="npm not found.",
                    fix="Run: devpilot setup node",
                )
            )

        tsc = which("tsc")
        if tsc:
            results.append(
                CheckResult(
                    name="TypeScript installed",
                    passed=True,
                    message=f"Found at {tsc}",
                )
            )
        else:
            results.append(
                CheckResult(
                    name="TypeScript installed",
                    passed=False,
                    message="tsc not found.",
                    fix="Run: sudo npm install -g typescript",
                )
            )

        return results

    def doctor(self) -> list[CheckResult]:
        """Run comprehensive health checks for Node.js.

        Returns:
            List of CheckResult objects (delegates to verify).
        """
        return self.verify()
