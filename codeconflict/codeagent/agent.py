import os
from openai import OpenAI
from pydantic import BaseModel
from typing import Optional, Type, Any, Dict, List, Union
from typing_extensions import TypeAlias
import json
import logging
import httpx
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from .models import AgentMessage, AgentAction
from .utils import format_agent_response

from ..environment.docker_env import DockerEnv

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CodeWeaverAgent:
    def __init__(self, name: str, system_prompt: str, base_url: str = "http://localhost:8080", workspace_path: str = "/workspace", agent_workspace: str = "", response_format: Type[BaseModel] = AgentMessage, action_descriptions: str = """) -> None:
            Available actions:
            - speak: Use this action to communicate your thoughts, suggestions, or responses. Always include meaningful content when using this action.
            - leave: Use this action to exit the conversation when you've reached a conclusion or consensus. No content is required for this action.
            """):
        self.console = Console()
        self.name = name
        self.response_format = response_format
        self.system_prompt = "You are " + self.name + ". " + system_prompt
        if action_descriptions:
            self.system_prompt += action_descriptions
        self.system_prompt += "\nKeep your responses concise and conversational."
        self.client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        if not os.getenv('OPENAI_API_KEY'):
            raise ValueError('OPENAI_API_KEY environment variable is not set')
        self.conversation_history = []
        # Initialize DockerEnv with agent-specific workspace
        if name == "SWE1":
            agent_workspace = "agent1workspace"
            base_url = "http://localhost:8080"
        elif name == "SWE2":
            agent_workspace = "agent2workspace"
            base_url = "http://localhost:8081"
        self.docker_env = DockerEnv(base_url=base_url, workspace_path=workspace_path, agent_workspace=agent_workspace)

    async def close(self):
        """Close the Docker environment client"""
        await self.docker_env.close()

    async def respond(self, message: Optional[str]) -> Optional[BaseModel]:
        """Generate a structured response based on the conversation history and new message"""
        # Add the received message to conversation history
        if message:
            self.conversation_history.append({"role": "user", "content": message})

        # Prepare messages for the API call
        messages = [
            {"role": "system", "content": self.system_prompt}
        ] + self.conversation_history

        try:
            response = self.client.beta.chat.completions.parse(
                model="gpt-4o-mini",
                messages=messages,
                response_format=self.response_format
            )
            
            # Get the parsed response
            parsed_response = response.choices[0].message.parsed
            logger.info(f"Model response: {parsed_response}")
            
            # Handle AgentAction responses
            if isinstance(parsed_response, AgentAction):
                # Execute the action in Docker environment
                observation = None
                logger.info(f"Executing Docker action: {parsed_response.action}")
                if parsed_response.action == 'read':
                    observation = await self.docker_env.read_file(parsed_response.path)
                    logger.info(f"Read file {parsed_response.path}: {observation}")
                elif parsed_response.action == 'write':
                    observation = await self.docker_env.write_file(parsed_response.path, parsed_response.content)
                    logger.info(f"Wrote to file {parsed_response.path}: {observation}")
                elif parsed_response.action == 'execute':
                    observation = await self.docker_env.execute_command(parsed_response.command)
                    logger.info(f"Executed command: {parsed_response.command}\nResult: {observation}")

                # Convert response to display string
                action_content = format_agent_response(self.name, parsed_response)
                observation_content = f"\nObservation: {str(observation)}"
                display_content = action_content + observation_content
            else:
                # Handle regular AgentMessage responses
                display_content = format_agent_response(self.name, parsed_response)
            
            # Create a styled panel for the response
            styled_text = Text(display_content)
            styled_text.stylize(f"bold {self._get_agent_color()}")

            # Store the string representation in conversation history
            self.conversation_history.append({
                "role": "assistant",
                "content": display_content
            })
            return parsed_response
        except Exception as e:
            self.console.print(f"[red bold]Error generating response:[/red bold] {str(e)}")
            return None

    def _get_agent_color(self) -> str:
        """Return a consistent color for the agent based on its name"""
        colors = ["blue", "green", "yellow", "magenta", "cyan", "red"]
        color_index = sum(ord(c) for c in self.name) % len(colors)
        return colors[color_index]