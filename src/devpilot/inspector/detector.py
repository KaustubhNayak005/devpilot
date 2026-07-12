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


@dataclass(frozen=True)
class DetectionRule:
    """An immutable detection rule.

    Attributes:
        pattern: Exact filename ("Cargo.toml") or extension glob ("*.cmake").
        primary: True if a match gives "definite" confidence, else "likely".
        stack: Stack name this rule detects.
        tools: Tools required by the stack.
    """

    pattern: str
    primary: bool
    stack: str
    tools: tuple[str, ...]


DETECTION_RULES: tuple[DetectionRule, ...] = (
    DetectionRule("pubspec.yaml", True, "Flutter", ("flutter", "dart", "android-sdk", "java-17")),
    DetectionRule("CMakeLists.txt", True, "C++ / CMake", ("cmake", "ninja-build", "clangd", "gcc")),
    DetectionRule("*.cmake", False, "C++ / CMake", ("cmake", "ninja-build", "clangd", "gcc")),
    DetectionRule("Cargo.toml", True, "Rust", ("rustup", "cargo")),
    DetectionRule("go.mod", True, "Go", ("golang",)),
    DetectionRule("package.json", True, "Node.js", ("nodejs", "npm")),
    DetectionRule("requirements.txt", True, "Python", ("python3", "pip")),
    DetectionRule("pyproject.toml", True, "Python", ("python3", "pip")),
    DetectionRule("Dockerfile", True, "Docker", ("docker", "docker-compose")),
)


def _rule_matches(rule: DetectionRule, seen_files: set[str]) -> bool:
    """Check whether a rule's pattern matches any collected filename."""
    if rule.pattern.startswith("*."):
        ext = rule.pattern[1:]
        return any(fname.endswith(ext) for fname in seen_files)
    return rule.pattern in seen_files


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


def _collect_filenames(root: Path, max_depth: int = 3) -> set[str]:
    """Collect file names in the tree up to max_depth, skipping hidden dirs."""
    seen_files: set[str] = set()
    for dirpath, dirnames, filenames in os.walk(root):
        rel = Path(dirpath).relative_to(root)
        depth = len(rel.parts) if str(rel) != "." else 0
        if depth > max_depth:
            dirnames.clear()
            continue
        dirnames[:] = [d for d in dirnames if not d.startswith(".")]
        seen_files.update(filenames)
    return seen_files


def detect_stack(path: str) -> list[StackRequirement]:
    """Scan a directory and detect development stacks.

    Walks the directory tree up to depth 3, skipping hidden directories,
    and checks for known project files. Returns fresh StackRequirement
    instances on every call — results are never shared or mutated globally.

    Args:
        path: Root directory path to scan.

    Returns:
        List of StackRequirement objects, sorted by confidence
        ("definite" first, then "likely").
    """
    root = Path(path).resolve()
    seen_files = _collect_filenames(root)

    # Merge rule matches per stack name; "definite" wins over "likely".
    detected: dict[str, StackRequirement] = {}
    for rule in DETECTION_RULES:
        if not _rule_matches(rule, seen_files):
            continue
        confidence = "definite" if rule.primary else "likely"
        existing = detected.get(rule.stack)
        if existing is None:
            detected[rule.stack] = StackRequirement(
                name=rule.stack,
                tools=list(rule.tools),
                confidence=confidence,
            )
        else:
            if confidence == "definite":
                existing.confidence = "definite"
            for tool in rule.tools:
                if tool not in existing.tools:
                    existing.tools.append(tool)

    results = list(detected.values())

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
