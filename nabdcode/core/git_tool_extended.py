import subprocess
from typing import Optional

class GitToolExtended:
    """Extended Git operations with comprehensive security and functionality."""

    @staticmethod
    def git_status() -> str:
        """
        Get current Git repository status.
        Returns: String with status information
        """
        try:
            result = subprocess.run(
                ["git", "status", "--porcelain"],
                capture_output=True,
                text=True,
                check=False
            )

            if result.returncode != 0:
                return "[SYSTEM: GIT ERROR]\nNot a Git repository or git command failed."

            if not result.stdout.strip():
                return "[SYSTEM: GIT INFO]\nWorking directory is clean (no changes)."

            # Parse and format status
            status_lines = []
            for line in result.stdout.strip().split('\n'):
                if not line:
                    continue

                status = line[0]  # First character: M=modified, A=added, D=deleted, R=rename, etc.
                filename = line[1:].strip()

                status_symbols = {
                    'M': 'Modified',
                    'A': 'Added',
                    'D': 'Deleted',
                    'R': 'Renamed',
                    'C': 'Copied',
                    'U': 'Unmerged',
                    '?': 'Untracked',
                    '!': 'Ignored'
                }

                status_text = status_symbols.get(status, 'Unknown')
                status_lines.append(f"  {status_text}: {filename}")

            return f"[SYSTEM: GIT STATUS]\n{len(status_lines)} file(s) changed:\n" + "\n".join(status_lines)

        except Exception as e:
            return f"[SYSTEM: GIT ERROR]\nFailed to get status: {str(e)}"

    @staticmethod
    def git_diff() -> str:
        """
        Show unstaged changes.
        Returns: String with diff output
        """
        try:
            result = subprocess.run(
                ["git", "diff"],
                capture_output=True,
                text=True,
                check=False
            )

            if result.returncode != 0:
                return "[SYSTEM: GIT INFO]\nNo unstaged changes."

            if not result.stdout.strip():
                return "[SYSTEM: GIT INFO]\nNo unstaged changes."

            # Truncate if too large
            max_diff_chars = 5000
            if len(result.stdout) > max_diff_chars:
                diff = result.stdout[:max_diff_chars] + "\n\n[DIFF TRUNCATED]"
            else:
                diff = result.stdout

            return f"[SYSTEM: GIT DIFF]\n{diff}"

        except Exception as e:
            return f"[SYSTEM: GIT ERROR]\nFailed to get diff: {str(e)}"

    @staticmethod
    def git_log(limit: int = 10) -> str:
        """
        Show commit history.
        Args:
            limit: Maximum number of commits to show
        Returns: String with commit log
        """
        try:
            result = subprocess.run(
                ["git", "log", "--oneline", f"-{limit}"],
                capture_output=True,
                text=True,
                check=False
            )

            if result.returncode != 0:
                return "[SYSTEM: GIT ERROR]\nFailed to get commit log."

            if not result.stdout.strip():
                return "[SYSTEM: GIT INFO]\nNo commits in repository."

            commits = result.stdout.strip().split('\n')

            log_output = f"[SYSTEM: GIT LOG]\nShowing last {len(commits)} commit(s):\n"
            for i, commit in enumerate(commits, 1):
                log_output += f"  {i}. {commit}\n"

            return log_output

        except Exception as e:
            return f"[SYSTEM: GIT ERROR]\nFailed to get commit log: {str(e)}"

    @staticmethod
    def git_branch() -> str:
        """
        Show current branch and all branches.
        Returns: String with branch information
        """
        try:
            # Current branch
            branch_result = subprocess.run(
                ["git", "branch", "--show-current"],
                capture_output=True,
                text=True,
                check=False
            )

            current_branch = branch_result.stdout.strip() if branch_result.returncode == 0 else "unknown"

            # All branches
            all_branches_result = subprocess.run(
                ["git", "branch", "-a"],
                capture_output=True,
                text=True,
                check=False
            )

            all_branches = all_branches_result.stdout.strip().split('\n') if all_branches_result.returncode == 0 else []

            output = f"[SYSTEM: GIT BRANCH]\nCurrent branch: {current_branch}\n\nAll branches:\n"
            for branch in all_branches:
                if branch.strip():
                    marker = " *" if branch.strip().startswith("*") else "   "
                    output += f"{marker} {branch.strip()}\n"

            return output

        except Exception as e:
            return f"[SYSTEM: GIT ERROR]\nFailed to get branch info: {str(e)}"

    @staticmethod
    def git_remote() -> str:
        """
        Show remote repository information.
        Returns: String with remote information
        """
        try:
            # Check if remote exists
            remote_result = subprocess.run(
                ["git", "remote", "-v"],
                capture_output=True,
                text=True,
                check=False
            )

            if remote_result.returncode != 0:
                return "[SYSTEM: GIT INFO]\nNo remote repository configured."

            remotes = remote_result.stdout.strip().split('\n') if remote_result.returncode == 0 else []

            output = f"[SYSTEM: GIT REMOTE]\nRemotes configured:\n"
            for remote in remotes:
                if remote.strip():
                    output += f"  {remote.strip()}\n"

            return output

        except Exception as e:
            return f"[SYSTEM: GIT ERROR]\nFailed to get remote info: {str(e)}"

    @staticmethod
    def git_reset_hard(commit_hash: str) -> str:
        """
        Reset repository to specific commit (hard reset).
        WARNING: This discards all uncommitted changes!
        Args:
            commit_hash: Commit hash or reference to reset to
        Returns: String with result
        """
        try:
            # First check if there are changes
            status_result = subprocess.run(
                ["git", "status", "--porcelain"],
                capture_output=True,
                text=True,
                check=False
            )

            if status_result.stdout.strip():
                logger.warning("Resetting hard with uncommitted changes!")

            # Perform hard reset
            result = subprocess.run(
                ["git", "reset", "--hard", commit_hash],
                capture_output=True,
                text=True,
                check=False
            )

            if result.returncode != 0:
                return f"[SYSTEM: GIT WARNING]\nFailed to reset to {commit_hash}: {result.stderr}"

            return f"[SYSTEM: GIT RESET]\nRepository successfully reset to {commit_hash}"

        except Exception as e:
            return f"[SYSTEM: GIT ERROR]\nFailed to perform hard reset: {str(e)}"

    @staticmethod
    def git_checkout(branch_name: str) -> str:
        """
        Checkout a branch.
        Args:
            branch_name: Name of branch to checkout
        Returns: String with result
        """
        try:
            result = subprocess.run(
                ["git", "checkout", branch_name],
                capture_output=True,
                text=True,
                check=False
            )

            if result.returncode != 0:
                return f"[SYSTEM: GIT ERROR]\nFailed to checkout '{branch_name}': {result.stderr}"

            return f"[SYSTEM: GIT CHECKOUT]\nSuccessfully switched to branch '{branch_name}'"

        except Exception as e:
            return f"[SYSTEM: GIT ERROR]\nFailed to checkout branch: {str(e)}"

    @staticmethod
    def git_stash_push(message: str = "Stash changes") -> str:
        """
        Stash current changes.
        Args:
            message: Stash message
        Returns: String with result
        """
        try:
            result = subprocess.run(
                ["git", "stash", "push", "-m", message],
                capture_output=True,
                text=True,
                check=False
            )

            if result.returncode != 0:
                return f"[SYSTEM: GIT ERROR]\nFailed to stash changes: {result.stderr}"

            return f"[SYSTEM: GIT STASH]\nChanges stashed successfully with message: {message}"

        except Exception as e:
            return f"[SYSTEM: GIT ERROR]\nFailed to stash changes: {str(e)}"

    @staticmethod
    def git_stash_pop() -> str:
        """
        Pop most recent stash.
        Returns: String with result
        """
        try:
            result = subprocess.run(
                ["git", "stash", "pop"],
                capture_output=True,
                text=True,
                check=False
            )

            if result.returncode != 0:
                # Stash might be empty or conflict
                if "No stash entries found" in result.stderr or "No local changes" in result.stderr:
                    return "[SYSTEM: GIT INFO]\nNo stash to pop."
                return f"[SYSTEM: GIT ERROR]\nFailed to pop stash: {result.stderr}"

            return "[SYSTEM: GIT STASH POP]\nStashed changes applied successfully."

        except Exception as e:
            return f"[SYSTEM: GIT ERROR]\nFailed to pop stash: {str(e)}"

# Module-level convenience functions for tool registration
def git_status() -> str:
    return GitToolExtended.git_status()

def git_diff() -> str:
    return GitToolExtended.git_diff()

def git_log(limit: int = 10) -> str:
    return GitToolExtended.git_log(limit)

def git_branch() -> str:
    return GitToolExtended.git_branch()

def git_remote() -> str:
    return GitToolExtended.git_remote()

def git_checkout(branch: str) -> str:
    return GitToolExtended.git_checkout(branch)

def git_stash_push(message: str = "Stash changes") -> str:
    return GitToolExtended.git_stash_push(message)

def git_stash_pop() -> str:
    return GitToolExtended.git_stash_pop()