import os
import json
import docker
import asyncio
from openai import OpenAI

class DockerAgent:
    def __init__(self, container_name, container_host='unix://var/run/docker.sock'):
        self.container_name = container_name
        self.docker_client = docker.DockerClient(base_url=container_host)
        self.client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        if not os.getenv('OPENAI_API_KEY'):
            raise ValueError('OPENAI_API_KEY environment variable is not set')
        self.container = None
        
    async def connect_to_container(self):
        """Connect to the specified Docker container"""
        try:
            self.container = self.docker_client.containers.get(self.container_name)
            print(f'Connected to container {self.container_name}')
            return True
        except docker.errors.NotFound:
            print(f'Container {self.container_name} not found')
            return False
        except Exception as e:
            print(f'Failed to connect to container: {e}')
            return False

    async def send_command(self, command):
        """Execute a command in the container using Docker exec API"""
        try:
            if not self.container:
                raise ValueError('Container is not connected')
            
            # Split the command string into a list if it's not already
            if isinstance(command, str):
                command = command.split()
                
            # Create and start exec instance using the low-level API
            exec_config = {
                'cmd': command,
                'stdout': True,
                'stderr': True,
                'tty': False
            }
            
            # Use the container's API client to create and start exec instance
            exec_id = self.container.client.api.exec_create(self.container.id, **exec_config)
            output = self.container.client.api.exec_start(exec_id['Id'])
            
            return {'output': output.decode('utf-8')}
        except Exception as e:
            print(f'Error executing command: {e}')
            return None

    async def process_with_openai(self, user_input):
        """Process user input with OpenAI to generate appropriate commands"""
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "You are a bash command generator for Docker containers. Always wrap your command in <bash></bash> tags and provide only the exact command to execute, no explanations or markdown formatting."}, 
                    {"role": "user", "content": user_input}
                ]
            )
            content = response.choices[0].message.content
            
            # Extract command from between <bash></bash> tags
            import re
            match = re.search(r'<bash>(.*?)</bash>', content, re.DOTALL)
            if match:
                return match.group(1).strip()
            return content.strip()
        except Exception as e:
            print(f'Error processing with OpenAI: {e}')
            return None

    async def run_interactive(self):
        """Run an interactive session with the container"""
        if not await self.connect_to_container():
            return

        print('Interactive session started. Type \'exit\' to quit.')
        while True:
            try:
                user_input = input('> ')
                if user_input.lower() == 'exit':
                    break

                command = await self.process_with_openai(user_input)
                if command:
                    print(f'Generated command: {command}')
                    result = await self.send_command(command)
                    if result:
                        print(f'Output: {result["output"]}')
            except KeyboardInterrupt:
                print("\nExiting...")
                break
            except Exception as e:
                print(f"Error: {e}")

        self.docker_client.close()

def main():
    try:
        agent = DockerAgent('hello_world_test')
        
        # Create a new event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # Run the interactive session
        loop.run_until_complete(agent.run_interactive())
    except KeyboardInterrupt:
        print("\nExiting...")
    finally:
        loop.close()

if __name__ == '__main__':
    main()