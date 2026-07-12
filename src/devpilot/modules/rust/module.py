"""Rust module — installs the Rust toolchain via rustup."""

import logging
import tempfile
from pathlib import Path

from devpilot.modules.base import BaseModule, CheckResult
from devpilot.utils.shell import run_command, which

logger = logging.getLogger("devpilot")

CARGO_BIN = Path.home() / ".cargo" / "bin"


def _find_tool(binary: str) -> Path | None:
    """Find a Rust tool on PATH or in ~/.cargo/bin (not yet sourced shells)."""
    found = which(binary)
    if found:
        return found
    candidate = CARGO_BIN / binary
    return candidate if candidate.exists() else None


class RustModule(BaseModule):
    """Installs rustup, rustc, and cargo via the official rustup installer."""

    name: str = "rust"
    dependencies: list[str] = []

    def install(self) -> bool:
        """Install the Rust toolchain non-interactively via rustup.

        Returns:
            True if cargo is available after installation, False otherwise.
        """
        if _find_tool("cargo"):
            logger.info("Rust toolchain already present.")
            return True

        logger.info("Downloading rustup installer...")
        curl_result = run_command(
            ["curl", "--proto", "=https", "--tlsv1.2", "-sSf", "https://sh.rustup.rs"],
            capture=True,
            check=False,
            timeout=120,
        )
        if curl_result.returncode != 0 or not curl_result.stdout:
            logger.error("Failed to download rustup installer.")
            return False

        tmp_file = tempfile.NamedTemporaryFile(suffix=".sh", mode="w", delete=False)
        script_path = Path(tmp_file.name)
        tmp_file.write(curl_result.stdout)
        tmp_file.close()
        try:
            result = run_command(
                ["sh", str(script_path), "-y"],
                capture=True,
                check=False,
                timeout=600,
            )
        finally:
            script_path.unlink(missing_ok=True)

        if result.returncode != 0:
            logger.error("rustup installer failed.")
            return False

        if not _find_tool("cargo"):
            logger.error("cargo not found after rustup install.")
            return False

        logger.info("Rust toolchain installed. Restart your shell to pick up ~/.cargo/bin.")
        return True

    def verify(self) -> list[CheckResult]:
        """Verify rustc and cargo are available.

        Returns:
            List of CheckResult objects.
        """
        results: list[CheckResult] = []
        for binary in ("rustc", "cargo"):
            tool_path = _find_tool(binary)
            if tool_path:
                ver = run_command([str(tool_path), "--version"], capture=True, check=False)
                message = (ver.stdout or "").strip() or f"Found at {tool_path}"
                results.append(
                    CheckResult(name=f"{binary} installed", passed=True, message=message)
                )
            else:
                results.append(
                    CheckResult(
                        name=f"{binary} installed",
                        passed=False,
                        message=f"{binary} not found in PATH or ~/.cargo/bin.",
                        fix="Run: devpilot setup rust",
                    )
                )
        return results

    def doctor(self) -> list[CheckResult]:
        """Run comprehensive health checks for the Rust toolchain.

        Returns:
            List of CheckResult objects (delegates to verify).
        """
        return self.verify()
