from __future__ import annotations

import re
import subprocess
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


@dataclass
class TestResult:
    success: bool
    return_code: int
    passed: int
    failed: int
    skipped: int
    errors: int
    duration_seconds: float
    command: str
    output: str


class PytestTool:
    def __init__(self, timeout: int = 120):
        self.timeout = timeout

    def run_tests(
        self,
        repository_path: str | Path,
        test_path: str | None = None,
        extra_args: list[str] | None = None,
    ) -> TestResult:
        repo_path = self._validate_path(repository_path)

        command = ["python", "-m", "pytest", "-q"]

        if test_path:
            command.append(test_path)

        if extra_args:
            command.extend(extra_args)

        start_time = time.perf_counter()

        try:
            result = subprocess.run(
                command,
                cwd=repo_path,
                capture_output=True,
                text=True,
                timeout=self.timeout,
            )

            duration = time.perf_counter() - start_time

            output = self._combine_output(
                result.stdout,
                result.stderr,
            )

            counts = self._parse_test_counts(output)

            return TestResult(
                success=result.returncode == 0,
                return_code=result.returncode,
                passed=counts["passed"],
                failed=counts["failed"],
                skipped=counts["skipped"],
                errors=counts["errors"],
                duration_seconds=round(duration, 2),
                command=" ".join(command),
                output=output,
            )

        except subprocess.TimeoutExpired as exc:
            duration = time.perf_counter() - start_time

            output = self._combine_output(
                self._decode_output(exc.stdout),
                self._decode_output(exc.stderr),
            )

            return TestResult(
                success=False,
                return_code=-1,
                passed=0,
                failed=0,
                skipped=0,
                errors=1,
                duration_seconds=round(duration, 2),
                command=" ".join(command),
                output=f"{output}\nTest execution timed out.".strip(),
            )

        except FileNotFoundError as exc:
            raise RuntimeError(
                "Python or pytest could not be executed."
            ) from exc

    def run_single_test(
        self,
        repository_path: str | Path,
        test_identifier: str,
    ) -> TestResult:
        return self.run_tests(
            repository_path=repository_path,
            test_path=test_identifier,
        )

    def run_failed_tests(
        self,
        repository_path: str | Path,
    ) -> TestResult:
        return self.run_tests(
            repository_path=repository_path,
            extra_args=["--lf"],
        )

    def collect_tests(
        self,
        repository_path: str | Path,
    ) -> str:
        repo_path = self._validate_path(repository_path)

        command = [
            "python",
            "-m",
            "pytest",
            "--collect-only",
            "-q",
        ]

        try:
            result = subprocess.run(
                command,
                cwd=repo_path,
                capture_output=True,
                text=True,
                timeout=self.timeout,
            )

            return self._combine_output(
                result.stdout,
                result.stderr,
            )

        except subprocess.TimeoutExpired as exc:
            raise RuntimeError(
                "Test collection timed out."
            ) from exc

    def to_dict(
        self,
        result: TestResult,
    ) -> dict[str, Any]:
        return asdict(result)

    @staticmethod
    def _parse_test_counts(output: str) -> dict[str, int]:
        counts = {
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "errors": 0,
        }

        patterns = {
            "passed": r"(\d+)\s+passed",
            "failed": r"(\d+)\s+failed",
            "skipped": r"(\d+)\s+skipped",
            "errors": r"(\d+)\s+errors?",
        }

        for key, pattern in patterns.items():
            matches = re.findall(pattern, output)

            if matches:
                counts[key] = int(matches[-1])

        return counts

    @staticmethod
    def _validate_path(
        repository_path: str | Path,
    ) -> Path:
        path = Path(repository_path).resolve()

        if not path.exists():
            raise FileNotFoundError(
                f"Repository path does not exist: {path}"
            )

        if not path.is_dir():
            raise NotADirectoryError(
                f"Repository path is not a directory: {path}"
            )

        return path

    @staticmethod
    def _combine_output(
        stdout: str | None,
        stderr: str | None,
    ) -> str:
        parts = []

        if stdout and stdout.strip():
            parts.append(stdout.strip())

        if stderr and stderr.strip():
            parts.append(stderr.strip())

        return "\n".join(parts)

    @staticmethod
    def _decode_output(
        output: str | bytes | None,
    ) -> str:
        if output is None:
            return ""

        if isinstance(output, bytes):
            return output.decode(
                errors="replace",
            )

        return output


if __name__ == "__main__":
    pytest_tool = PytestTool()

    result = pytest_tool.run_tests(".")

    print(f"Success: {result.success}")
    print(f"Passed: {result.passed}")
    print(f"Failed: {result.failed}")
    print(f"Skipped: {result.skipped}")
    print(f"Errors: {result.errors}")
    print(f"Duration: {result.duration_seconds}s")
    print()
    print(result.output)