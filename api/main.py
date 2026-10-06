from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from agents.cicd_agent import CICDAgent
from agents.diagnosis_agent import DiagnosisAgent
from agents.repository_agent import RepositoryAgent
from agents.reviewer_agent import ReviewerAgent
from agents.testing_agent import TestingAgent
from rag.indexer import RepositoryIndexer
from rag.retriever import RepositoryRetriever
from tools.git_diff_tool import GitDiffTool


app = FastAPI(
    title="Agentic DevOps Copilot",
    description=(
        "API for repository analysis, testing, CI/CD diagnosis, "
        "RAG retrieval, and code review."
    ),
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


testing_agent = TestingAgent()
cicd_agent = CICDAgent()
diagnosis_agent = DiagnosisAgent()
reviewer_agent = ReviewerAgent()
diff_tool = GitDiffTool()


class RepositoryRequest(BaseModel):
    repository_path: str


class TestRequest(BaseModel):
    repository_path: str
    test_path: str | None = None


class CICDLogRequest(BaseModel):
    log_text: str = Field(min_length=1)


class DiagnosisRequest(BaseModel):
    repository_path: str
    log_text: str | None = None


class RAGQueryRequest(BaseModel):
    repository_path: str
    query: str = Field(min_length=1)
    top_k: int = Field(default=5, ge=1, le=20)


class ReviewRequest(BaseModel):
    repository_path: str
    staged: bool = False


@app.get("/")
def root() -> dict:
    return {
        "name": "Agentic DevOps Copilot",
        "status": "running",
        "version": "0.1.0",
    }


@app.get("/health")
def health() -> dict:
    return {
        "status": "healthy",
    }


@app.post("/repository/analyze")
def analyze_repository(
    request: RepositoryRequest,
) -> dict:
    try:
        agent = RepositoryAgent(
            request.repository_path
        )

        summary = agent.analyze()

        return {
            "summary": agent.to_dict(),
            "tree": agent.get_tree(),
        }

    except Exception as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc


@app.post("/tests/run")
def run_tests(
    request: TestRequest,
) -> dict:
    try:
        result = testing_agent.analyze(
            repository_path=request.repository_path,
            test_path=request.test_path,
        )

        return testing_agent.to_dict(result)

    except Exception as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc


@app.post("/cicd/analyze")
def analyze_cicd(
    request: CICDLogRequest,
) -> dict:
    try:
        result = cicd_agent.analyze_log(
            request.log_text
        )

        return cicd_agent.to_dict(result)

    except Exception as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc


@app.post("/diagnosis/run")
def run_diagnosis(
    request: DiagnosisRequest,
) -> dict:
    try:
        testing_result = testing_agent.analyze(
            request.repository_path
        )

        cicd_result = None

        if request.log_text:
            cicd_result = cicd_agent.analyze_log(
                request.log_text
            )

        diagnosis = diagnosis_agent.diagnose(
            testing_analysis=testing_result,
            cicd_analysis=cicd_result,
        )

        return {
            "testing": testing_agent.to_dict(
                testing_result
            ),
            "cicd": (
                cicd_agent.to_dict(cicd_result)
                if cicd_result
                else None
            ),
            "diagnosis": diagnosis_agent.to_dict(
                diagnosis
            ),
        }

    except Exception as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc


@app.post("/rag/index")
def build_rag_index(
    request: RepositoryRequest,
) -> dict:
    try:
        repository_path = Path(
            request.repository_path
        ).resolve()

        indexer = RepositoryIndexer()

        index = indexer.build_index(
            repository_path
        )

        output_path = (
            Path("data")
            / f"{repository_path.name}_index.json"
        )

        saved_path = indexer.save_index(
            index,
            output_path,
        )

        return {
            "repository": str(repository_path),
            "files_indexed": index.total_files,
            "chunks_created": index.total_chunks,
            "embedding_model": index.embedding_model,
            "embedding_dimension": (
                index.embedding_dimension
            ),
            "index_path": str(saved_path),
        }

    except Exception as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc


@app.post("/rag/search")
def search_repository(
    request: RAGQueryRequest,
) -> dict:
    try:
        repository_path = Path(
            request.repository_path
        ).resolve()

        index_path = (
            Path("data")
            / f"{repository_path.name}_index.json"
        )

        indexer = RepositoryIndexer()

        if index_path.exists():
            index = indexer.load_index(
                index_path
            )
        else:
            index = indexer.build_index(
                repository_path
            )

            indexer.save_index(
                index,
                index_path,
            )

        retriever = RepositoryRetriever(
            index=index
        )

        results = retriever.retrieve(
            query=request.query,
            top_k=request.top_k,
        )

        return {
            "query": request.query,
            "results": [
                {
                    "chunk_id": result.chunk_id,
                    "file_path": result.file_path,
                    "start_line": result.start_line,
                    "end_line": result.end_line,
                    "score": result.score,
                    "content": result.content,
                }
                for result in results
            ],
        }

    except Exception as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc


@app.post("/review/diff")
def review_diff(
    request: ReviewRequest,
) -> dict:
    try:
        if request.staged:
            diff = diff_tool.get_staged_diff(
                request.repository_path
            )
        else:
            diff = diff_tool.get_working_tree_diff(
                request.repository_path
            )

        review = reviewer_agent.review_diff(
            diff
        )

        return {
            "diff": {
                "changed_files": [
                    {
                        "file_path": file.file_path,
                        "additions": file.additions,
                        "deletions": file.deletions,
                        "status": file.status,
                    }
                    for file in diff.changed_files
                ],
                "total_additions": (
                    diff.total_additions
                ),
                "total_deletions": (
                    diff.total_deletions
                ),
            },
            "review": reviewer_agent.to_dict(
                review
            ),
        }

    except Exception as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc