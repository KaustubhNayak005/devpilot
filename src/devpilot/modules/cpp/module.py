"""C/C++ module — installs GCC, Clang, CMake, GDB, Make and verifies the toolchain."""

import logging
import shutil
import tempfile
from pathlib import Path

from devpilot.modules.base import BaseModule, CheckResult
from devpilot.utils.shell import apt_install, run_command, which

logger = logging.getLogger("devpilot")


class CppModule(BaseModule):
    """Installs the C/C++ build toolchain (GCC, Clang, CMake, GDB, Make)."""

    name: str = "cpp"
    dependencies: list[str] = []

    def install(self) -> bool:
        """Install build-essential, clang, cmake, gdb, make and smoke-test with hello world.

        Returns:
            True if the toolchain compiles and runs successfully, False otherwise.
        """
        pkgs = ["build-essential", "gcc", "g++", "clang", "cmake", "gdb", "make"]
        if not apt_install(pkgs):
            logger.error("Failed to install C/C++ packages via apt.")
            return False

        if not which("g++"):
            logger.error("g++ not found after installation.")
            return False

        # Smoke-test: compile + run hello world
        tmp_dir = Path(tempfile.mkdtemp(prefix="devpilot-cpp-test-"))
        hello_cpp = tmp_dir / "hello.cpp"
        hello_bin = tmp_dir / "hello"
        try:
            hello_cpp.write_text(
                "#include <iostream>\n"
                'int main() { std::cout << "Hello from DevPilot"'
                "<< std::endl; return 0; }"
            )
            compile_result = run_command(
                ["g++", "-std=c++17", str(hello_cpp), "-o", str(hello_bin)],
                capture=True,
                check=False,
            )
            if compile_result.returncode != 0:
                logger.error(f"Hello world compilation failed: {compile_result.stderr}")
                return False

            run_result = run_command([str(hello_bin)], capture=True, check=False)
            if "Hello from DevPilot" not in (run_result.stdout or ""):
                logger.error("Hello world binary did not produce expected output.")
                return False
            logger.info("C++ toolchain smoke-test passed.")
        except OSError as exc:
            logger.error(f"Smoke-test failed: {exc}")
            return False
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)

        return True

    def verify(self) -> list[CheckResult]:
        """Verify each C/C++ tool is available.

        Returns:
            List of CheckResult objects.
        """
        tools = {
            "gcc": "gcc",
            "g++": "g++",
            "clang": "clang",
            "cmake": "cmake",
            "gdb": "gdb",
            "make": "make",
        }
        results: list[CheckResult] = []

        for name, binary in tools.items():
            tool_path = which(binary)
            if tool_path:
                ver = run_command([binary, "--version"], capture=True, check=False)
                first_line = (ver.stdout or "").split("\n")[0].strip()
                results.append(
                    CheckResult(
                        name=f"{name} installed",
                        passed=True,
                        message=first_line or f"Found at {tool_path}",
                    )
                )
            else:
                results.append(
                    CheckResult(
                        name=f"{name} installed",
                        passed=False,
                        message=f"{binary} not found.",
                        fix=f"Run: sudo apt install {name}",
                    )
                )

        # Quick compile check
        compile_check = True
        tmp_dir = Path(tempfile.mkdtemp(prefix="devpilot-cpp-verify-"))
        tmp_src = tmp_dir / "test.cpp"
        tmp_bin = tmp_dir / "test.out"
        try:
            tmp_src.write_text("int main() { return 0; }")
            comp = run_command(
                ["g++", "-std=c++17", str(tmp_src), "-o", str(tmp_bin)],
                capture=True,
                check=False,
            )
            compile_check = comp.returncode == 0
        except (OSError, FileNotFoundError):
            compile_check = False
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)

        results.append(
            CheckResult(
                name="g++ can compile",
                passed=compile_check,
                message=(
                    "Can compile a trivial C++ program"
                    if compile_check
                    else "C++ compilation failed."
                ),
                fix=None if compile_check else "Run: sudo apt install build-essential",
            )
        )

        return results

    def doctor(self) -> list[CheckResult]:
        """Run comprehensive health checks for C/C++ toolchain.

        Returns:
            List of CheckResult objects (delegates to verify).
        """
        return self.verify()
