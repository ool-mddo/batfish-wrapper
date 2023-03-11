"""
gitops operation utilities
"""

import re
from typing import List, Dict
import git


class GitRepositoryOperator:
    def __init__(self, path: str):
        """Constructor
        Args:
            path (str): Path of target repository
        """
        self.repo = git.Repo(path)

    def current_branch(self) -> Dict:
        """Return current branch
        Returns:
            Dict: current branch info
        """
        branches = self._branches()
        current_branch = next((branch for branch in branches if re.match(r"\*", branch)), None)
        return {"current_branch": re.sub(r'\*', '', current_branch)}

    def switch_branch(self, branch: str) -> Dict:
        """Change(switch) current branch
        Args:
            branch (str): next branch name
        Returns:
            Dict: current branch info
        """
        try:
            message = self.repo.git.checkout(branch)
        except git.exc.GitCommandError as err:  # pylint: disable=E1101
            return {"current_branch": branch, "message": err.stderr, "status": "error"}
        return {"current_branch": branch, "message": message, "status": "success"}

    def _branches(self) -> List[str]:
        """Return all branch names in the repository
        Returns:
            List[str]: branch names
        """
        return [re.sub(r" *", "", branch) for branch in self.repo.git.branch().split("\n")]
