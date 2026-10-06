from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass
class EvaluationMetrics:
    total_cases: int
    correct_diagnoses: int
    correct_failure_areas: int
    successful_retrievals: int
    approved_safe_changes: int
    rejected_risky_changes: int

    diagnosis_accuracy: float
    failure_area_accuracy: float
    retrieval_success_rate: float
    review_accuracy: float


class MetricsCalculator:
    def calculate(
        self,
        results: list[dict[str, Any]],
    ) -> EvaluationMetrics:
        total_cases = len(results)

        if total_cases == 0:
            return EvaluationMetrics(
                total_cases=0,
                correct_diagnoses=0,
                correct_failure_areas=0,
                successful_retrievals=0,
                approved_safe_changes=0,
                rejected_risky_changes=0,
                diagnosis_accuracy=0.0,
                failure_area_accuracy=0.0,
                retrieval_success_rate=0.0,
                review_accuracy=0.0,
            )

        correct_diagnoses = sum(
            1
            for result in results
            if result.get("diagnosis_correct", False)
        )

        correct_failure_areas = sum(
            1
            for result in results
            if result.get("failure_area_correct", False)
        )

        successful_retrievals = sum(
            1
            for result in results
            if result.get("retrieval_successful", False)
        )

        approved_safe_changes = sum(
            1
            for result in results
            if (
                result.get("expected_review") == "approve"
                and result.get("actual_review") == "approve"
            )
        )

        rejected_risky_changes = sum(
            1
            for result in results
            if (
                result.get("expected_review") == "reject"
                and result.get("actual_review") == "reject"
            )
        )

        review_cases = sum(
            1
            for result in results
            if result.get("expected_review")
            in {"approve", "reject"}
        )

        review_correct = (
            approved_safe_changes
            + rejected_risky_changes
        )

        diagnosis_accuracy = (
            correct_diagnoses / total_cases
        )

        failure_area_accuracy = (
            correct_failure_areas / total_cases
        )

        retrieval_success_rate = (
            successful_retrievals / total_cases
        )

        review_accuracy = (
            review_correct / review_cases
            if review_cases
            else 0.0
        )

        return EvaluationMetrics(
            total_cases=total_cases,
            correct_diagnoses=correct_diagnoses,
            correct_failure_areas=correct_failure_areas,
            successful_retrievals=successful_retrievals,
            approved_safe_changes=approved_safe_changes,
            rejected_risky_changes=rejected_risky_changes,
            diagnosis_accuracy=round(
                diagnosis_accuracy,
                4,
            ),
            failure_area_accuracy=round(
                failure_area_accuracy,
                4,
            ),
            retrieval_success_rate=round(
                retrieval_success_rate,
                4,
            ),
            review_accuracy=round(
                review_accuracy,
                4,
            ),
        )

    @staticmethod
    def to_dict(
        metrics: EvaluationMetrics,
    ) -> dict[str, Any]:
        return asdict(metrics)

    @staticmethod
    def percentage(
        value: float,
    ) -> str:
        return f"{value * 100:.1f}%"


if __name__ == "__main__":
    sample_results = [
        {
            "diagnosis_correct": True,
            "failure_area_correct": True,
            "retrieval_successful": True,
            "expected_review": "approve",
            "actual_review": "approve",
        },
        {
            "diagnosis_correct": True,
            "failure_area_correct": False,
            "retrieval_successful": True,
            "expected_review": "reject",
            "actual_review": "reject",
        },
        {
            "diagnosis_correct": False,
            "failure_area_correct": True,
            "retrieval_successful": False,
            "expected_review": "approve",
            "actual_review": "reject",
        },
    ]

    calculator = MetricsCalculator()
    metrics = calculator.calculate(
        sample_results
    )

    print(
        "Diagnosis accuracy:",
        calculator.percentage(
            metrics.diagnosis_accuracy
        ),
    )

    print(
        "Failure-area accuracy:",
        calculator.percentage(
            metrics.failure_area_accuracy
        ),
    )

    print(
        "Retrieval success:",
        calculator.percentage(
            metrics.retrieval_success_rate
        ),
    )

    print(
        "Review accuracy:",
        calculator.percentage(
            metrics.review_accuracy
        ),
    )