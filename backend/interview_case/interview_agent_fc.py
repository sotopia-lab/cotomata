import logging
import sys
from enum import Enum
from rich.logging import RichHandler
from pydantic import Field, BaseModel
from typing import Optional, List, Dict, Any
from openai import OpenAI
from aact import Message, NodeFactory
from aact.messages import Text, Tick, DataModel
from aact.messages.registry import DataModelFactory
from .base_agent import BaseAgent  # type: ignore[import-untyped]
import json
import os

# Check Python version
if sys.version_info >= (3, 11):
    pass
else:
    pass

# Configure logging
FORMAT = "%(asctime)s - %(levelname)s - %(name)s - %(message)s"
logging.basicConfig(
    level=logging.WARNING,
    format=FORMAT,
    datefmt="[%X]",
    handlers=[RichHandler()],
)


class ActionType(Enum):
    NONE = "none"
    SPEAK = "speak"
    NON_VERBAL = "non-verbal"
    LEAVE = "leave"
    THOUGHT = "thought"
    BROWSE = "browse"
    BROWSE_ACTION = "browse_action"
    READ = "read"
    WRITE = "write"
    RUN = "run"

    def __str__(self) -> str:
        return self.value

    def __eq__(self, other: object) -> bool:
        if isinstance(other, ActionType):
            return self.value == other.value
        elif isinstance(other, str):
            return self.value == other
        else:
            return NotImplemented


class AgentFunctionArgs(BaseModel):
    content: Optional[str] = Field(None, description="Content for speak, thought, or non-verbal actions")
    url: Optional[str] = Field(None, description="URL for browse action")
    command: Optional[str] = Field(None, description="Command for browse_action or run actions")
    path: Optional[str] = Field(None, description="File path for read/write actions")

def get_agent_functions(agent_name: str) -> List[Dict[str, Any]]:
    """Define the available tools for the agent."""
    return [
        {
            "type": "function",
            "function": {
                "name": "speak",
                "description": "Talk to other agents to share information or ask them something",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "content": {
                            "type": "string",
                            "description": "The message to send to other agents (should be short)"
                        }
                    },
                    "required": ["content"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "thought",
                "description": "Record thoughts, plans, or goals (use rarely, max 2 turns)",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "content": {
                            "type": "string",
                            "description": "Your thoughts or plans (should be short)"
                        }
                    },
                    "required": ["content"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "browse",
                "description": "Open a web page",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "url": {
                            "type": "string",
                            "description": "The URL to open"
                        }
                    },
                    "required": ["url"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "browse_action",
                "description": "Perform actions in the web browser. Available commands include navigation, interaction, and form manipulation.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "command": {
                            "type": "string",
                            "description": """Browser command to execute. Available commands:
                                    1. goto(url: str) - Navigate to a URL. Example: goto('http://www.example.com')
                                    2. go_back() - Navigate to previous page. Example: go_back()
                                    3. go_forward() - Navigate to next page. Example: go_forward()
                                    4. noop(wait_ms: float = 1000) - Do nothing/wait for page load. Example: noop() or noop(500)
                                    5. scroll(delta_x: float, delta_y: float) - Scroll horizontally/vertically. Example: scroll(0, 200)
                                    6. fill(bid: str, value: str) - Fill form field. Example: fill('237', 'example value')
                                    7. select_option(bid: str, options: str | list[str]) - Select dropdown options. Example: select_option('a48', 'blue')
                                    8. click(bid: str, button='left', modifiers=[]) - Click element. Example: click('a51')
                                    9. dblclick(bid: str, button='left', modifiers=[]) - Double click element. Example: dblclick('12')
                                    10. hover(bid: str) - Hover over element. Example: hover('b8')
                                    11. press(bid: str, key_comb: str) - Press keys. Example: press('88', 'Backspace')
                                    12. focus(bid: str) - Focus element. Example: focus('b455')
                                    13. clear(bid: str) - Clear input field. Example: clear('996')
                                    14. drag_and_drop(from_bid: str, to_bid: str) - Drag and drop. Example: drag_and_drop('56', '498')
                                    15. upload_file(bid: str, file: str | list[str]) - Upload files. Example: upload_file('572', '/path/to/file.pdf')"""
                        }
                    },
                    "required": ["command"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "read",
                "description": "Read the contents of a file",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "Path of the file to read"
                        }
                    },
                    "required": ["path"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "write",
                "description": "Write content to a file",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "Path of the file to write"
                        },
                        "content": {
                            "type": "string",
                            "description": "Content to write to the file"
                        }
                    },
                    "required": ["path", "content"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "run",
                "description": "Run a command in the Linux shell",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "command": {
                            "type": "string",
                            "description": "Command to execute"
                        }
                    },
                    "required": ["command"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "none",
                "description": "Do nothing this turn",
                "parameters": {
                    "type": "object",
                    "properties": {},
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "leave",
                "description": "Leave the conversation when goals are completed",
                "parameters": {
                    "type": "object",
                    "properties": {},
                }
            }
        }
    ]


@DataModelFactory.register("agent_action")
class AgentAction(DataModel):
    agent_name: str = Field(description="the name of the agent")
    action_type: ActionType = Field(
        description="whether to speak at this turn or choose to not do anything"
    )
    argument: str = Field(
        description="the utterance if choose to speak, the expression or gesture if choose non-verbal communication, or the physical action if choose action"
    )
    path: Optional[str] = Field(description="path of file")

    def to_natural_language(self) -> str:
        action_descriptions = {
            ActionType.NONE: "did nothing",
            ActionType.SPEAK: f'said: "{self.argument}"',
            ActionType.THOUGHT: f'thought: "{self.argument}"',
            ActionType.BROWSE: f'browsed: "{self.argument}"',
            ActionType.RUN: f'ran: "{self.argument}"',
            ActionType.READ: f'read: "{self.argument}"',
            ActionType.WRITE: f'wrote: "{self.argument}"',
            ActionType.NON_VERBAL: f"[{self.action_type.value}] {self.argument}",
            ActionType.LEAVE: "left the conversation",
        }

        return action_descriptions.get(self.action_type, "performed an unknown action")


@NodeFactory.register("llm_agent_fc")
class LLMAgent(BaseAgent[AgentAction | Tick | Text, AgentAction]):
    def __init__(
        self,
        input_text_channels: list[str],
        input_tick_channel: str,
        input_env_channels: list[str],
        output_channel: str,
        query_interval: int,
        agent_name: str,
        goal: str,
        model_name: str,
        redis_url: str,
    ):
        super().__init__(
            [
                (input_text_channel, AgentAction)
                for input_text_channel in input_text_channels
            ]
            + [
                (input_tick_channel, Tick),
            ]
            + [(input_env_channel, Text) for input_env_channel in input_env_channels],
            [(output_channel, AgentAction)],
            redis_url,
        )
        self.output_channel = output_channel
        self.query_interval = query_interval
        self.count_ticks = 0
        self.message_history: List[Dict[str, Any]] = []
        self.name = agent_name
        self.model_name = model_name
        self.goal = goal
        self.client = OpenAI()

    async def send(self, message: AgentAction) -> None:
        if message.action_type in ("speak", "thought"):
            await self.r.publish(
                self.output_channel,
                Message[AgentAction](data=message).model_dump_json(),
            )
        elif message.action_type in ("browse", "browse_action", "write", "read", "run"):
            await self.r.publish(
                "Agent:Runtime",
                Message[AgentAction](data=message).model_dump_json(),
            )

    def _add_to_history(self, role: str, text: str, action_type: str = "text") -> None:
        """Add a message to the conversation history."""
        # For assistant and user messages, use simple text content
        if role in ["assistant", "user", "system"]:
            self.message_history.append({
                "role": role,
                "content": text
            })
        # For tool responses, use the proper tool message format
        elif role == "tool":
            self.message_history.append({
                "role": "tool",
                "tool_call_id": "call_" + str(len(self.message_history)),
                "name": action_type,
                "content": text
            })

    def _format_message_history(self, message_history: List[Dict[str, Any]]) -> str:
        """Format message history for display in the prompt."""
        formatted_messages = []
        for msg in message_history:
            role = msg["role"]
            for content in msg["content"]:
                formatted_messages.append(f"{role}: {content['text']}")
        return "\n".join(formatted_messages)

    async def aact(self, message: AgentAction | Tick | Text) -> AgentAction:
        match message:
            case Text(text=text):
                if "BrowserOutputObservation" in text:
                    text = text.split("BrowserOutputObservation", 1)[1][:100]
                    self._add_to_history("system", text)
                else:
                    self._add_to_history("system", text)
                return AgentAction(
                    agent_name=self.name, action_type="none", argument="", path=""
                )
            case Tick():
                self.count_ticks += 1
                if self.count_ticks % self.query_interval == 0:
                    try:
                        response = self.client.chat.completions.create(
                            model=self.model_name,
                            messages=[
                                {
                                    "role": "system",
                                    "content": f"You are an AI agent named {self.name}. Your goal is: {self.goal}"
                                }
                            ] + self.message_history + [
                                {
                                    "role": "user",
                                    "content": "What would you like to do next?"
                                }
                            ],
                            tools=get_agent_functions(self.name),
                            tool_choice="auto"
                        )
                        
                        tool_calls = response.choices[0].message.tool_calls
                        print(tool_calls)
                        if not tool_calls:
                            return AgentAction(
                                agent_name=self.name,
                                action_type="none",
                                argument="",
                                path=""
                            )

                        # Get the first tool call
                        tool_call = tool_calls[0]
                        action_type = tool_call.function.name
                        args = json.loads(tool_call.function.arguments)

                        # Add assistant's response to history
                        self._add_to_history("assistant", f"Using {action_type}")
                        
                        if action_type == "thought":
                            content = args.get("content", "")
                            self._add_to_history("assistant", content)
                            return AgentAction(
                                agent_name=self.name,
                                action_type=action_type,
                                argument=content,
                                path=""
                            )
                        elif action_type == "speak":
                            content = args.get("content", "")
                            self._add_to_history("assistant", content)
                            return AgentAction(
                                agent_name=self.name,
                                action_type=action_type,
                                argument=content,
                                path=""
                            )
                        elif action_type == "browse":
                            url = args.get("url", "")
                            self._add_to_history("assistant", f"Browsing {url}")
                            return AgentAction(
                                agent_name=self.name,
                                action_type=action_type,
                                argument=url,
                                path=""
                            )
                        elif action_type == "browse_action":
                            command = args.get("command", "")
                            self._add_to_history("assistant", f"Browser action: {command}")
                            return AgentAction(
                                agent_name=self.name,
                                action_type=action_type,
                                argument=command,
                                path=""
                            )
                        elif action_type == "write":
                            path = args.get("path", "")
                            content = args.get("content", "")
                            self._add_to_history("assistant", f"Writing to {path}")
                            return AgentAction(
                                agent_name=self.name,
                                action_type=action_type,
                                argument=content,
                                path=path
                            )
                        elif action_type == "read":
                            path = args.get("path", "")
                            self._add_to_history("assistant", f"Reading from {path}")
                            return AgentAction(
                                agent_name=self.name,
                                action_type=action_type,
                                argument="Nan",
                                path=path
                            )
                        elif action_type == "run":
                            command = args.get("command", "")
                            self._add_to_history("assistant", f"Running command: {command}")
                            return AgentAction(
                                agent_name=self.name,
                                action_type=action_type,
                                argument=command,
                                path=""
                            )
                        else:
                            return AgentAction(
                                agent_name=self.name,
                                action_type="none",
                                argument="",
                                path=""
                            )
                    except Exception as e:
                        print(f"Error during OpenAI call: {e}")
                        return AgentAction(
                            agent_name=self.name,
                            action_type="none",
                            argument="",
                            path=""
                        )
                else:
                    return AgentAction(
                        agent_name=self.name,
                        action_type="none",
                        argument="",
                        path=""
                    )
            case AgentAction(
                agent_name=agent_name,
                action_type=action_type,
                argument=text
            ):
                if action_type == "speak":
                    self._add_to_history("user", text)
                return AgentAction(
                    agent_name=self.name,
                    action_type="none",
                    argument="",
                    path=""
                )
        raise ValueError(f"Unexpected message type: {type(message)}")