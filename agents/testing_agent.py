from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from tools.pytest_tool import PytestTool, TestResult


@dataclass
class TestingAnalysis:
    success: bool
    passed: int
    failed: int
    skipped: int
    errors: int
    duration_seconds: float
    failed_tests: list[str]
    summary: str
    raw_output: str


class TestingAgent:
    def __init__(self, timeout: int = 120):
        self.pytest_tool = PytestTool(timeout=timeout)

    def analyze(
        self,
        repository_path: str | Path,
        test_path: str | None = None,
    ) -> TestingAnalysis:
        result = self.pytest_tool.run_tests(
            repository_path=repository_path,
            test_path=test_path,
        )

        failed_tests = self._extract_failed_tests(result.output)

        return TestingAnalysis(
            success=result.success,
            passed=result.passed,
            failed=result.failed,
            skipped=result.skipped,
            errors=result.errors,
            duration_seconds=result.duration_seconds,
            failed_tests=failed_tests,
            summary=self._build_summary(result, failed_tests),
            raw_output=result.output,
        )

    def rerun_failed_tests(
        self,
        repository_path: str | Path,
    ) -> TestingAnalysis:
        result = self.pytest_tool.run_failed_tests(repository_path)

        failed_tests = self._extract_failed_tests(result.output)

        return TestingAnalysis(
            success=result.success,
            passed=result.passed,
            failed=result.failed,
            skipped=result.skipped,
            errors=result.errors,
            duration_seconds=result.duration_seconds,
            failed_tests=failed_tests,
            summary=self._build_summary(result, failed_tests),
            raw_output=result.output,
        )

    def run_specific_test(
        self,
        repository_path: str | Path,
        test_identifier: str,
    ) -> TestingAnalysis:
        result = self.pytest_tool.run_single_test(
            repository_path=repository_path,
            test_identifier=test_identifier,
        )

        failed_tests = self._extract_failed_tests(result.output)

        return TestingAnalysis(
            success=result.success,
            passed=result.passed,
            failed=result.failed,
            skipped=result.skipped,
            errors=result.errors,
            duration_seconds=result.duration_seconds,
            failed_tests=failed_tests,
            summary=self._build_summary(result, failed_tests),
            raw_output=result.output,
        )

    def collect_tests(
        self,
        repository_path: str | Path,
    ) -> list[str]:
        output = self.pytest_tool.collect_tests(repository_path)

        tests = []

        for line in output.splitlines():
            line = line.strip()

            if "::" in line:
                tests.append(line)

        return tests

    def to_dict(
        self,
        analysis: TestingAnalysis,
    ) -> dict[str, Any]:
        return asdict(analysis)

    @staticmethod
    def _extract_failed_tests(output: str) -> list[str]:
        failed_tests = []

        for line in output.splitlines():
            stripped = line.strip()

            if stripped.startswith("FAILED "):
                test_name = stripped.removeprefix("FAILED ").split(" - ")[0]

                if test_name not in failed_tests:
                    failed_tests.append(test_name)

        return failed_tests

    @staticmethod
    def _build_summary(
        result: TestResult,
        failed_tests: list[str],
    ) -> str:
        if result.success:
            return (
                f"All tests passed. "
                f"{result.passed} passed in "
                f"{result.duration_seconds} seconds."
            )

        parts = []

        if result.failed:
            parts.append(f"{result.failed} failed")

        if result.errors:
            parts.append(f"{result.errors} errors")

        if result.passed:
            parts.append(f"{result.passed} passed")

        if result.skipped:
            parts.append(f"{result.skipped} skipped")

        summary = ", ".join(parts) if parts else "Test execution failed"

        if failed_tests:
            summary += f". Failed tests: {', '.join(failed_tests[:5])}"

        return summary + "."


if __name__ == "__main__":
    agent = TestingAgent()

    analysis = agent.analyze(".")

    print("Success:", analysis.success)
    print("Passed:", analysis.passed)
    print("Failed:", analysis.failed)
    print("Errors:", analysis.errors)
    print("Failed tests:", analysis.failed_tests)
    print("Summary:", analysis.summary)