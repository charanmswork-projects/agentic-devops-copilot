from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from agents.cicd_agent import CICDAnalysis
from agents.testing_agent import TestingAnalysis


@dataclass
class DiagnosisResult:
    issue_type: str
    root_cause: str
    confidence: float
    affected_area: str
    recommended_action: str
    evidence: list[str]


class DiagnosisAgent:
    def diagnose(
        self,
        testing_analysis: TestingAnalysis | None = None,
        cicd_analysis: CICDAnalysis | None = None,
    ) -> DiagnosisResult:
        evidence: list[str] = []

        if testing_analysis:
            evidence.extend(
                self._collect_testing_evidence(testing_analysis)
            )

        if cicd_analysis:
            evidence.extend(
                self._collect_cicd_evidence(cicd_analysis)
            )

        issue_type = self._identify_issue_type(
            testing_analysis,
            cicd_analysis,
        )

        root_cause = self._determine_root_cause(
            issue_type,
            testing_analysis,
            cicd_analysis,
        )

        confidence = self._calculate_confidence(
            testing_analysis,
            cicd_analysis,
        )

        affected_area = self._identify_affected_area(
            testing_analysis,
            cicd_analysis,
        )

        recommended_action = self._recommend_action(
            issue_type,
            affected_area,
        )

        return DiagnosisResult(
            issue_type=issue_type,
            root_cause=root_cause,
            confidence=confidence,
            affected_area=affected_area,
            recommended_action=recommended_action,
            evidence=evidence,
        )

    def to_dict(
        self,
        diagnosis: DiagnosisResult,
    ) -> dict[str, Any]:
        return asdict(diagnosis)

    @staticmethod
    def _collect_testing_evidence(
        analysis: TestingAnalysis,
    ) -> list[str]:
        evidence = []

        if analysis.failed:
            evidence.append(
                f"{analysis.failed} test(s) failed"
            )

        if analysis.errors:
            evidence.append(
                f"{analysis.errors} test error(s) detected"
            )

        for test in analysis.failed_tests[:5]:
            evidence.append(
                f"Failed test: {test}"
            )

        return evidence

    @staticmethod
    def _collect_cicd_evidence(
        analysis: CICDAnalysis,
    ) -> list[str]:
        evidence = []

        if analysis.errors:
            evidence.append(
                f"{analysis.errors} CI/CD error signal(s)"
            )

        if analysis.exceptions:
            evidence.append(
                f"{analysis.exceptions} exception signal(s)"
            )

        if analysis.failed_jobs:
            for job in analysis.failed_jobs[:5]:
                evidence.append(
                    f"Failed pipeline job: {job}"
                )

        if analysis.likely_failure_area != "none":
            evidence.append(
                f"Pipeline failure area: "
                f"{analysis.likely_failure_area}"
            )

        return evidence

    @staticmethod
    def _identify_issue_type(
        testing_analysis: TestingAnalysis | None,
        cicd_analysis: CICDAnalysis | None,
    ) -> str:
        if testing_analysis:
            if testing_analysis.failed > 0:
                return "test_failure"

            if testing_analysis.errors > 0:
                return "test_execution_error"

        if cicd_analysis:
            failure_area = cicd_analysis.likely_failure_area

            mapping = {
                "build": "build_failure",
                "deployment": "deployment_failure",
                "dependency": "dependency_failure",
                "authentication": "authentication_failure",
                "linting": "linting_failure",
                "pipeline": "pipeline_failure",
                "application": "application_failure",
                "testing": "test_failure",
            }

            return mapping.get(
                failure_area,
                "unknown_failure",
            )

        return "no_issue"

    @staticmethod
    def _determine_root_cause(
        issue_type: str,
        testing_analysis: TestingAnalysis | None,
        cicd_analysis: CICDAnalysis | None,
    ) -> str:
        if issue_type == "test_failure":
            if testing_analysis and testing_analysis.failed_tests:
                return (
                    "One or more automated tests are failing. "
                    "The failure is likely related to recent code "
                    "changes or incorrect test expectations."
                )

            return (
                "The CI pipeline detected failing automated tests."
            )

        if issue_type == "test_execution_error":
            return (
                "The test suite could not execute correctly. "
                "This may be caused by missing dependencies, "
                "configuration problems, or import errors."
            )

        if issue_type == "build_failure":
            return (
                "The application build process failed. "
                "Possible causes include compilation errors, "
                "invalid build configuration, or dependency issues."
            )

        if issue_type == "dependency_failure":
            return (
                "A required dependency could not be installed "
                "or loaded successfully."
            )

        if issue_type == "deployment_failure":
            return (
                "The deployment stage failed. "
                "The issue may involve deployment configuration, "
                "container settings, or infrastructure commands."
            )

        if issue_type == "authentication_failure":
            return (
                "The pipeline encountered an authentication or "
                "authorization problem while accessing a service."
            )

        if issue_type == "linting_failure":
            return (
                "Static analysis or linting checks failed because "
                "the source code does not satisfy configured rules."
            )

        if issue_type == "pipeline_failure":
            return (
                "A CI/CD pipeline step failed, but the available "
                "evidence does not identify a more specific cause."
            )

        if issue_type == "application_failure":
            return (
                "An application-level error or exception occurred "
                "during the pipeline execution."
            )

        if issue_type == "no_issue":
            return "No failure was detected."

        return (
            "A failure was detected, but the current evidence is "
            "insufficient to determine the exact root cause."
        )

    @staticmethod
    def _identify_affected_area(
        testing_analysis: TestingAnalysis | None,
        cicd_analysis: CICDAnalysis | None,
    ) -> str:
        if cicd_analysis:
            if cicd_analysis.likely_failure_area != "none":
                return cicd_analysis.likely_failure_area

        if testing_analysis:
            if testing_analysis.failed or testing_analysis.errors:
                return "testing"

        return "unknown"

    @staticmethod
    def _calculate_confidence(
        testing_analysis: TestingAnalysis | None,
        cicd_analysis: CICDAnalysis | None,
    ) -> float:
        score = 0.35

        if testing_analysis:
            if testing_analysis.failed_tests:
                score += 0.25

            if testing_analysis.failed > 0:
                score += 0.15

            if testing_analysis.errors > 0:
                score += 0.10

        if cicd_analysis:
            if cicd_analysis.failed_jobs:
                score += 0.10

            if cicd_analysis.exceptions:
                score += 0.10

            if cicd_analysis.likely_failure_area != "none":
                score += 0.10

        return round(
            min(score, 0.95),
            2,
        )

    @staticmethod
    def _recommend_action(
        issue_type: str,
        affected_area: str,
    ) -> str:
        recommendations = {
            "test_failure":
                "Inspect the failing tests and compare them with "
                "recent source-code changes.",

            "test_execution_error":
                "Check imports, dependencies, test configuration, "
                "and environment setup.",

            "build_failure":
                "Inspect the build logs and verify the build "
                "configuration and dependency versions.",

            "dependency_failure":
                "Verify dependency names, versions, package sources, "
                "and installation configuration.",

            "deployment_failure":
                "Inspect deployment configuration and validate "
                "container or infrastructure settings.",

            "authentication_failure":
                "Verify credentials, tokens, permissions, and "
                "repository secrets.",

            "linting_failure":
                "Review linting output and fix the reported "
                "source-code quality issues.",

            "pipeline_failure":
                "Inspect the failing pipeline step and its logs.",

            "application_failure":
                "Inspect the reported exception and the relevant "
                "application code.",

            "no_issue":
                "No corrective action is required.",
        }

        return recommendations.get(
            issue_type,
            f"Investigate the {affected_area} area using the "
            "available logs and repository changes.",
        )


if __name__ == "__main__":
    agent = DiagnosisAgent()

    diagnosis = agent.diagnose()

    print("Issue type:", diagnosis.issue_type)
    print("Root cause:", diagnosis.root_cause)
    print("Confidence:", diagnosis.confidence)
    print("Affected area:", diagnosis.affected_area)
    print("Recommended action:", diagnosis.recommended_action)