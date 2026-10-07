# Agentic DevOps Copilot

An AI-oriented Software Engineering and DevOps Copilot designed to analyze repositories, inspect CI/CD failures, run automated tests, retrieve relevant code using RAG, diagnose issues, and review code changes through a unified workflow.

The project combines multiple specialized agents with repository tooling, semantic retrieval, FastAPI, and a Streamlit dashboard.

## Architecture

```text
                     Streamlit Dashboard
                            |
                            v
                         FastAPI
                            |
          +-----------------+-----------------+
          |                 |                 |
          v                 v                 v
 Repository Agent      Testing Agent      CI/CD Agent
          |                 |                 |
          |                 +--------+--------+
          |                          |
          |                          v
          |                   Diagnosis Agent
          |                          |
          +-----------> RAG <--------+
                     |
                     v
                Reviewer Agent
                     |
                     v
                 Git / CI/CD
```

## Features

- Repository structure and source-code analysis
- Automated test execution using Pytest
- CI/CD log parsing and failure detection
- Root-cause diagnosis from test and pipeline evidence
- Git diff analysis
- Automated code-change review
- Detection of risky changes and possible secrets
- Repository indexing using embeddings
- Semantic code retrieval with RAG
- FastAPI backend
- Streamlit dashboard
- Modular multi-agent architecture

## Project Structure

```text
agentic-devops-copilot/
│
├── agents/
│   ├── repository_agent.py
│   ├── cicd_agent.py
│   ├── testing_agent.py
│   ├── diagnosis_agent.py
│   └── reviewer_agent.py
│
├── rag/
│   ├── embeddings.py
│   ├── indexer.py
│   └── retriever.py
│
├── tools/
│   ├── github_tool.py
│   ├── pytest_tool.py
│   ├── log_parser.py
│   └── git_diff_tool.py
│
├── evaluation/
│   ├── benchmark.py
│   └── metrics.py
│
├── api/
│   └── main.py
│
├── dashboard/
│   └── app.py
│
├── tests/
├── .github/workflows/
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── README.md
```

## Tech Stack

- Python
- FastAPI
- Streamlit
- Pytest
- Git
- Sentence Transformers
- NumPy
- RAG / Embeddings
- Docker
- GitHub Actions

## Getting Started

Clone the repository:

```bash
git clone https://github.com/YOUR_USERNAME/agentic-devops-copilot.git
cd agentic-devops-copilot
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Start the FastAPI backend:

```bash
python -m uvicorn api.main:app --reload
```

Open the API documentation:

```text
http://127.0.0.1:8000/docs
```

Start the Streamlit dashboard in another terminal:

```bash
streamlit run dashboard/app.py
```

Open:

```text
http://localhost:8501
```

## RAG Workflow

Repository files are divided into chunks and converted into vector embeddings.

```text
Repository
    |
    v
Code / Config / Documentation
    |
    v
Chunking
    |
    v
Embedding Model
    |
    v
Vector Index
    |
    v
Semantic Retrieval
    |
    v
Relevant Context
```

This allows the system to retrieve code related to errors, failing tests, configuration problems, and developer questions.

## Current Workflow

```text
Repository Analysis
        |
        v
Automated Testing
        |
        v
CI/CD Log Analysis
        |
        v
Failure Diagnosis
        |
        v
Relevant Code Retrieval
        |
        v
Git Diff Review
        |
        v
Developer Decision
```

The current implementation combines deterministic engineering tools with agent-style orchestration.

## Planned Improvements

The next development stages include:

- LLM-based root-cause reasoning
- Agent orchestration with LangGraph
- AI-generated fix proposals
- Automatic validation of proposed fixes
- Human approval before code modification
- GitHub pull-request generation
- GitHub Actions integration
- Persistent vector database
- Agent evaluation and benchmarking
- Dockerized deployment

## Goal

The goal of this project is to explore how agentic AI can support real software engineering and DevOps workflows by combining code understanding, testing, CI/CD observability, retrieval, diagnosis, and review in one system.

## Author

**Charan Mettur Selvaraj**

M.Sc. Information and Communication Systems  
TU Chemnitz, Germany