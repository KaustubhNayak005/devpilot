"""Project stack detector — scans directories for known project files."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass
class StackRequirement:
    """A detected development stack and the tools it requires.

    Attributes:
        name: Human-readable name of the stack, e.g. "Flutter".
        tools: List of tool names required for this stack.
        confidence: "definite" if a primary file matched, "likely" if secondary.
    """

    name: str
    tools: list[str]
    confidence: str


# Ordered list of (file_glob, primary, StackRequirement)
# "primary" means a match gives "definite" confidence; otherwise "likely".
DETECTION_RULES: list[tuple[str, bool, StackRequirement]] = [
    (
        "pubspec.yaml",
        True,
        StackRequirement(
            name="Flutter",
            tools=["flutter", "dart", "android-sdk", "java-17"],
            confidence="definite",
        ),
    ),
    (
        "CMakeLists.txt",
        True,
        StackRequirement(
            name="C++ / CMake",
            tools=["cmake", "ninja-build", "clangd", "gcc"],
            confidence="definite",
        ),
    ),
    (
        "*.cmake",
        False,
        StackRequirement(
            name="C++ / CMake",
            tools=["cmake", "ninja-build", "clangd", "gcc"],
            confidence="likely",
        ),
    ),
    (
        "Cargo.toml",
        True,
        StackRequirement(
            name="Rust",
            tools=["rustup", "cargo"],
            confidence="definite",
        ),
    ),
    (
        "go.mod",
        True,
        StackRequirement(
            name="Go",
            tools=["golang"],
            confidence="definite",
        ),
    ),
    (
        "package.json",
        True,
        StackRequirement(
            name="Node.js",
            tools=["nodejs", "npm"],
            confidence="definite",
        ),
    ),
    (
        "requirements.txt",
        True,
        StackRequirement(
            name="Python",
            tools=["python3", "pip"],
            confidence="definite",
        ),
    ),
    (
        "pyproject.toml",
        True,
        StackRequirement(
            name="Python",
            tools=["python3", "pip"],
            confidence="definite",
        ),
    ),
    (
        "Dockerfile",
        True,
        StackRequirement(
            name="Docker",
            tools=["docker", "docker-compose"],
            confidence="definite",
        ),
    ),
]


def _has_github_actions(path: str) -> bool:
    """Check if a directory tree contains GitHub Actions workflow files.

    Args:
        path: Root directory to scan.

    Returns:
        True if any .yml/.yaml files exist under .github/workflows/.
    """
    workflows_dir = Path(path) / ".github" / "workflows"
    if not workflows_dir.is_dir():
        return False
    for _ in workflows_dir.glob("*.yml"):
        return True
    for _ in workflows_dir.glob("*.yaml"):
        return True
    return False


def detect_stack(path: str) -> list[StackRequirement]:
    """Scan a directory and detect development stacks.

    Walks the directory tree up to depth 3, skipping hidden directories,
    and checks for known project files.

    Args:
        path: Root directory path to scan.

    Returns:
        List of StackRequirement objects, sorted by confidence
        ("definite" first, then "likely").
    """
    root = Path(path).resolve()
    seen_files: set[str] = set()

    for dirpath, dirnames, _filenames in os.walk(root):
        # Calculate depth relative to root
        rel = Path(dirpath).relative_to(root)
        depth = len(rel.parts) if str(rel) != "." else 0
        if depth > 3:
            dirnames.clear()
            continue

        # Skip hidden directories
        dirnames[:] = [d for d in dirnames if not d.startswith(".")]

        for entry in Path(dirpath).iterdir():
            if not entry.is_file():
                continue
            seen_files.add(entry.name)

    results: list[StackRequirement] = []

    # Check glob-based detection rules
    for file_glob, is_primary, req in DETECTION_RULES:
        if file_glob.startswith("*."):
            ext = file_glob[1:]
            for fname in seen_files:
                if fname.endswith(ext):
                    req.confidence = "definite" if is_primary else "likely"
                    if not any(r.name == req.name and r.confidence == "definite" for r in results):
                        results.append(req)
                    break
        else:
            if file_glob in seen_files:
                req.confidence = "definite" if is_primary else "likely"
                # Dedup by name — prefer "definite" over "likely"
                existing = next((r for r in results if r.name == req.name), None)
                if existing:
                    if req.confidence == "definite":
                        existing.confidence = "definite"
                else:
                    results.append(req)

    # Check GitHub Actions separately (it's a directory pattern)
    # Only check the root directly to avoid deep walks
    if _has_github_actions(str(root)):
        results.append(
            StackRequirement(
                name="GitHub Actions",
                tools=["gh"],
                confidence="definite",
            )
        )

    # Sort: "definite" first, then "likely"
    results.sort(key=lambda r: 0 if r.confidence == "definite" else 1)
    return results
