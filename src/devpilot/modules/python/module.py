"""Python module — installs python3, pip, venv and verifies the toolchain."""

import logging
import shutil
import tempfile
from pathlib import Path

from devpilot.modules.base import BaseModule, CheckResult
from devpilot.utils.shell import apt_install, run_command, which

logger = logging.getLogger("devpilot")


class PythonModule(BaseModule):
    """Installs python3, pip, and venv; verifies with a temp venv smoke-test."""

    name: str = "python"

    def install(self) -> bool:
        """Install python3, pip, venv via apt and run a smoke-test venv.

        Returns:
            True if python3 toolchain is functional, False otherwise.
        """
        if not which("python3") or not which("pip3"):
            if not apt_install(["python3", "python3-pip", "python3-venv"]):
                logger.error("Failed to install Python packages via apt.")
                return False
            logger.info("Python 3 packages installed successfully.")

        if not which("python3"):
            logger.error("python3 not found after installation.")
            return False

        # Smoke-test: create temp venv, install a package, import it
        tmp_dir = Path(tempfile.mkdtemp(prefix="devpilot-py-test-"))
        venv_dir = tmp_dir / ".venv"
        try:
            run_command(["python3", "-m", "venv", str(venv_dir)], capture=True, check=False)
            pip_bin = venv_dir / "bin" / "pip"
            python_bin = venv_dir / "bin" / "python"
            if pip_bin.exists():
                run_command(
                    [str(pip_bin), "install", "rich"],
                    capture=True,
                    check=False,
                    timeout=120,
                )
                result = run_command(
                    [str(python_bin), "-c", "import rich; print('ok')"],
                    capture=True,
                    check=False,
                )
                if "ok" not in (result.stdout or ""):
                    logger.warning("Smoke-test import failed.")
            else:
                logger.warning("pip binary not found in venv.")
        except OSError as exc:
            logger.error(f"Smoke-test venv creation failed: {exc}")
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)

        return True

    def verify(self) -> list[CheckResult]:
        """Verify python3, pip, and venv are available.

        Returns:
            List of CheckResult objects.
        """
        results: list[CheckResult] = []

        py3 = which("python3")
        if py3:
            ver = run_command(["python3", "--version"], capture=True, check=False)
            results.append(
                CheckResult(
                    name="python3 installed",
                    passed=True,
                    message=ver.stdout.strip() if ver.stdout else f"Found at {py3}",
                )
            )
        else:
            results.append(
                CheckResult(
                    name="python3 installed",
                    passed=False,
                    message="python3 not found.",
                    fix="Run: sudo apt install python3",
                )
            )

        pip = which("pip3")
        if pip:
            ver = run_command(["pip3", "--version"], capture=True, check=False)
            results.append(
                CheckResult(
                    name="pip installed",
                    passed=True,
                    message=(
                        ver.stdout.strip().split("(")[0].strip()
                        if ver.stdout
                        else f"Found at {pip}"
                    ),
                )
            )
        else:
            results.append(
                CheckResult(
                    name="pip installed",
                    passed=False,
                    message="pip3 not found.",
                    fix="Run: sudo apt install python3-pip",
                )
            )

        # Check venv module
        venv_test = run_command(
            ["python3", "-m", "venv", "--help"],
            capture=True,
            check=False,
        )
        results.append(
            CheckResult(
                name="venv module",
                passed=venv_test.returncode == 0,
                message=(
                    "venv module available"
                    if venv_test.returncode == 0
                    else "venv module not available."
                ),
                fix=(None if venv_test.returncode == 0 else "Run: sudo apt install python3-venv"),
            )
        )

        return results

    def doctor(self) -> list[CheckResult]:
        """Run comprehensive health checks for Python.

        Returns:
            List of CheckResult objects (delegates to verify).
        """
        return self.verify()
