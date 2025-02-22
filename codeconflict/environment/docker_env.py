import os
from typing import Dict, Any
import httpx

class DockerEnv:
    def __init__(self, base_url: str = "http://localhost:8080", workspace_path: str = "/workspace", agent_workspace: str = ""):
        """Initialize Docker environment with FastAPI server URL and workspace path"""
        self.base_url = base_url
        self.workspace_path = workspace_path
        self.agent_workspace = agent_workspace
        self.client = httpx.AsyncClient()

    async def read_file(self, path: str) -> Dict[str, str]:
        """Read file content from the Docker container"""
        try:
            response = await self.client.get(f"{self.base_url}/read/{self.agent_workspace}/{path}")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            raise RuntimeError(f"Failed to read file {path}: {str(e)}")

    async def write_file(self, path: str, content: str, start_line: int | None = None, end_line: int | None = None) -> Dict[str, str]:
        """Write content to a file in the Docker container
        
        Args:
            path: The file path to write to
            content: The content to write
            start_line: Optional starting line number (0-based) for line-specific updates
            end_line: Optional ending line number (0-based) for line-specific updates
        """
        print(f"Writing to file {path} with content: {content}")
        try:
            response = await self.client.post(
                f"{self.base_url}/write/{self.agent_workspace}/{path}",
                json={
                    "content": content,
                    "start_line": start_line,
                    "end_line": end_line
                }
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            raise RuntimeError(f"Failed to write file {path}: {str(e)}")

    async def execute_command(self, command: str) -> Dict[str, Any]:
        """Execute a bash command in the Docker container"""
        try:
            response = await self.client.post(
                f"{self.base_url}/bash",
                json={"command": command}
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            raise RuntimeError(f"Failed to execute command: {str(e)}")

    async def init_git_repo(self, email: str, name: str) -> Dict[str, Any]:
        """Initialize a Git repository with user configuration"""
        commands = [
            "git init",
            f"git config --global user.email \"{email}\"",
            f"git config --global user.name \"{name}\""
        ]
        results = {}
        for cmd in commands:
            results[cmd] = await self.execute_command(cmd)
        return results

    async def commit_changes(self, message: str, working_dir: str = "") -> Dict[str, Any]:
        """Add and commit changes with the given message

        Args:
            message (str): Commit message
            working_dir (str): Directory to execute git commands in. Defaults to workspace root.
        """
        commands = [
            f"cd {working_dir} && git add .",
            f"cd {working_dir} && git commit -m \"{message}\""
        ]
        results = {}
        for cmd in commands:
            results[cmd] = await self.execute_command(cmd)
        return results

    # async def create_branch(self, branch_name: str) -> Dict[str, Any]:
    #     """Create and checkout a new branch"""
    #     return await self.execute_command(f"git checkout -b {branch_name}")

    async def merge_branch(self, branch_name: str, working_dir: str = "") -> Dict[str, Any]:
        """Merge the specified branch into the current branch"""
        return await self.execute_command(f"cd {working_dir} && git merge {branch_name} --no-commit --no-ff")
    
    async def merge_main(self, branch_name: str, working_dir: str = "") -> Dict[str, Any]:
        """Merge the current branch into master branch

        Args:
            branch_name (str): Name of the current branch to merge into master
            working_dir (str): Directory to execute git commands in. Defaults to workspace root.
        """
        commands = [
            f"cd {working_dir} && git add .",
            f"cd {working_dir} && git commit -m 'Committing merge changes'",
            f"cd {working_dir} && git checkout master",
            f"cd {working_dir} && git merge {branch_name}",
            f"cd {working_dir} && git add .",
            f"cd {working_dir} && git commit -m 'Merged {branch_name} into master'"
        ]
        results = {}
        for cmd in commands:
            results[cmd] = await self.execute_command(cmd)
        return results


    async def code_diff(self, working_dir: str = "") -> Dict[str, Any]:
        return await self.execute_command(f"cd {working_dir} && git diff")
    
    async def merge_abort(self, working_dir: str = ""):
        """Abort the current merge operation"""
        return await self.execute_command(f"cd {working_dir} && git merge --abort")

    async def checkout_branch(self, branch_name: str) -> Dict[str, Any]:
        """Checkout the specified branch"""
        return await self.execute_command(f"git checkout {branch_name}")

    async def pull_base(self) -> Dict[str, Any]:
        """Pull updates from the base workspace

        Args:
            working_dir (str): Directory to execute git commands in. Defaults to workspace root.
        """
        commands = [
            "cd /workspace/base && git remote add origin /workspace/base",
            "cd /workspace/base && git branch --set-upstream-to=origin/master master",
            "cd /workspace/base && git pull origin master"
        ]
        results = {}
        for cmd in commands:
            results[cmd] = await self.execute_command(cmd)
        return results

    async def close(self):
        """Close the HTTP client"""
        await self.client.aclose()