import os
from openai import OpenAI
from pydantic import BaseModel
from typing import Optional, Type, Any, Dict, List, Union
from typing_extensions import TypeAlias
import json
import logging
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from .models import AgentMessage
from .utils import format_agent_response

# # Configure logging
# logging.basicConfig(level=logging.INFO)
# logger = logging.getLogger(__name__)

class CodeWeaverAgent:
    def __init__(self, name: str, system_prompt: str, response_format: Type[BaseModel] = AgentMessage, action_descriptions: str = """) -> None:
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

    def respond(self, message: Optional[str]) -> Optional[BaseModel]:
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
            
            # Log the raw response for debugging
            # logger.debug(f"Raw response from API: {response}")
            
            # Get the parsed response
            parsed_response = response.choices[0].message.parsed
            
            # Convert response to display string using utility function
            display_content = format_agent_response(self.name, parsed_response)
            
            # Create a styled panel for the response
            styled_text = Text(display_content)
            styled_text.stylize(f"bold {self._get_agent_color()}")
            # self.console.print(Panel(styled_text, title=self.name, border_style=self._get_agent_color()))

            # Store the string representation in conversation history
            self.conversation_history.append({
                "role": "assistant",
                "content": display_content
            })
            # print(parsed_response.model_dump_json())
            return parsed_response
        except Exception as e:
            self.console.print(f"[red bold]Error generating response:[/red bold] {str(e)}")
            return None

    def _get_agent_color(self) -> str:
        """Return a consistent color for the agent based on its name"""
        # Use a simple hash of the agent name to select a color
        colors = ["blue", "green", "yellow", "magenta", "cyan", "red"]
        color_index = sum(ord(c) for c in self.name) % len(colors)
        return colors[color_index]