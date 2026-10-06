from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from tools.git_diff_tool import DiffResult


@dataclass
class ReviewFinding:
    severity: str
    message: str
    file_path: str | None = None


@dataclass
class ReviewResult:
    approved: bool
    risk_level: str
    findings: list[ReviewFinding]
    summary: str


class ReviewerAgent:
    def review_diff(
        self,
        diff_result: DiffResult,
    ) -> ReviewResult:
        findings: list[ReviewFinding] = []

        findings.extend(
            self._check_change_size(diff_result)
        )

        findings.extend(
            self._check_sensitive_files(diff_result)
        )

        findings.extend(
            self._check_for_debug_code(diff_result.raw_diff)
        )

        findings.extend(
            self._check_for_secrets(diff_result.raw_diff)
        )

        findings.extend(
            self._check_test_changes(diff_result)
        )

        risk_level = self._calculate_risk(findings)

        approved = not any(
            finding.severity == "high"
            for finding in findings
        )

        summary = self._build_summary(
            approved=approved,
            risk_level=risk_level,
            findings=findings,
        )

        return ReviewResult(
            approved=approved,
            risk_level=risk_level,
            findings=findings,
            summary=summary,
        )

    def to_dict(
        self,
        result: ReviewResult,
    ) -> dict[str, Any]:
        return asdict(result)

    @staticmethod
    def _check_change_size(
        diff_result: DiffResult,
    ) -> list[ReviewFinding]:
        findings = []

        total_changes = (
            diff_result.total_additions
            + diff_result.total_deletions
        )

        if total_changes > 500:
            findings.append(
                ReviewFinding(
                    severity="medium",
                    message=(
                        "The change set is large and may be "
                        "difficult to review safely."
                    ),
                )
            )

        if len(diff_result.changed_files) > 20:
            findings.append(
                ReviewFinding(
                    severity="medium",
                    message=(
                        "A high number of files are modified "
                        "in this change set."
                    ),
                )
            )

        return findings

    @staticmethod
    def _check_sensitive_files(
        diff_result: DiffResult,
    ) -> list[ReviewFinding]:
        findings = []

        sensitive_patterns = (
            ".env",
            "secrets",
            "credentials",
            "private_key",
            "id_rsa",
            "config/prod",
            "production",
        )

        for file in diff_result.changed_files:
            normalized = file.file_path.lower()

            if any(
                pattern in normalized
                for pattern in sensitive_patterns
            ):
                findings.append(
                    ReviewFinding(
                        severity="high",
                        message=(
                            "Sensitive or production-related file "
                            "was modified."
                        ),
                        file_path=file.file_path,
                    )
                )

        return findings

    @staticmethod
    def _check_for_debug_code(
        raw_diff: str,
    ) -> list[ReviewFinding]:
        findings = []

        debug_patterns = (
            "print(",
            "breakpoint()",
            "pdb.set_trace()",
            "console.log(",
        )

        for line in raw_diff.splitlines():
            if not line.startswith("+"):
                continue

            if line.startswith("+++"):
                continue

            content = line[1:].strip()

            if any(
                pattern in content
                for pattern in debug_patterns
            ):
                findings.append(
                    ReviewFinding(
                        severity="low",
                        message=(
                            "Possible debug statement added: "
                            f"{content[:100]}"
                        ),
                    )
                )

        return findings

    @staticmethod
    def _check_for_secrets(
        raw_diff: str,
    ) -> list[ReviewFinding]:
        findings = []

        secret_patterns = (
            "api_key",
            "apikey",
            "access_token",
            "secret_key",
            "password",
            "private_key",
        )

        for line in raw_diff.splitlines():
            if not line.startswith("+"):
                continue

            if line.startswith("+++"):
                continue

            content = line[1:].strip()
            lowered = content.lower()

            if any(
                pattern in lowered
                for pattern in secret_patterns
            ):
                if "=" in content or ":" in content:
                    findings.append(
                        ReviewFinding(
                            severity="high",
                            message=(
                                "Possible credential or secret "
                                "detected in added code."
                            ),
                        )
                    )

        return findings

    @staticmethod
    def _check_test_changes(
        diff_result: DiffResult,
    ) -> list[ReviewFinding]:
        findings = []

        source_changed = False
        tests_changed = False

        for file in diff_result.changed_files:
            path = file.file_path.lower()

            if (
                "test" in path
                or "tests/" in path
                or path.endswith("_test.py")
            ):
                tests_changed = True
            else:
                if path.endswith(
                    (
                        ".py",
                        ".js",
                        ".ts",
                        ".java",
                        ".go",
                        ".cpp",
                        ".c",
                    )
                ):
                    source_changed = True

        if source_changed and not tests_changed:
            findings.append(
                ReviewFinding(
                    severity="medium",
                    message=(
                        "Source code changed without corresponding "
                        "test changes."
                    ),
                )
            )

        return findings

    @staticmethod
    def _calculate_risk(
        findings: list[ReviewFinding],
    ) -> str:
        if any(
            finding.severity == "high"
            for finding in findings
        ):
            return "high"

        if any(
            finding.severity == "medium"
            for finding in findings
        ):
            return "medium"

        if findings:
            return "low"

        return "minimal"

    @staticmethod
    def _build_summary(
        approved: bool,
        risk_level: str,
        findings: list[ReviewFinding],
    ) -> str:
        if not findings:
            return (
                "No significant review issues were detected. "
                "The change set appears safe for further validation."
            )

        high = sum(
            1 for finding in findings
            if finding.severity == "high"
        )

        medium = sum(
            1 for finding in findings
            if finding.severity == "medium"
        )

        low = sum(
            1 for finding in findings
            if finding.severity == "low"
        )

        status = (
            "approved"
            if approved
            else "not approved"
        )

        return (
            f"Review {status}. "
            f"Risk level: {risk_level}. "
            f"Findings: {high} high, "
            f"{medium} medium, {low} low."
        )


if __name__ == "__main__":
    from tools.git_diff_tool import GitDiffTool

    diff_tool = GitDiffTool()
    reviewer = ReviewerAgent()

    diff = diff_tool.get_working_tree_diff(".")
    result = reviewer.review_diff(diff)

    print("Approved:", result.approved)
    print("Risk:", result.risk_level)
    print("Summary:", result.summary)

    for finding in result.findings:
        print(
            f"[{finding.severity}] "
            f"{finding.message}"
        )