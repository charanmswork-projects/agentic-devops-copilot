from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from tools.log_parser import LogAnalysis, LogParser


@dataclass
class CICDAnalysis:
    success: bool
    errors: int
    warnings: int
    exceptions: int
    failed_tests: list[str]
    failed_jobs: list[str]
    stack_traces: list[str]
    likely_failure_area: str
    summary: str


class CICDAgent:
    def __init__(self):
        self.log_parser = LogParser()

    def analyze_log(
        self,
        log_text: str,
    ) -> CICDAnalysis:
        analysis = self.log_parser.parse(log_text)

        failure_area = self._identify_failure_area(
            analysis,
            log_text,
        )

        success = self._is_successful(analysis)

        return CICDAnalysis(
            success=success,
            errors=len(analysis.errors),
            warnings=len(analysis.warnings),
            exceptions=len(analysis.exceptions),
            failed_tests=analysis.failed_tests,
            failed_jobs=analysis.failed_jobs,
            stack_traces=analysis.stack_traces,
            likely_failure_area=failure_area,
            summary=self._build_summary(
                analysis,
                failure_area,
                success,
            ),
        )

    def analyze_log_file(
        self,
        log_path: str | Path,
    ) -> CICDAnalysis:
        path = Path(log_path)

        if not path.exists():
            raise FileNotFoundError(
                f"Log file not found: {path}"
            )

        if not path.is_file():
            raise ValueError(
                f"Path is not a file: {path}"
            )

        log_text = path.read_text(
            encoding="utf-8",
            errors="replace",
        )

        return self.analyze_log(log_text)

    def to_dict(
        self,
        analysis: CICDAnalysis,
    ) -> dict[str, Any]:
        return asdict(analysis)

    @staticmethod
    def _is_successful(
        analysis: LogAnalysis,
    ) -> bool:
        return not (
            analysis.errors
            or analysis.exceptions
            or analysis.failed_tests
            or analysis.failed_jobs
        )

    @staticmethod
    def _identify_failure_area(
        analysis: LogAnalysis,
        log_text: str,
    ) -> str:
        text = log_text.lower()

        if analysis.failed_tests:
            return "testing"

        if any(
            keyword in text
            for keyword in (
                "docker build",
                "dockerfile",
                "image build",
                "build failed",
                "compilation failed",
            )
        ):
            return "build"

        if any(
            keyword in text
            for keyword in (
                "deploy",
                "deployment",
                "kubectl",
                "helm",
            )
        ):
            return "deployment"

        if any(
            keyword in text
            for keyword in (
                "lint",
                "flake8",
                "ruff",
                "eslint",
                "pylint",
            )
        ):
            return "linting"

        if any(
            keyword in text
            for keyword in (
                "dependency",
                "requirements.txt",
                "pip install",
                "npm install",
                "package not found",
                "module not found",
            )
        ):
            return "dependency"

        if any(
            keyword in text
            for keyword in (
                "permission denied",
                "unauthorized",
                "forbidden",
                "authentication failed",
            )
        ):
            return "authentication"

        if analysis.failed_jobs:
            return "pipeline"

        if analysis.errors or analysis.exceptions:
            return "application"

        return "none"

    @staticmethod
    def _build_summary(
        analysis: LogAnalysis,
        failure_area: str,
        success: bool,
    ) -> str:
        if success:
            return "No CI/CD failure signals were detected."

        parts = []

        if analysis.errors:
            parts.append(
                f"{len(analysis.errors)} error signals"
            )

        if analysis.exceptions:
            parts.append(
                f"{len(analysis.exceptions)} exception signals"
            )

        if analysis.failed_tests:
            parts.append(
                f"{len(analysis.failed_tests)} failed tests"
            )

        if analysis.failed_jobs:
            parts.append(
                f"{len(analysis.failed_jobs)} failed pipeline jobs"
            )

        details = ", ".join(parts)

        if not details:
            details = "Pipeline failure detected"

        return (
            f"{details}. "
            f"Likely failure area: {failure_area}."
        )


if __name__ == "__main__":
    sample_log = """
    Running pytest
    FAILED tests/test_login.py::test_invalid_token
    ValueError: Invalid token
    Process completed with exit code 1
    """

    agent = CICDAgent()
    result = agent.analyze_log(sample_log)

    print("Success:", result.success)
    print("Failure area:", result.likely_failure_area)
    print("Failed tests:", result.failed_tests)
    print("Summary:", result.summary)