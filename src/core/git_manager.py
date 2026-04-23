import os

from git import Repo
from git.exc import GitCommandError


class GitManager:
    def __init__(self, data_dir: str):
        self.data_dir = data_dir
        self.repo_path = data_dir
        self._repo: Repo | None = None

    @property
    def repo(self) -> Repo:
        """Cached Repo object - re-created after init_repo"""
        if self._repo is None:
            self._repo = Repo(self.repo_path)
        return self._repo

    def init_repo(self) -> None:
        if os.path.isdir(os.path.join(self.repo_path, ".git")):
            self._repo = Repo(self.repo_path)
            return

        repo = Repo.init(self.repo_path)

        gitignore_path = os.path.join(self.repo_path, ".gitignore")
        with open(gitignore_path, "w", encoding="utf-8") as f:
            f.write("chroma_db/\nsession_memory/\ngraphrag_db/\n")

        # Create minimal config dir so initial commit has something
        config_dir = os.path.join(self.repo_path, "config")
        os.makedirs(config_dir, exist_ok=True)
        settings_path = os.path.join(config_dir, "settings.json")
        if not os.path.isfile(settings_path):
            with open(settings_path, "w", encoding="utf-8") as f:
                f.write("{}\n")

        repo.index.add([".gitignore", "config/settings.json"])
        repo.index.commit("Lv0: initial state")
        self._repo = repo

    def commit(self, message: str) -> None:
        repo = self.repo

        # Stage config/ and data/evolution_log/ only
        for prefix in ["config", os.path.join("data", "evolution_log")]:
            full_path = os.path.join(self.repo_path, prefix)
            if os.path.isdir(full_path):
                for root, _dirs, files in os.walk(full_path):
                    for fname in files:
                        rel = os.path.relpath(os.path.join(root, fname), self.repo_path)
                        repo.index.add([rel.replace(os.sep, "/")])

        if repo.is_dirty() or repo.index.diff("HEAD"):
            repo.index.commit(message)

    def log(self) -> list[dict]:
        repo = self.repo
        result = []
        for commit in repo.iter_commits():
            result.append({
                "hash": commit.hexsha,
                "message": commit.message.strip(),
                "date": commit.committed_datetime.isoformat(),
            })
        return result

    def checkout(self, commit_hash: str) -> None:
        repo = self.repo
        # Partial checkout: only config/ and data/evolution_log/
        for prefix in ["config", os.path.join("data", "evolution_log")]:
            full_path = os.path.join(self.repo_path, prefix)
            if os.path.isdir(full_path):
                # Check if this path exists in the target commit
                try:
                    repo.git.ls_tree(commit_hash, prefix.replace(os.sep, "/"))
                    repo.git.checkout(commit_hash, "--", prefix.replace(os.sep, "/"))
                except GitCommandError:
                    # Path doesn't exist in target commit, skip
                    pass

    def revert_last(self) -> None:
        repo = self.repo
        repo.git.revert("HEAD", no_edit=True)

    def get_evolution_commits(self) -> list[dict]:
        """获取进化相关的commit列表（commit message 以 'evolution:' 开头）"""
        repo = self.repo
        result = []
        for commit in repo.iter_commits():
            if commit.message.strip().startswith("evolution:"):
                result.append({
                    "hash": commit.hexsha,
                    "message": commit.message.strip(),
                    "date": commit.committed_datetime.isoformat(),
                })
        return result

    def revert_evolution_commit(self, commit_hash: str | None = None) -> bool:
        """回退单个进化commit。如果 commit_hash 为 None，回退最近的进化commit。"""
        repo = self.repo
        try:
            if commit_hash:
                repo.git.revert(commit_hash, no_edit=True)
            else:
                # 找到最近的进化commit
                evo_commits = self.get_evolution_commits()
                if not evo_commits:
                    return False
                repo.git.revert(evo_commits[0]["hash"], no_edit=True)
            return True
        except GitCommandError:
            return False
