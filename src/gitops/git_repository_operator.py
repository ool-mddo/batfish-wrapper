"""
gitops operation utilities
"""

import git
import re
from typing import List, Dict


class GitRepositoryOperator:
    def __init__(self, path: str):
        self.repo = git.Repo(path)

    def current_branch(self) -> Dict:
        branches = self._branches()
        current_branch = next((branch for branch in branches if re.match(r"\*", branch)), None)
        return {"current_branch": re.sub(r'\*', '', current_branch)}

    def switch_branch(self, branch: str) -> Dict:
        try:
            message = self.repo.git.checkout(branch)
        except git.exc.GitCommandError as err:
            return {"current_branch": branch, "message": err.stderr, "status": "error"}
        return {"current_branch": branch, "message": message, "status": "success"}

    def _branches(self) -> List[str]:
        return [re.sub(r" *", "", branch) for branch in self.repo.git.branch().split("\n")]
