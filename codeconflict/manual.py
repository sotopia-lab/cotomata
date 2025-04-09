import docker

class DockerShell:
    def __init__(self, container_name):
        self.client = docker.from_env()
        self.container = self.client.containers.get(container_name)
        self.current_dir = "/workspace"  # Default starting directory

    def execute_command(self, command):
        try:
            # If the command is 'cd', update the current directory
            if command.startswith('cd '):
                new_dir = command[3:].strip()
                # Handle relative and absolute paths
                if new_dir.startswith('/'):
                    check_dir = new_dir
                else:
                    check_dir = f"{self.current_dir}/{new_dir}"
                
                # Verify if directory exists
                result = self.container.exec_run(
                    f'test -d {check_dir} && echo "EXISTS"',
                    workdir=self.current_dir
                )
                if result.output.decode().strip() == "EXISTS":
                    self.current_dir = check_dir
                else:
                    print(f"Directory not found: {new_dir}")
                return

            # Execute command in current directory
            result = self.container.exec_run(
                cmd=f'/bin/bash -c "{command}"',
                workdir=self.current_dir,
                tty=True
            )
            
            # Print output
            output = result.output.decode('utf-8')
            if output:
                print(output.rstrip())

        except Exception as e:
            print(f"Error: {str(e)}")

    def run_interactive(self):
        print(f"Starting interactive shell in container. Current directory: {self.current_dir}")
        while True:
            command = input(f"\n{self.current_dir}$ ")
            if command.lower() == 'exit':
                break
            if command.strip():
                self.execute_command(command)

if __name__ == "__main__":
    container_name = "hello_world_test"
    try:
        shell = DockerShell(container_name)
        shell.run_interactive()
    except docker.errors.NotFound:
        print(f"Container '{container_name}' not found")
    except Exception as e:
        print(f"Error: {str(e)}")
