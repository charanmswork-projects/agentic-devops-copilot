from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from typing import Any


@dataclass
class LogEvent:
    level: str
    message: str
    line_number: int
    raw_line: str


@dataclass
class LogAnalysis:
    total_lines: int
    errors: list[LogEvent]
    warnings: list[LogEvent]
    exceptions: list[LogEvent]
    failed_tests: list[str]
    failed_jobs: list[str]
    stack_traces: list[str]


class LogParser:
    ERROR_PATTERNS = (
        r"\berror\b",
        r"\bfatal\b",
        r"\bfailed\b",
        r"\bfailure\b",
    )

    WARNING_PATTERNS = (
        r"\bwarning\b",
        r"\bwarn\b",
        r"\bdeprecated\b",
    )

    EXCEPTION_PATTERNS = (
        r"\bexception\b",
        r"Traceback \(most recent call last\)",
        r"\b[A-Za-z]+Error:",
        r"\b[A-Za-z]+Exception:",
    )

    FAILED_TEST_PATTERNS = (
        r"FAILED\s+([^\s]+)",
        r"FAIL:\s+([^\s]+)",
    )

    FAILED_JOB_PATTERNS = (
        r"job\s+['\"]?([^'\"]+)['\"]?\s+failed",
        r"step\s+['\"]?([^'\"]+)['\"]?\s+failed",
        r"process completed with exit code\s+(\d+)",
    )

    def parse(self, log_text: str) -> LogAnalysis:
        if not isinstance(log_text, str):
            raise TypeError("log_text must be a string")

        lines = log_text.splitlines()

        errors: list[LogEvent] = []
        warnings: list[LogEvent] = []
        exceptions: list[LogEvent] = []

        for index, line in enumerate(lines, start=1):
            stripped = line.strip()

            if not stripped:
                continue

            if self._matches_any(stripped, self.EXCEPTION_PATTERNS):
                exceptions.append(
                    LogEvent(
                        level="exception",
                        message=self._clean_message(stripped),
                        line_number=index,
                        raw_line=line,
                    )
                )

            elif self._matches_any(stripped, self.ERROR_PATTERNS):
                errors.append(
                    LogEvent(
                        level="error",
                        message=self._clean_message(stripped),
                        line_number=index,
                        raw_line=line,
                    )
                )

            elif self._matches_any(stripped, self.WARNING_PATTERNS):
                warnings.append(
                    LogEvent(
                        level="warning",
                        message=self._clean_message(stripped),
                        line_number=index,
                        raw_line=line,
                    )
                )

        return LogAnalysis(
            total_lines=len(lines),
            errors=errors,
            warnings=warnings,
            exceptions=exceptions,
            failed_tests=self.extract_failed_tests(log_text),
            failed_jobs=self.extract_failed_jobs(log_text),
            stack_traces=self.extract_stack_traces(log_text),
        )

    def extract_failed_tests(self, log_text: str) -> list[str]:
        failed_tests: list[str] = []

        for pattern in self.FAILED_TEST_PATTERNS:
            matches = re.findall(
                pattern,
                log_text,
                flags=re.IGNORECASE,
            )

            for match in matches:
                value = match.strip()

                if value and value not in failed_tests:
                    failed_tests.append(value)

        return failed_tests

    def extract_failed_jobs(self, log_text: str) -> list[str]:
        failed_jobs: list[str] = []

        for pattern in self.FAILED_JOB_PATTERNS:
            matches = re.findall(
                pattern,
                log_text,
                flags=re.IGNORECASE,
            )

            for match in matches:
                value = match.strip()

                if value and value not in failed_jobs:
                    failed_jobs.append(value)

        return failed_jobs

    def extract_stack_traces(self, log_text: str) -> list[str]:
        lines = log_text.splitlines()
        traces: list[str] = []

        current_trace: list[str] = []
        collecting = False

        for line in lines:
            stripped = line.strip()

            if stripped.startswith(
                "Traceback (most recent call last)"
            ):
                if current_trace:
                    traces.append("\n".join(current_trace))

                current_trace = [line]
                collecting = True
                continue

            if collecting:
                current_trace.append(line)

                if self._looks_like_exception_line(stripped):
                    traces.append("\n".join(current_trace))
                    current_trace = []
                    collecting = False

        if current_trace:
            traces.append("\n".join(current_trace))

        return traces

    def get_summary(self, analysis: LogAnalysis) -> dict[str, Any]:
        return {
            "total_lines": analysis.total_lines,
            "error_count": len(analysis.errors),
            "warning_count": len(analysis.warnings),
            "exception_count": len(analysis.exceptions),
            "failed_test_count": len(analysis.failed_tests),
            "failed_job_count": len(analysis.failed_jobs),
            "stack_trace_count": len(analysis.stack_traces),
        }

    def to_dict(self, analysis: LogAnalysis) -> dict[str, Any]:
        return asdict(analysis)

    @staticmethod
    def _matches_any(
        text: str,
        patterns: tuple[str, ...],
    ) -> bool:
        return any(
            re.search(pattern, text, flags=re.IGNORECASE)
            for pattern in patterns
        )

    @staticmethod
    def _clean_message(message: str) -> str:
        message = re.sub(
            r"^\[[^\]]+\]\s*",
            "",
            message,
        )

        message = re.sub(
            r"^\d{4}-\d{2}-\d{2}[T\s][^\s]+\s*",
            "",
            message,
        )

        return message.strip()

    @staticmethod
    def _looks_like_exception_line(line: str) -> bool:
        return bool(
            re.match(
                r"^[A-Za-z_][A-Za-z0-9_.]*(Error|Exception):",
                line,
            )
        )


if __name__ == "__main__":
    sample_log = """
    INFO Starting test execution
    WARNING Deprecated configuration detected
    FAILED tests/test_auth.py::test_invalid_token
    Traceback (most recent call last):
      File "app/auth.py", line 42, in validate_token
        user = decode_token(token)
    ValueError: Invalid token format
    ERROR Authentication test failed
    Process completed with exit code 1
    """

    parser = LogParser()
    analysis = parser.parse(sample_log)

    print(parser.get_summary(analysis))
    print()
    print("Failed tests:", analysis.failed_tests)
    print("Failed jobs:", analysis.failed_jobs)
    print("Stack traces:", len(analysis.stack_traces))