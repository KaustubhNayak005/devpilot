"""Base module abstract class and shared data types."""

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class CheckResult:
    """Result of a single health check or verification step.

    Attributes:
        name: Human-readable check name, e.g. "git installed".
        passed: Whether the check passed.
        message: Descriptive message about the check result.
        fix: Suggested fix command or instruction, if the check failed.
    """

    name: str
    passed: bool
    message: str
    fix: str | None = None


class BaseModule(ABC):
    """Abstract base for all DevPilot install modules.

    Subclasses must define:
        name: A human-readable module name (class attribute).
        install(): Install the module's tools.
        verify(): Run real-time verification checks.
        doctor(): Run comprehensive health checks.
    """

    name: str

    @abstractmethod
    def install(self) -> bool:
        """Install the module's tools and configuration.

        Returns:
            True if installation succeeded, False otherwise.
        """
        ...

    @abstractmethod
    def verify(self) -> list[CheckResult]:
        """Verify the module's tools are correctly installed and configured.

        Returns:
            A list of CheckResult objects, one per verification step.
        """
        ...

    @abstractmethod
    def doctor(self) -> list[CheckResult]:
        """Run comprehensive health checks for the module.

        Returns:
            A list of CheckResult objects covering all health dimensions.
        """
        ...
