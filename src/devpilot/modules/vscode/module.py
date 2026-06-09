"""VS Code module — detects VS Code and validates WSL extension."""

import logging

from devpilot.modules.base import BaseModule, CheckResult
from devpilot.utils.shell import run_command, which

logger = logging.getLogger("devpilot")


class VSCodeModule(BaseModule):
    """Detects VS Code (via 'code' CLI) and verifies the WSL extension is installed."""

    name: str = "vscode"

    def install(self) -> bool:
        """Detect VS Code and advise on WSL extension.

        Returns:
            True if code is found, False with advice if not.
        """
        code_path = which("code")
        if code_path:
            logger.info(f"VS Code found at {code_path}.")
            return True

        logger.warning("VS Code CLI ('code') not found in PATH.")
        logger.warning(
            "Install VS Code on Windows, then run 'code' from WSL2 to set up the server."
        )
        return False

    def verify(self) -> list[CheckResult]:
        """Verify VS Code CLI and WSL extension.

        Returns:
            List of CheckResult objects.
        """
        results: list[CheckResult] = []

        code_path = which("code")
        if code_path:
            ver = run_command(["code", "--version"], capture=True, check=False)
            first_line = (ver.stdout or "").split("\n")[0].strip()
            results.append(
                CheckResult(
                    name="VS Code CLI",
                    passed=True,
                    message=f"Version {first_line}" if first_line else f"Found at {code_path}",
                )
            )
        else:
            results.append(
                CheckResult(
                    name="VS Code CLI",
                    passed=False,
                    message="code not found in PATH.",
                    fix="Install VS Code on Windows and launch from WSL2 terminal.",
                )
            )

        # Check WSL extension
        if code_path:
            ext_result = run_command(
                ["code", "--list-extensions"],
                capture=True,
                check=False,
            )
            has_wsl = "ms-vscode-remote.remote-wsl" in (ext_result.stdout or "")
            results.append(
                CheckResult(
                    name="WSL extension",
                    passed=has_wsl,
                    message=(
                        "Remote-WSL extension is installed"
                        if has_wsl
                        else "Remote-WSL extension not found."
                    ),
                    fix=(
                        None
                        if has_wsl
                        else "Run: code --install-extension ms-vscode-remote.remote-wsl"
                    ),
                )
            )
        else:
            results.append(
                CheckResult(
                    name="WSL extension",
                    passed=False,
                    message="Cannot check without VS Code CLI.",
                    fix="Install and launch VS Code from WSL2 first.",
                )
            )

        return results

    def doctor(self) -> list[CheckResult]:
        """Run comprehensive health checks for VS Code.

        Returns:
            List of CheckResult objects (delegates to verify).
        """
        return self.verify()
