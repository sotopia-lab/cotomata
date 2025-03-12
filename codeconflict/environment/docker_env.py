# import os
# from typing import Dict, Any
# import httpx

# class DockerEnv:
#     def __init__(self, base_url: str = "http://localhost:8080", workspace_path: str = "/workspace", agent_workspace: str = ""):
#         """Initialize Docker environment with FastAPI server URL and workspace path"""
#         self.base_url = base_url
#         self.workspace_path = workspace_path
#         self.agent_workspace = agent_workspace
#         self.client = httpx.AsyncClient()

#     async def read_file(self, path: str) -> Dict[str, str]:
#         """Read file content from the Docker container"""
#         try:
#             response = await self.client.get(f"{self.base_url}/read/{self.agent_workspace}/{path}")
#             response.raise_for_status()
#             return response.json()
#         except Exception as e:
#             raise RuntimeError(f"Failed to read file {path}: {str(e)}")

#     async def write_file(self, path: str, content: str, start_line: int | None = None, end_line: int | None = None) -> Dict[str, str]:
#         """Write content to a file in the Docker container
        
#         Args:
#             path: The file path to write to
#             content: The content to write
#             start_line: Optional starting line number (0-based) for line-specific updates
#             end_line: Optional ending line number (0-based) for line-specific updates
#         """
#         print(f"Writing to file {path} with content: {content}")
#         try:
#             response = await self.client.post(
#                 f"{self.base_url}/write/{self.agent_workspace}/{path}",
#                 json={
#                     "content": content,
#                     "start_line": start_line,
#                     "end_line": end_line
#                 }
#             )
#             response.raise_for_status()
#             return response.json()
#         except Exception as e:
#             raise RuntimeError(f"Failed to write file {path}: {str(e)}")

#     async def execute_command(self, command: str) -> Dict[str, Any]:
#         """Execute a bash command in the Docker container"""
#         try:
#             response = await self.client.post(
#                 f"{self.base_url}/bash",
#                 json={"command": command}
#             )
#             response.raise_for_status()
#             return response.json()
#         except Exception as e:
#             raise RuntimeError(f"Failed to execute command: {str(e)}")

#     async def init_git_repo(self, email: str, name: str) -> Dict[str, Any]:
#         """Initialize a Git repository with user configuration"""
#         commands = [
#             "git init",
#             f"git config --global user.email \"{email}\"",
#             f"git config --global user.name \"{name}\""
#         ]
#         results = {}
#         for cmd in commands:
#             results[cmd] = await self.execute_command(cmd)
#         return results

#     async def commit_changes(self, message: str, working_dir: str = "") -> Dict[str, Any]:
#         """Add and commit changes with the given message

#         Args:
#             message (str): Commit message
#             working_dir (str): Directory to execute git commands in. Defaults to workspace root.
#         """
#         commands = [
#             f"cd {working_dir} && git add .",
#             f"cd {working_dir} && git commit -m \"{message}\""
#         ]
#         results = {}
#         for cmd in commands:
#             results[cmd] = await self.execute_command(cmd)
#         return results

#     # async def create_branch(self, branch_name: str) -> Dict[str, Any]:
#     #     """Create and checkout a new branch"""
#     #     return await self.execute_command(f"git checkout -b {branch_name}")

#     async def merge_branch(self, branch_name: str, working_dir: str = "") -> Dict[str, Any]:
#         """Merge the specified branch into the current branch"""
#         return await self.execute_command(f"cd {working_dir} && git merge {branch_name} --no-commit --no-ff")
    
#     async def merge_main(self, branch_name: str, working_dir: str = "") -> Dict[str, Any]:
#         """Merge the current branch into master branch

#         Args:
#             branch_name (str): Name of the current branch to merge into master
#             working_dir (str): Directory to execute git commands in. Defaults to workspace root.
#         """
#         commands = [
#             f"cd {working_dir} && git add .",
#             f"cd {working_dir} && git commit -m 'Committing merge changes'",
#             f"cd /workspace/base && git merge {branch_name}",
#             # f"cd {working_dir} && git add .",
#             # f"cd {working_dir} && git commit -m 'Merged {branch_name} into master'"
#         ]
#         results = {}
#         for cmd in commands:
#             results[cmd] = await self.execute_command(cmd)
#         return results


#     async def code_diff(self, working_dir: str = "") -> Dict[str, Any]:
#         return await self.execute_command(f"cd {working_dir} && git diff")
    
#     async def merge_abort(self, working_dir: str = ""):
#         """Abort the current merge operation"""
#         return await self.execute_command(f"cd {working_dir} && git merge --abort")

#     async def checkout_branch(self, branch_name: str) -> Dict[str, Any]:
#         """Checkout the specified branch"""
#         return await self.execute_command(f"git checkout {branch_name}")

#     async def pull_base(self) -> Dict[str, Any]:
#         """Pull updates from the base workspace

#         Args:
#             working_dir (str): Directory to execute git commands in. Defaults to workspace root.
#         """
#         commands = [
#             "cd /workspace/base && git remote add origin /workspace/base",
#             "cd /workspace/base && git branch --set-upstream-to=origin/master master",
#             "cd /workspace/base && git pull origin master"
#         ]
#         results = {}
#         for cmd in commands:
#             results[cmd] = await self.execute_command(cmd)
#         return results

#     async def close(self):
#         """Close the HTTP client"""
#         await self.client.aclose()




import os
import io
from typing import Dict, Any, Optional, Union
import docker

class DockerEnv:
    def __init__(self, container_name: str, workspace_path: str = "/workspace", agent_workspace: str = ""):
        """Initialize Docker environment using the Python Docker client
        
        Args:
            container_name: Name or ID of the container to connect to
            workspace_path: Base workspace path inside the container
            agent_workspace: Optional sub-workspace directory
        """
        self.client = docker.from_env()
        self.container = self.client.containers.get(container_name)
        self.workspace_path = workspace_path
        self.agent_workspace = agent_workspace
    
    def _get_full_path(self, path: str) -> str:
        """Get the full path inside the container"""
        if self.agent_workspace:
            return os.path.join(self.workspace_path, self.agent_workspace, path)
        return os.path.join(self.workspace_path, path)
    
    async def read_file(self, path: str) -> Dict[str, str]:
        """Read file content from the Docker container"""
        try:
            full_path = self._get_full_path(path)
            # Execute 'cat' command to read file content
            exit_code, output = self.container.exec_run(f"cat {full_path}")
            
            if exit_code != 0:
                raise RuntimeError(f"Failed to read file: {output.decode('utf-8')}")
            
            content = output.decode('utf-8')
            return {"content": content, "path": path}
        except Exception as e:
            raise RuntimeError(f"Failed to read file {path}: {str(e)}")
    
    async def write_file(self, path: str, content: str, 
                         start_line: Optional[int] = None, 
                         end_line: Optional[int] = None) -> Dict[str, str]:
        """Write content to a file in the Docker container
        
        Args:
            path: The file path to write to
            content: The content to write
            start_line: Optional starting line number (0-based) for line-specific updates
            end_line: Optional ending line number (0-based) for line-specific updates
        """
        try:
            full_path = self._get_full_path(path)
            
            # If we need to do a partial update (replace specific lines)
            if start_line is not None and end_line is not None:
                # First read the existing file
                current_content_result = await self.read_file(path)
                current_content = current_content_result["content"]
                lines = current_content.splitlines()
                
                # Validate line indices
                if start_line < 0 or end_line >= len(lines) or start_line > end_line:
                    raise ValueError(f"Invalid line range: {start_line}-{end_line}")
                
                # Replace the specified lines
                new_lines = lines[:start_line] + content.splitlines() + lines[end_line + 1:]
                content = '\n'.join(new_lines)
            
            # Create parent directories if they don't exist
            dir_path = os.path.dirname(full_path)
            self.container.exec_run(f"mkdir -p {dir_path}")
            
            # Write the content to the file
            # We use echo with base64 encoding to handle special characters and multi-line content
            import base64
            encoded_content = base64.b64encode(content.encode('utf-8')).decode('utf-8')
            cmd = f"echo '{encoded_content}' | base64 -d > {full_path}"
            exit_code, output = self.container.exec_run(["sh", "-c", cmd])
            
            if exit_code != 0:
                raise RuntimeError(f"Failed to write file: {output.decode('utf-8')}")
            
            return {"status": "success", "path": path}
        except Exception as e:
            raise RuntimeError(f"Failed to write file {path}: {str(e)}")
    
    async def execute_command(self, command: str) -> Dict[str, Any]:
        """Execute a bash command in the Docker container"""
        try:
            exit_code, output = self.container.exec_run(["sh", "-c", command])
            return {
                "command": command,
                "exit_code": exit_code,
                "output": output.decode('utf-8')
            }
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
        """Add and commit changes with the given message"""
        commands = [
            f"cd {working_dir} && git add .",
            f"cd {working_dir} && git commit -m \"{message}\""
        ]
        results = {}
        for cmd in commands:
            results[cmd] = await self.execute_command(cmd)
        return results
    
    async def merge_branch(self, branch_name: str, working_dir: str = "") -> Dict[str, Any]:
        """Merge the specified branch into the current branch"""
        return await self.execute_command(f"cd {working_dir} && git merge {branch_name} --no-commit --no-ff")
    
    async def merge_main(self, branch_name: str, working_dir: str = "") -> Dict[str, Any]:
        """Merge the current branch into master branch"""
        commands = [
            f"cd {working_dir} && git add .",
            f"cd {working_dir} && git commit -m 'Committing merge changes'",
            f"cd /workspace/base && git merge {branch_name}"
        ]
        results = {}
        for cmd in commands:
            results[cmd] = await self.execute_command(cmd)
        return results
    
    async def code_diff(self, working_dir: str = "") -> Dict[str, Any]:
        """Get git diff output"""
        return await self.execute_command(f"cd {working_dir} && git diff")
    
    async def merge_abort(self, working_dir: str = "") -> Dict[str, Any]:
        """Abort the current merge operation"""
        return await self.execute_command(f"cd {working_dir} && git merge --abort")
    
    async def checkout_branch(self, branch_name: str) -> Dict[str, Any]:
        """Checkout the specified branch"""
        return await self.execute_command(f"git checkout {branch_name}")
    
    async def pull_base(self) -> Dict[str, Any]:
        """Pull updates from the base workspace"""
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
        """Close the Docker client"""
        self.client.close()


async def main():
    """Interactive command-line interface for DockerEnv"""
    import asyncio
    
    # Get container name from user
    container_name = input("Enter container name or ID: ").strip()
    if not container_name:
        print("Container name cannot be empty.")
        return
    
    try:
        # Initialize the Docker environment
        docker_env = DockerEnv(container_name=container_name)
        print(f"Connected to container: {container_name}")
        
        # Print available commands
        print("\nAvailable commands:")
        print("  exec <command>          - Execute a command in the container")
        print("  read <path>             - Read a file from the container")
        print("  write <path> <content>  - Write content to a file")
        print("  update <path> <content> <start_line> <end_line> - Update specific lines in a file")
        print("  git-init <email> <name> - Initialize a Git repository")
        print("  git-commit <message> <dir> - Commit changes in directory")
        print("  git-diff <dir>          - Show Git diff in directory")
        print("  git-checkout <branch>   - Checkout a Git branch")
        print("  exit                    - Exit the program")
        
        while True:
            # Get user input
            user_input = input("\nEnter command: ").strip()
            if not user_input:
                continue
                
            # Parse command
            parts = user_input.split(maxsplit=1)
            command = parts[0].lower()
            
            # Process commands
            if command == "exit":
                print("Exiting...")
                break
                
            elif command == "exec":
                if len(parts) < 2:
                    print("Usage: exec <command>")
                    continue
                cmd = parts[1]
                result = await docker_env.execute_command(cmd)
                print(f"\nCommand: {cmd}")
                print(f"Exit code: {result['exit_code']}")
                print(f"Output:\n{result['output']}")
                
            elif command == "read":
                if len(parts) < 2:
                    print("Usage: read <path>")
                    continue
                path = parts[1]
                try:
                    result = await docker_env.read_file(path)
                    print(f"\nFile: {path}")
                    print(f"Content:\n{result['content']}")
                except Exception as e:
                    print(f"Error reading file: {str(e)}")
                
            elif command == "write":
                try:
                    path_content = parts[1].split(maxsplit=1)
                    path = path_content[0]
                    content = path_content[1] if len(path_content) > 1 else ""
                    await docker_env.write_file(path, content)
                    print(f"Successfully wrote to {path}")
                except Exception as e:
                    print(f"Error writing file: {str(e)}")
                    print("Usage: write <path> <content>")
                
            elif command == "update":
                try:
                    args = parts[1].split(maxsplit=3)
                    if len(args) < 4:
                        print("Usage: update <path> <content> <start_line> <end_line>")
                        continue
                    path, content, start_line, end_line = args
                    await docker_env.write_file(path, content, int(start_line), int(end_line))
                    print(f"Successfully updated lines {start_line}-{end_line} in {path}")
                except Exception as e:
                    print(f"Error updating file: {str(e)}")
                
            elif command == "git-init":
                try:
                    args = parts[1].split(maxsplit=1)
                    if len(args) < 2:
                        print("Usage: git-init <email> <name>")
                        continue
                    email, name = args
                    result = await docker_env.init_git_repo(email, name)
                    print("Git repository initialized:")
                    for cmd, res in result.items():
                        print(f"  {cmd}: exit_code={res['exit_code']}")
                except Exception as e:
                    print(f"Error initializing Git: {str(e)}")
                
            elif command == "git-commit":
                try:
                    args = parts[1].split(maxsplit=1)
                    if len(args) < 2:
                        print("Usage: git-commit <message> <dir>")
                        continue
                    message, directory = args
                    result = await docker_env.commit_changes(message, directory)
                    print("Commit results:")
                    for cmd, res in result.items():
                        print(f"  {cmd}: exit_code={res['exit_code']}")
                        if res['exit_code'] == 0:
                            print(f"  Output: {res['output']}")
                except Exception as e:
                    print(f"Error committing changes: {str(e)}")
                
            elif command == "git-diff":
                try:
                    directory = parts[1] if len(parts) > 1 else ""
                    result = await docker_env.code_diff(directory)
                    print(f"Git diff in {directory or 'current directory'}:")
                    print(result['output'])
                except Exception as e:
                    print(f"Error showing diff: {str(e)}")
                
            elif command == "git-checkout":
                try:
                    if len(parts) < 2:
                        print("Usage: git-checkout <branch>")
                        continue
                    branch = parts[1]
                    result = await docker_env.checkout_branch(branch)
                    print(f"Checkout result (exit_code={result['exit_code']}):")
                    print(result['output'])
                except Exception as e:
                    print(f"Error checking out branch: {str(e)}")
                
            else:
                print(f"Unknown command: {command}")
                print("Type 'exit' to quit")
        
    except Exception as e:
        print(f"Error: {str(e)}")
    finally:
        # Close the Docker client
        if 'docker_env' in locals():
            await docker_env.close()
        print("\nDocker client closed")


if __name__ == "__main__":
    import asyncio
    
    # Run the main function
    asyncio.run(main())