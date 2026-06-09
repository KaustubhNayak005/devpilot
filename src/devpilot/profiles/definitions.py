"""Developer profile definitions."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Profile:
    """A developer profile — a curated set of tools for a specific workflow.

    Attributes:
        name: Profile slug, used in the CLI command.
        description: One-line summary shown in profile list.
        apt_packages: Packages to install via apt.
        pip_packages: Packages to install via pip.
        npm_packages: Packages to install via npm -g.
        post_install_notes: Tips shown after installation.
    """

    name: str
    description: str
    apt_packages: list[str]
    pip_packages: list[str]
    npm_packages: list[str]
    post_install_notes: list[str]


PROFILES: dict[str, Profile] = {
    "cpp": Profile(
        name="cpp",
        description="C++ development — compiler, debugger, build tools, LSP",
        apt_packages=[
            "gcc",
            "g++",
            "clang",
            "clangd",
            "cmake",
            "ninja-build",
            "gdb",
            "valgrind",
            "make",
            "pkg-config",
        ],
        pip_packages=["conan"],
        npm_packages=[],
        post_install_notes=[
            "clangd is installed — configure your editor to use it for LSP.",
            "Conan package manager installed via pip for C++ dependencies.",
        ],
    ),
    "python": Profile(
        name="python",
        description="Python development — interpreter, linters, formatters, virtual envs",
        apt_packages=["python3", "python3-pip", "python3-venv"],
        pip_packages=["ruff", "mypy", "pytest", "ipython", "uv"],
        npm_packages=[],
        post_install_notes=[
            "Use 'uv' instead of pip for fast dependency resolution.",
            "Run 'python3 -m venv .venv' to create a virtual environment.",
        ],
    ),
    "flutter": Profile(
        name="flutter",
        description="Flutter / Dart mobile and web development",
        apt_packages=[
            "openjdk-17-jdk",
            "clang",
            "cmake",
            "ninja-build",
            "libgtk-3-dev",
            "pkg-config",
        ],
        pip_packages=[],
        npm_packages=[],
        post_install_notes=[
            "Flutter SDK must be installed manually:",
            "  https://docs.flutter.dev/get-started/install/linux",
            "After install, run: flutter doctor",
            "Android Studio must be installed separately for mobile builds.",
        ],
    ),
    "ai-engineer": Profile(
        name="ai-engineer",
        description="AI / ML development — Python stack, CUDA tools, popular frameworks",
        apt_packages=["python3", "python3-pip", "python3-venv", "git", "curl"],
        pip_packages=[
            "torch",
            "transformers",
            "datasets",
            "accelerate",
            "jupyter",
            "ipython",
            "ruff",
            "mypy",
            "uv",
        ],
        npm_packages=[],
        post_install_notes=[
            "PyTorch installed for CPU. For CUDA, reinstall with the correct index URL:",
            "  pip install torch --index-url https://download.pytorch.org/whl/cu121",
            "Run 'jupyter notebook' to start Jupyter.",
        ],
    ),
    "competitive-programming": Profile(
        name="competitive-programming",
        description="Competitive programming — fast compilers, debuggers, common tools",
        apt_packages=[
            "gcc",
            "g++",
            "clang",
            "gdb",
            "python3",
            "python3-pip",
            "time",
            "valgrind",
        ],
        pip_packages=["online-judge-tools"],
        npm_packages=[],
        post_install_notes=[
            "oj (online-judge-tools) installed for contest automation.",
            "Compile with: g++ -O2 -std=c++17 -o sol sol.cpp",
        ],
    ),
    "fullstack": Profile(
        name="fullstack",
        description="Full-stack web — Node.js, Python, Docker, common CLI tools",
        apt_packages=[
            "nodejs",
            "npm",
            "python3",
            "python3-pip",
            "docker.io",
            "docker-compose",
            "git",
            "curl",
            "jq",
        ],
        pip_packages=["httpie"],
        npm_packages=["typescript", "prettier", "eslint"],
        post_install_notes=[
            "Add your user to the docker group: sudo usermod -aG docker $USER",
            "Then log out and back in for docker group to take effect.",
        ],
    ),
}
