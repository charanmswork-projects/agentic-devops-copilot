from __future__ import annotations

import shutil
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


@dataclass
class CommitInfo:
    commit_hash: str
    author: str
    date: str
    message: str


@dataclass
class RepositoryMetadata:
    path: str
    remote_url: str
    current_branch: str
    latest_commit: CommitInfo
    is_dirty: bool


class GitHubTool:
    def __init__(self, workspace: str | Path = "workspace"):
        self.workspace = Path(workspace).resolve()
        self.workspace.mkdir(parents=True, exist_ok=True)

    def clone_repository(
        self,
        repository_url: str,
        directory_name: str | None = None,
        branch: str | None = None,
    ) -> Path:
        if not repository_url.startswith(("https://", "git@")):
            raise ValueError("Invalid repository URL")

        repo_name = directory_name or self._extract_repository_name(repository_url)
        destination = self.workspace / repo_name

        if destination.exists():
            raise FileExistsError(
                f"Repository already exists at {destination}"
            )

        command = ["git", "clone"]

        if branch:
            command.extend(["--branch", branch])

        command.extend([repository_url, str(destination)])

        self._run_command(command)

        return destination

    def update_repository(self, repository_path: str | Path) -> str:
        repository_path = self._validate_repository(repository_path)

        branch = self.get_current_branch(repository_path)

        return self._run_command(
            ["git", "pull", "origin", branch],
            cwd=repository_path,
        )

    def get_metadata(
        self,
        repository_path: str | Path,
    ) -> RepositoryMetadata:
        repository_path = self._validate_repository(repository_path)

        latest_commit = self.get_latest_commit(repository_path)

        return RepositoryMetadata(
            path=str(repository_path),
            remote_url=self.get_remote_url(repository_path),
            current_branch=self.get_current_branch(repository_path),
            latest_commit=latest_commit,
            is_dirty=self.has_uncommitted_changes(repository_path),
        )

    def get_metadata_dict(
        self,
        repository_path: str | Path,
    ) -> dict[str, Any]:
        return asdict(self.get_metadata(repository_path))

    def get_remote_url(self, repository_path: str | Path) -> str:
        repository_path = self._validate_repository(repository_path)

        return self._run_command(
            ["git", "remote", "get-url", "origin"],
            cwd=repository_path,
        )

    def get_current_branch(self, repository_path: str | Path) -> str:
        repository_path = self._validate_repository(repository_path)

        return self._run_command(
            ["git", "branch", "--show-current"],
            cwd=repository_path,
        )

    def get_latest_commit(
        self,
        repository_path: str | Path,
    ) -> CommitInfo:
        repository_path = self._validate_repository(repository_path)

        output = self._run_command(
            [
                "git",
                "log",
                "-1",
                "--pretty=format:%H|%an|%aI|%s",
            ],
            cwd=repository_path,
        )

        parts = output.split("|", 3)

        if len(parts) != 4:
            raise RuntimeError("Unable to parse latest commit")

        return CommitInfo(
            commit_hash=parts[0],
            author=parts[1],
            date=parts[2],
            message=parts[3],
        )

    def get_recent_commits(
        self,
        repository_path: str | Path,
        limit: int = 5,
    ) -> list[CommitInfo]:
        repository_path = self._validate_repository(repository_path)

        if limit <= 0:
            return []

        output = self._run_command(
            [
                "git",
                "log",
                f"-{limit}",
                "--pretty=format:%H|%an|%aI|%s",
            ],
            cwd=repository_path,
        )

        commits: list[CommitInfo] = []

        for line in output.splitlines():
            parts = line.split("|", 3)

            if len(parts) != 4:
                continue

            commits.append(
                CommitInfo(
                    commit_hash=parts[0],
                    author=parts[1],
                    date=parts[2],
                    message=parts[3],
                )
            )

        return commits

    def has_uncommitted_changes(
        self,
        repository_path: str | Path,
    ) -> bool:
        repository_path = self._validate_repository(repository_path)

        output = self._run_command(
            ["git", "status", "--porcelain"],
            cwd=repository_path,
        )

        return bool(output.strip())

    def get_changed_files(
        self,
        repository_path: str | Path,
    ) -> list[str]:
        repository_path = self._validate_repository(repository_path)

        output = self._run_command(
            ["git", "status", "--porcelain"],
            cwd=repository_path,
        )

        changed_files = []

        for line in output.splitlines():
            if len(line) >= 4:
                changed_files.append(line[3:].strip())

        return changed_files

    def remove_repository(self, repository_path: str | Path) -> None:
        repository_path = Path(repository_path).resolve()

        if not repository_path.exists():
            return

        if self.workspace not in repository_path.parents:
            raise ValueError(
                "Only repositories inside the workspace can be removed"
            )

        shutil.rmtree(repository_path)

    def _validate_repository(
        self,
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
    def _extract_repository_name(repository_url: str) -> str:
        name = repository_url.rstrip("/").split("/")[-1]

        if name.endswith(".git"):
            name = name[:-4]

        if not name:
            raise ValueError("Unable to determine repository name")

        return name

    @staticmethod
    def _run_command(
        command: list[str],
        cwd: str | Path | None = None,
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

        except FileNotFoundError as exc:
            raise RuntimeError(
                "Git is not installed or is not available in PATH"
            ) from exc

        except subprocess.CalledProcessError as exc:
            error = exc.stderr.strip() or exc.stdout.strip()

            raise RuntimeError(
                f"Git command failed: {error}"
            ) from exc


if __name__ == "__main__":
    github = GitHubTool()

    repository = github.clone_repository(
        "https://github.com/psf/requests.git"
    )

    metadata = github.get_metadata(repository)

    print(f"Repository: {metadata.path}")
    print(f"Remote: {metadata.remote_url}")
    print(f"Branch: {metadata.current_branch}")
    print(f"Latest commit: {metadata.latest_commit.commit_hash[:8]}")
    print(f"Message: {metadata.latest_commit.message}")
    print(f"Uncommitted changes: {metadata.is_dirty}")