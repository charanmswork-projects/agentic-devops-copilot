from __future__ import annotations

import os
from typing import Any

import requests
import streamlit as st


API_URL = os.getenv(
    "COPILOT_API_URL",
    "http://127.0.0.1:8000",
).rstrip("/")


st.set_page_config(
    page_title="Agentic DevOps Copilot",
    page_icon="🤖",
    layout="wide",
)


def call_api(
    endpoint: str,
    payload: dict[str, Any] | None = None,
    method: str = "POST",
    timeout: int = 300,
) -> dict[str, Any]:
    url = f"{API_URL}{endpoint}"

    try:
        if method == "GET":
            response = requests.get(
                url,
                timeout=timeout,
            )
        else:
            response = requests.post(
                url,
                json=payload,
                timeout=timeout,
            )

        response.raise_for_status()

        return response.json()

    except requests.ConnectionError as exc:
        raise RuntimeError(
            "Cannot connect to the FastAPI backend. "
            "Make sure it is running on port 8000."
        ) from exc

    except requests.HTTPError as exc:
        try:
            detail = response.json().get(
                "detail",
                response.text,
            )
        except ValueError:
            detail = response.text

        raise RuntimeError(
            f"API request failed: {detail}"
        ) from exc

    except requests.RequestException as exc:
        raise RuntimeError(
            f"Request failed: {exc}"
        ) from exc


def check_backend() -> bool:
    try:
        response = call_api(
            "/health",
            method="GET",
            timeout=5,
        )
        return response.get("status") == "healthy"

    except RuntimeError:
        return False


def show_repository_summary(
    data: dict[str, Any],
) -> None:
    summary = data.get("summary", {})

    col1, col2, col3, col4, col5 = st.columns(5)

    col1.metric(
        "Total Files",
        summary.get("total_files", 0),
    )

    col2.metric(
        "Source Files",
        summary.get("source_files", 0),
    )

    col3.metric(
        "Tests",
        summary.get("test_files", 0),
    )

    col4.metric(
        "Config Files",
        summary.get("config_files", 0),
    )

    col5.metric(
        "Documentation",
        summary.get("documentation_files", 0),
    )

    languages = summary.get(
        "languages",
        {},
    )

    if languages:
        st.subheader("Detected Languages")

        language_data = [
            {
                "Extension": extension,
                "Files": count,
            }
            for extension, count
            in languages.items()
        ]

        st.dataframe(
            language_data,
            use_container_width=True,
            hide_index=True,
        )

    important_files = summary.get(
        "important_files",
        [],
    )

    if important_files:
        st.subheader("Important Files")

        for file_path in important_files:
            st.code(file_path)

    st.subheader("Repository Tree")

    st.code(
        data.get(
            "tree",
            "No repository tree available.",
        ),
        language="text",
    )


def show_test_results(
    result: dict[str, Any],
) -> None:
    success = result.get(
        "success",
        False,
    )

    if success:
        st.success("All tests passed.")
    else:
        st.error("Test execution detected failures.")

    col1, col2, col3, col4 = st.columns(4)

    col1.metric(
        "Passed",
        result.get("passed", 0),
    )

    col2.metric(
        "Failed",
        result.get("failed", 0),
    )

    col3.metric(
        "Errors",
        result.get("errors", 0),
    )

    col4.metric(
        "Skipped",
        result.get("skipped", 0),
    )

    st.write(
        f"Execution time: "
        f"{result.get('duration_seconds', 0)} seconds"
    )

    summary = result.get("summary")

    if summary:
        st.info(summary)

    failed_tests = result.get(
        "failed_tests",
        [],
    )

    if failed_tests:
        st.subheader("Failed Tests")

        for test in failed_tests:
            st.code(test)

    with st.expander("Raw pytest output"):
        st.code(
            result.get(
                "raw_output",
                "",
            ),
            language="text",
        )


def show_diagnosis(
    result: dict[str, Any],
) -> None:
    diagnosis = result.get(
        "diagnosis",
        {},
    )

    issue_type = diagnosis.get(
        "issue_type",
        "unknown",
    )

    confidence = diagnosis.get(
        "confidence",
        0,
    )

    affected_area = diagnosis.get(
        "affected_area",
        "unknown",
    )

    col1, col2, col3 = st.columns(3)

    col1.metric(
        "Issue Type",
        issue_type.replace("_", " ").title(),
    )

    col2.metric(
        "Confidence",
        f"{confidence * 100:.0f}%",
    )

    col3.metric(
        "Affected Area",
        affected_area.title(),
    )

    st.subheader("Root Cause")

    st.write(
        diagnosis.get(
            "root_cause",
            "No diagnosis available.",
        )
    )

    st.subheader("Recommended Action")

    st.info(
        diagnosis.get(
            "recommended_action",
            "No recommendation available.",
        )
    )

    evidence = diagnosis.get(
        "evidence",
        [],
    )

    if evidence:
        st.subheader("Evidence")

        for item in evidence:
            st.write(f"• {item}")


def show_review(
    result: dict[str, Any],
) -> None:
    review = result.get(
        "review",
        {},
    )

    diff = result.get(
        "diff",
        {},
    )

    approved = review.get(
        "approved",
        False,
    )

    risk = review.get(
        "risk_level",
        "unknown",
    )

    if approved:
        st.success(
            "Reviewer Agent approved the change set."
        )
    else:
        st.error(
            "Reviewer Agent found blocking issues."
        )

    col1, col2, col3 = st.columns(3)

    col1.metric(
        "Risk Level",
        risk.title(),
    )

    col2.metric(
        "Additions",
        diff.get(
            "total_additions",
            0,
        ),
    )

    col3.metric(
        "Deletions",
        diff.get(
            "total_deletions",
            0,
        ),
    )

    st.write(
        review.get(
            "summary",
            "",
        )
    )

    findings = review.get(
        "findings",
        [],
    )

    if findings:
        st.subheader("Review Findings")

        for finding in findings:
            severity = finding.get(
                "severity",
                "unknown",
            )

            file_path = finding.get(
                "file_path",
            )

            message = finding.get(
                "message",
                "",
            )

            text = (
                f"[{severity.upper()}] {message}"
            )

            if file_path:
                text += f" — {file_path}"

            if severity == "high":
                st.error(text)

            elif severity == "medium":
                st.warning(text)

            else:
                st.info(text)

    changed_files = diff.get(
        "changed_files",
        [],
    )

    if changed_files:
        st.subheader("Changed Files")

        st.dataframe(
            changed_files,
            use_container_width=True,
            hide_index=True,
        )


st.title("Agentic DevOps Copilot")

st.caption(
    "Repository analysis, testing, CI/CD diagnosis, "
    "RAG retrieval and automated code review."
)

backend_online = check_backend()

with st.sidebar:
    st.header("Configuration")

    repository_path = st.text_input(
        "Repository Path",
        placeholder=r"C:\Users\...\project",
    )

    if backend_online:
        st.success("Backend connected")
    else:
        st.error("Backend offline")

    st.caption(
        f"API: {API_URL}"
    )


if not backend_online:
    st.warning(
        "Start the FastAPI backend before using the dashboard."
    )

    st.code(
        "python -m uvicorn api.main:app --reload",
        language="powershell",
    )


(
    overview_tab,
    tests_tab,
    cicd_tab,
    diagnosis_tab,
    rag_tab,
    review_tab,
) = st.tabs(
    [
        "Repository",
        "Testing",
        "CI/CD",
        "Diagnosis",
        "RAG Search",
        "Code Review",
    ]
)


with overview_tab:
    st.header("Repository Analysis")

    st.write(
        "Inspect repository structure, source files, "
        "tests and configuration."
    )

    if st.button(
        "Analyze Repository",
        type="primary",
        use_container_width=True,
    ):
        if not repository_path:
            st.warning(
                "Enter a repository path first."
            )

        else:
            with st.spinner(
                "Analyzing repository..."
            ):
                try:
                    result = call_api(
                        "/repository/analyze",
                        {
                            "repository_path":
                                repository_path,
                        },
                    )

                    st.session_state[
                        "repository_result"
                    ] = result

                except RuntimeError as exc:
                    st.error(str(exc))

    if "repository_result" in st.session_state:
        show_repository_summary(
            st.session_state[
                "repository_result"
            ]
        )


with tests_tab:
    st.header("Automated Testing")

    test_path = st.text_input(
        "Specific test path",
        placeholder=(
            "Optional: "
            "tests/test_auth.py::test_login"
        ),
    )

    if st.button(
        "Run Tests",
        use_container_width=True,
    ):
        if not repository_path:
            st.warning(
                "Enter a repository path first."
            )

        else:
            with st.spinner(
                "Running pytest..."
            ):
                try:
                    result = call_api(
                        "/tests/run",
                        {
                            "repository_path":
                                repository_path,
                            "test_path":
                                test_path or None,
                        },
                    )

                    st.session_state[
                        "test_result"
                    ] = result

                except RuntimeError as exc:
                    st.error(str(exc))

    if "test_result" in st.session_state:
        show_test_results(
            st.session_state[
                "test_result"
            ]
        )


with cicd_tab:
    st.header("CI/CD Log Analysis")

    log_text = st.text_area(
        "Pipeline Logs",
        height=300,
        placeholder=(
            "Paste GitHub Actions or "
            "other CI/CD logs here..."
        ),
    )

    if st.button(
        "Analyze Pipeline Log",
        use_container_width=True,
    ):
        if not log_text.strip():
            st.warning(
                "Paste a pipeline log first."
            )

        else:
            with st.spinner(
                "Analyzing pipeline..."
            ):
                try:
                    result = call_api(
                        "/cicd/analyze",
                        {
                            "log_text":
                                log_text,
                        },
                    )

                    st.session_state[
                        "cicd_result"
                    ] = result

                except RuntimeError as exc:
                    st.error(str(exc))

    if "cicd_result" in st.session_state:
        result = st.session_state[
            "cicd_result"
        ]

        if result.get("success"):
            st.success(
                "No CI/CD failure detected."
            )
        else:
            st.error(
                "Pipeline failure detected."
            )

        col1, col2, col3 = st.columns(3)

        col1.metric(
            "Errors",
            result.get(
                "errors",
                0,
            ),
        )

        col2.metric(
            "Warnings",
            result.get(
                "warnings",
                0,
            ),
        )

        col3.metric(
            "Exceptions",
            result.get(
                "exceptions",
                0,
            ),
        )

        st.subheader(
            "Likely Failure Area"
        )

        st.info(
            result.get(
                "likely_failure_area",
                "unknown",
            ).title()
        )

        st.write(
            result.get(
                "summary",
                "",
            )
        )

        failed_tests = result.get(
            "failed_tests",
            [],
        )

        if failed_tests:
            st.subheader(
                "Failed Tests"
            )

            for test in failed_tests:
                st.code(test)


with diagnosis_tab:
    st.header("Root Cause Diagnosis")

    diagnosis_log = st.text_area(
        "CI/CD log",
        height=200,
        key="diagnosis_log",
        placeholder=(
            "Optional: paste CI/CD log "
            "for additional evidence"
        ),
    )

    if st.button(
        "Run Diagnosis",
        type="primary",
        use_container_width=True,
    ):
        if not repository_path:
            st.warning(
                "Enter a repository path first."
            )

        else:
            with st.spinner(
                "Agents are diagnosing the failure..."
            ):
                try:
                    result = call_api(
                        "/diagnosis/run",
                        {
                            "repository_path":
                                repository_path,
                            "log_text":
                                diagnosis_log or None,
                        },
                    )

                    st.session_state[
                        "diagnosis_result"
                    ] = result

                except RuntimeError as exc:
                    st.error(str(exc))

    if "diagnosis_result" in st.session_state:
        show_diagnosis(
            st.session_state[
                "diagnosis_result"
            ]
        )


with rag_tab:
    st.header("Repository Knowledge Search")

    st.write(
        "Search the repository using semantic retrieval."
    )

    col1, col2 = st.columns(
        [3, 1]
    )

    with col1:
        rag_query = st.text_input(
            "Ask about the repository",
            placeholder=(
                "Where is authentication "
                "validation implemented?"
            ),
        )

    with col2:
        top_k = st.number_input(
            "Results",
            min_value=1,
            max_value=20,
            value=5,
        )

    col1, col2 = st.columns(2)

    with col1:
        if st.button(
            "Build RAG Index",
            use_container_width=True,
        ):
            if not repository_path:
                st.warning(
                    "Enter a repository path first."
                )

            else:
                with st.spinner(
                    "Building repository index..."
                ):
                    try:
                        result = call_api(
                            "/rag/index",
                            {
                                "repository_path":
                                    repository_path,
                            },
                            timeout=600,
                        )

                        st.success(
                            f"Indexed "
                            f"{result.get('files_indexed', 0)} "
                            f"files into "
                            f"{result.get('chunks_created', 0)} "
                            f"chunks."
                        )

                    except RuntimeError as exc:
                        st.error(str(exc))

    with col2:
        if st.button(
            "Search Repository",
            use_container_width=True,
        ):
            if not repository_path:
                st.warning(
                    "Enter a repository path first."
                )

            elif not rag_query.strip():
                st.warning(
                    "Enter a search query."
                )

            else:
                with st.spinner(
                    "Searching repository..."
                ):
                    try:
                        result = call_api(
                            "/rag/search",
                            {
                                "repository_path":
                                    repository_path,
                                "query":
                                    rag_query,
                                "top_k":
                                    int(top_k),
                            },
                            timeout=600,
                        )

                        st.session_state[
                            "rag_result"
                        ] = result

                    except RuntimeError as exc:
                        st.error(str(exc))

    if "rag_result" in st.session_state:
        results = st.session_state[
            "rag_result"
        ].get(
            "results",
            [],
        )

        if not results:
            st.info(
                "No relevant results found."
            )

        for position, result in enumerate(
            results,
            start=1,
        ):
            title = (
                f"{position}. "
                f"{result['file_path']} "
                f"— score {result['score']}"
            )

            with st.expander(
                title,
                expanded=position == 1,
            ):
                st.caption(
                    f"Lines "
                    f"{result['start_line']}–"
                    f"{result['end_line']}"
                )

                st.code(
                    result["content"],
                )


with review_tab:
    st.header("Code Review")

    staged = st.checkbox(
        "Review staged changes only"
    )

    if st.button(
        "Review Git Diff",
        use_container_width=True,
    ):
        if not repository_path:
            st.warning(
                "Enter a repository path first."
            )

        else:
            with st.spinner(
                "Reviewer Agent is inspecting changes..."
            ):
                try:
                    result = call_api(
                        "/review/diff",
                        {
                            "repository_path":
                                repository_path,
                            "staged":
                                staged,
                        },
                    )

                    st.session_state[
                        "review_result"
                    ] = result

                except RuntimeError as exc:
                    st.error(str(exc))

    if "review_result" in st.session_state:
        show_review(
            st.session_state[
                "review_result"
            ]
        )