from __future__ import annotations

import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


@dataclass
class DiffFile:
    file_path: str
    additions: int
    deletions: int
    status: str


@dataclass
class DiffResult:
    changed_files: list[DiffFile]
    total_additions: int
    total_deletions: int
    raw_diff: str


class GitDiffTool:
    def get_working_tree_diff(
        self,
        repository_path: str | Path,
    ) -> DiffResult:
        repo_path = self._validate_repository(repository_path)

        raw_diff = self._run_command(
            ["git", "diff"],
            cwd=repo_path,
        )

        changed_files = self._get_changed_files(
            repo_path,
            ["git", "diff", "--numstat"],
        )

        return self._build_result(
            changed_files=changed_files,
            raw_diff=raw_diff,
        )

    def get_staged_diff(
        self,
        repository_path: str | Path,
    ) -> DiffResult:
        repo_path = self._validate_repository(repository_path)

        raw_diff = self._run_command(
            ["git", "diff", "--cached"],
            cwd=repo_path,
        )

        changed_files = self._get_changed_files(
            repo_path,
            ["git", "diff", "--cached", "--numstat"],
        )

        return self._build_result(
            changed_files=changed_files,
            raw_diff=raw_diff,
        )

    def get_commit_diff(
        self,
        repository_path: str | Path,
        commit_hash: str,
    ) -> DiffResult:
        repo_path = self._validate_repository(repository_path)

        raw_diff = self._run_command(
            [
                "git",
                "show",
                commit_hash,
                "--format=",
                "--patch",
            ],
            cwd=repo_path,
        )

        changed_files = self._get_changed_files(
            repo_path,
            [
                "git",
                "show",
                commit_hash,
                "--format=",
                "--numstat",
            ],
        )

        return self._build_result(
            changed_files=changed_files,
            raw_diff=raw_diff,
        )

    def compare_commits(
        self,
        repository_path: str | Path,
        base_commit: str,
        target_commit: str,
    ) -> DiffResult:
        repo_path = self._validate_repository(repository_path)

        comparison = f"{base_commit}..{target_commit}"

        raw_diff = self._run_command(
            [
                "git",
                "diff",
                comparison,
            ],
            cwd=repo_path,
        )

        changed_files = self._get_changed_files(
            repo_path,
            [
                "git",
                "diff",
                "--numstat",
                comparison,
            ],
        )

        return self._build_result(
            changed_files=changed_files,
            raw_diff=raw_diff,
        )

    def get_file_diff(
        self,
        repository_path: str | Path,
        file_path: str,
    ) -> str:
        repo_path = self._validate_repository(repository_path)

        return self._run_command(
            [
                "git",
                "diff",
                "--",
                file_path,
            ],
            cwd=repo_path,
        )

    def get_changed_file_names(
        self,
        repository_path: str | Path,
        staged: bool = False,
    ) -> list[str]:
        repo_path = self._validate_repository(repository_path)

        command = ["git", "diff"]

        if staged:
            command.append("--cached")

        command.append("--name-only")

        output = self._run_command(
            command,
            cwd=repo_path,
        )

        if not output:
            return []

        return [
            line.strip()
            for line in output.splitlines()
            if line.strip()
        ]

    def to_dict(
        self,
        result: DiffResult,
    ) -> dict[str, Any]:
        return asdict(result)

    def _get_changed_files(
        self,
        repository_path: Path,
        command: list[str],
    ) -> list[DiffFile]:
        output = self._run_command(
            command,
            cwd=repository_path,
        )

        if not output:
            return []

        files: list[DiffFile] = []

        for line in output.splitlines():
            parts = line.split("\t")

            if len(parts) < 3:
                continue

            additions_raw = parts[0]
            deletions_raw = parts[1]
            file_path = parts[2]

            additions = self._parse_count(additions_raw)
            deletions = self._parse_count(deletions_raw)

            status = self._get_file_status(
                repository_path,
                file_path,
            )

            files.append(
                DiffFile(
                    file_path=file_path,
                    additions=additions,
                    deletions=deletions,
                    status=status,
                )
            )

        return files

    def _get_file_status(
        self,
        repository_path: Path,
        file_path: str,
    ) -> str:
        output = self._run_command(
            [
                "git",
                "status",
                "--short",
                "--",
                file_path,
            ],
            cwd=repository_path,
        )

        if not output:
            return "modified"

        code = output[:2].strip()

        status_map = {
            "A": "added",
            "M": "modified",
            "D": "deleted",
            "R": "renamed",
            "C": "copied",
            "??": "untracked",
        }

        return status_map.get(
            code,
            "modified",
        )

    @staticmethod
    def _build_result(
        changed_files: list[DiffFile],
        raw_diff: str,
    ) -> DiffResult:
        total_additions = sum(
            file.additions
            for file in changed_files
        )

        total_deletions = sum(
            file.deletions
            for file in changed_files
        )

        return DiffResult(
            changed_files=changed_files,
            total_additions=total_additions,
            total_deletions=total_deletions,
            raw_diff=raw_diff,
        )

    @staticmethod
    def _parse_count(value: str) -> int:
        if value == "-":
            return 0

        try:
            return int(value)
        except ValueError:
            return 0

    @staticmethod
    def _validate_repository(
        repository_path: str | Path,
    ) -> Path:
        path = Path(repository_path).resolve()

        if not path.exists():
            raise FileNotFoundError(
                f"Repository not found: {path}"
            )

        if not path.is_dir():
            raise NotADirectoryError(
                f"Repository path is not a directory: {path}"
            )

        if not (path / ".git").exists():
            raise ValueError(
                f"{path} is not a Git repository"
            )

        return path

    @staticmethod
    def _run_command(
        command: list[str],
        cwd: str | Path,
    ) -> str:
        try:
            result = subprocess.run(
                command,
                cwd=cwd,
                capture_output=True,
                text=True,
                check=True,
            )

            return result.stdout.strip()

        except subprocess.CalledProcessError as exc:
            error = exc.stderr.strip() or exc.stdout.strip()

            raise RuntimeError(
                f"Git command failed: {error}"
            ) from exc

        except FileNotFoundError as exc:
            raise RuntimeError(
                "Git is not installed or is not available in PATH"
            ) from exc


if __name__ == "__main__":
    diff_tool = GitDiffTool()

    result = diff_tool.get_working_tree_diff(".")

    print(f"Files changed: {len(result.changed_files)}")
    print(f"Additions: {result.total_additions}")
    print(f"Deletions: {result.total_deletions}")

    for file in result.changed_files:
        print(
            f"{file.status}: {file.file_path} "
            f"(+{file.additions} / -{file.deletions})"
        )