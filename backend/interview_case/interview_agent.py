import logging
import sys
from enum import Enum
from rich.logging import RichHandler
from pydantic import Field

from typing import Optional, Any

from aact import Message, NodeFactory
from aact.messages import Text, Tick, DataModel
from aact.messages.registry import DataModelFactory

from .base_agent import BaseAgent  # type: ignore[import-untyped]
from .generate import agenerate # type: ignore[import-untyped]
from .generate import StrOutputParser
from .generate import agenerate_agent_response
from .agent_models import AgentResponse, ActionType

import json
import asyncio

# Configure basic logging
FORMAT = "%(message)s"
logging.basicConfig(
    level=logging.INFO,
    format=FORMAT,
    datefmt="[%X]",
    handlers=[RichHandler(show_time=False, show_path=False)]
)

logger = logging.getLogger(__name__)

def format_box_message(title: str, content: str) -> str:
    """Format a message in a nice box with title."""
    width = min(100, max(len(line) for line in content.split('\n')) + 4)
    horizontal_line = "─" * width
    padded_content = "\n".join(f"│ {line:<{width-2}} │" for line in content.split('\n'))
    
    title_line = f"╭─ {title} "
    title_line += "─" * (width - len(title_line) - 1) + "╮"
    bottom_line = "╰" + horizontal_line + "╯"
    
    return f"{title_line}\n{padded_content}\n{bottom_line}"

def log_agent_action(agent_name: str, thinking: str | None = None, action: str | None = None) -> None:
    """Log agent thoughts and actions to the logger only."""
    if thinking:
        logger.info(f"[{agent_name}] Thinking: {thinking}")
    
    if action:
        logger.info(f"[{agent_name}] Action: {action}")

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
    thinking: Optional[str] = Field(description="the agent's thought process before taking the action", default=None)

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
        description = action_descriptions.get(self.action_type, "performed an unknown action")
        if self.thinking:
            description = f'(thinking: "{self.thinking}") ' + description
        return description

@NodeFactory.register("llm_agent")
class LLMAgent(BaseAgent[AgentAction | Tick | Text, AgentAction]):
    def __init__(
        self,
        input_text_channels: list[str],
        input_tick_channel: str,
        input_env_channels: list[str],
        output_channel: str,
        turn_order: int,
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
        self.turn_order = turn_order
        self.current_turn = turn_order  # Start at own turn order
        self.last_action_time = 0
        self.count_ticks = 0
        self.message_history: list[tuple[str, str, str]] = []
        self.name = agent_name
        self.model_name = model_name
        self.goal = goal
        self.MIN_TICKS_BETWEEN_ACTIONS = 10  # Increased delay between actions
        self.error_count = 0  # Track consecutive errors
        self.MAX_ERRORS = 3  # Maximum number of consecutive errors before backing off
        self.none_action_count = 0  # Track consecutive none actions
        self.MAX_NONE_ACTIONS = 20  # Maximum consecutive none actions before forcing turn

    def _should_force_turn(self) -> bool:
        """Determine if we should force a turn due to deadlock."""
        return self.none_action_count >= self.MAX_NONE_ACTIONS

    async def send(self, message: AgentAction) -> None:
        try:
            # Actions that should be sent to the output channel
            output_channel_actions = {
                "speak", "thought", "non-verbal", "leave"
            }
            
            # Actions that should be sent to the runtime channel
            runtime_channel_actions = {
                "browse", "browse_action", "write", "read", "run"
            }
            
            logger.info(f"[{self.name}] Sending action: {message.action_type}")
            
            if str(message.action_type) in output_channel_actions:
                logger.info(f"[{self.name}] Publishing to output channel: {message.action_type}")
                await self.r.publish(
                    self.output_channel,
                    Message[AgentAction](data=message).model_dump_json(),
                )
                # Add to message history immediately for output actions
                if message.argument:
                    self.message_history.append(
                        (self.name, str(message.action_type), message.argument)
                    )
                    logger.info(f"[{self.name}] Added to history: {message.action_type} - {message.argument[:50]}...")
            
            elif str(message.action_type) in runtime_channel_actions:
                logger.info(f"[{self.name}] Publishing to runtime channel: {message.action_type}")
                await self.r.publish(
                    "Agent:Runtime",
                    Message[AgentAction](data=message).model_dump_json(),
                )
                
                # Add to message history after sending to runtime
                if message.argument:
                    self.message_history.append(
                        (self.name, str(message.action_type), message.argument)
                    )
                    logger.info(f"[{self.name}] Added to history: {message.action_type} - {message.argument[:50]}...")
                elif message.path:
                    self.message_history.append(
                        (self.name, str(message.action_type), message.path)
                    )
                    logger.info(f"[{self.name}] Added to history: {message.action_type} - {message.path}")
            
            # Update timing for any non-none action
            if str(message.action_type) != "none":
                self.last_action_time = self.count_ticks
                logger.info(f"[{self.name}] Updated action time to: {self.last_action_time}")
                
        except Exception as e:
            logger.error(f"[{self.name}] Error sending message: {e}")
            raise

    async def aact(self, message: AgentAction | Tick | Text) -> AgentAction:
        try:
            logger.info(f"[{self.name}] Processing message type: {type(message)}")
            
            match message:
                case Text(text=text):
                    logger.info(f"[{self.name}] Processing Text message: {text[:100]}...")
                    
                    if "BrowserOutputObservation" in text:
                        text = text.split("BrowserOutputObservation", 1)[1][:100]
                        logger.info(f"[{self.name}] Processing browser observation: {text}")
                        self.message_history.append((self.name, "observation data", text))
                        self.error_count = 0  # Reset error count on successful action
                        self.none_action_count = 0  # Reset none action count on successful action
                    else:
                        # Add observation to history
                        logger.info(f"[{self.name}] Processing observation data: {text[:100]}...")
                        self.message_history.append((self.name, "observation data", text))
                        self.error_count = 0  # Reset error count on successful action
                        self.none_action_count = 0  # Reset none action count on successful action
                    
                    return AgentAction(
                        agent_name=self.name, action_type="none", argument="", path=""
                    )
                    
                case Tick():
                    current_time = self.count_ticks
                    self.count_ticks += 1
                    
                    # Check if enough time has passed since last action
                    time_since_last = current_time - self.last_action_time
                    if time_since_last < self.MIN_TICKS_BETWEEN_ACTIONS:
                        self.none_action_count += 1
                        return AgentAction(
                            agent_name=self.name, action_type="none", argument="", path=""
                        )
                    
                    # Simple turn check - if we've seen too many none actions, force our turn
                    if self._should_force_turn():
                        logger.warning(f"[{self.name}] Forcing turn after {self.none_action_count} none actions")
                        self.current_turn = self.turn_order  # Reset to our turn
                        self.none_action_count = 0
                    else:
                        # Normal turn alternation
                        is_my_turn = (self.current_turn == self.turn_order)
                        if not is_my_turn:
                            self.none_action_count += 1
                            return AgentAction(
                                agent_name=self.name, action_type="none", argument="", path=""
                            )
                    
                    logger.info(f"[{self.name}] Turn info - Current: {self.current_turn}, Taking Turn: {True}")

                    # If we've had too many errors, back off for longer
                    if self.error_count >= self.MAX_ERRORS:
                        logger.warning(f"[{self.name}] Too many consecutive errors ({self.error_count}), backing off")
                        self.last_action_time = current_time  # Reset timing to force delay
                        self.error_count = 0  # Reset error count
                        self.none_action_count = 0  # Reset none action count
                        return AgentAction(
                            agent_name=self.name,
                            action_type="none",
                            argument="",
                            path="",
                            thinking="Backing off after multiple errors"
                        )

                    try:
                        logger.info(f"[{self.name}] Generating response...")
                        response = await agenerate_agent_response(
                            model_name=self.model_name,
                            agent_name=self.name,
                            history=self._format_message_history(self.message_history),
                            goal=self.goal,
                            temperature=0.7,
                        )
                        
                        if not response:
                            self.error_count += 1
                            self.none_action_count += 1
                            logger.error(f"[{self.name}] Failed to generate response (error #{self.error_count})")
                            return AgentAction(
                                agent_name=self.name,
                                action_type="none",
                                argument="",
                                path="",
                                thinking=f"Encountered error #{self.error_count}, will retry after delay"
                            )
                        
                        # On successful response, update turn and reset counters
                        self.current_turn = 3 - self.turn_order  # Toggle between 1 and 2
                        self.none_action_count = 0
                        self.error_count = 0
                        
                        logger.info(f"[{self.name}] Generated response: {response.action}")
                        
                        # Log agent's thinking and response
                        if hasattr(response, 'thinking'):
                            log_agent_action(self.name, thinking=response.thinking)
                        
                        # Update timing info ONLY for non-none actions
                        if response.action != "none":
                            self.last_action_time = current_time
                            logger.info(f"[{self.name}] Updated action timing")
                        
                        # For runtime actions, set a longer delay
                        if response.action in ["write", "run", "read", "browse", "browse_action"]:
                            self.last_action_time = current_time + 3  # Extra delay for runtime actions
                        
                        # Process response into action
                        try:
                            if response.action == "speak":
                                content = response.args.content
                                log_agent_action(self.name, action=f'Says: "{content}"')
                                self.message_history.append((self.name, "speak", content))
                                return AgentAction(
                                    agent_name=self.name,
                                    action_type="speak",
                                    argument=content,
                                    path="",
                                    thinking=response.thinking if hasattr(response, 'thinking') else None
                                )
                            elif response.action == "write":
                                path = response.args.path
                                content = response.args.content
                                
                                # Check recent history for similar write actions
                                recent_writes = [msg for msg in self.message_history[-10:]
                                               if msg[1] == "write"]
                                
                                if any(content in write[2] for write in recent_writes):
                                    # If we've tried this write before, skip it
                                    logger.info(f"[{self.name}] Skipping duplicate write to: {path}")
                                    return AgentAction(
                                        agent_name=self.name,
                                        action_type="none",
                                        argument="",
                                        path="",
                                        thinking=f"Already attempted to write similar content to {path}"
                                    )
                                
                                log_agent_action(self.name, action=f'Writes to file: {path}')
                                return AgentAction(
                                    agent_name=self.name,
                                    action_type="write",
                                    argument=content,
                                    path=path,
                                    thinking=response.thinking if hasattr(response, 'thinking') else None
                                )
                            elif response.action == "thought":
                                content = response.args.content
                                log_agent_action(self.name, action=f'Thinks: "{content}"')
                                self.message_history.append((self.name, "thought", content))
                                return AgentAction(
                                    agent_name=self.name,
                                    action_type="thought",
                                    argument=content,
                                    path="",
                                    thinking=response.thinking if hasattr(response, 'thinking') else None
                                )
                            elif response.action == "non-verbal":
                                content = response.args.content
                                log_agent_action(self.name, action=f'Gestures: {content}')
                                self.message_history.append((self.name, "non-verbal", content))
                                return AgentAction(
                                    agent_name=self.name,
                                    action_type="non-verbal",
                                    argument=content,
                                    path="",
                                    thinking=response.thinking if hasattr(response, 'thinking') else None
                                )
                            elif response.action == "browse":
                                url = response.args.url
                                log_agent_action(self.name, action=f'Browses: {url}')
                                return AgentAction(
                                    agent_name=self.name,
                                    action_type="browse",
                                    argument=url,
                                    path="",
                                    thinking=response.thinking if hasattr(response, 'thinking') else None
                                )
                            elif response.action == "browse_action":
                                command = response.args.command
                                log_agent_action(self.name, action=f'Browser action: {command}')
                                return AgentAction(
                                    agent_name=self.name,
                                    action_type="browse_action",
                                    argument=command,
                                    path="",
                                    thinking=response.thinking if hasattr(response, 'thinking') else None
                                )
                            elif response.action == "read":
                                path = response.args.path
                                log_agent_action(self.name, action=f'Reads file: {path}')
                                return AgentAction(
                                    agent_name=self.name,
                                    action_type="read",
                                    argument="",
                                    path=path,
                                    thinking=response.thinking if hasattr(response, 'thinking') else None
                                )
                            elif response.action == "run":
                                command = response.args.command
                                log_agent_action(self.name, action=f'Runs command: {command}')
                                return AgentAction(
                                    agent_name=self.name,
                                    action_type="run",
                                    argument=command,
                                    path="",
                                    thinking=response.thinking if hasattr(response, 'thinking') else None
                                )
                            elif response.action == "none":
                                log_agent_action(self.name, action="Does nothing")
                                return AgentAction(
                                    agent_name=self.name,
                                    action_type="none",
                                    argument="",
                                    path="",
                                    thinking=response.thinking if hasattr(response, 'thinking') else None
                                )
                            elif response.action == "leave":
                                log_agent_action(self.name, action="Leaves the conversation")
                                return AgentAction(
                                    agent_name=self.name,
                                    action_type="leave",
                                    argument="",
                                    path="",
                                    thinking=response.thinking if hasattr(response, 'thinking') else None
                                )
                            
                        except AttributeError as e:
                            logger.error(f"[{self.name}] Error processing response action: {e}")
                            # If we can't process the action, return none and try again next turn
                            return AgentAction(
                                agent_name=self.name,
                                action_type="none",
                                argument="",
                                path="",
                                thinking="Had trouble processing the last action, will retry"
                            )
                            
                    except Exception as e:
                        logger.error(f"[{self.name}] Error generating response: {e}")
                        # Don't raise, just return none action and try again next turn
                        return AgentAction(
                            agent_name=self.name,
                            action_type="none",
                            argument="",
                            path="",
                            thinking="Encountered an error, will retry next turn"
                        )

                case AgentAction(agent_name=agent_name, action_type=action_type, argument=text):
                    # Track all actions in message history, not just speak
                    action_str = str(action_type)
                    
                    try:
                        # Update turn based on other agent's action
                        if action_str != "none" and agent_name != self.name:
                            # Other agent took action, next turn is ours
                            self.current_turn = self.turn_order
                            self.none_action_count = 0  # Reset none count when turn changes
                            logger.info(f"[{self.name}] Updated turn to {self.current_turn} after {agent_name}'s action")
                        
                        # Add thinking to history if present
                        if message.thinking:
                            self.message_history.append((agent_name, "thinking", message.thinking))
                            logger.info(f"[{self.name}] Added thinking to history: {message.thinking[:50]}...")
                        
                        if action_str in ["speak", "thought", "non-verbal", "browse", "browse_action", "run"]:
                            self.message_history.append((agent_name, action_str, text))
                            logger.info(f"[{self.name}] Added action to history: {action_str} - {text[:50]}...")
                        elif action_str in ["read", "write"]:
                            # For file operations, include both path and content
                            if message.path:
                                content = f"{message.path}: {text}" if text else message.path
                                self.message_history.append((agent_name, action_str, content))
                                logger.info(f"[{self.name}] Added file operation to history: {action_str} - {content}")
                        
                    except Exception as e:
                        logger.error(f"[{self.name}] Error processing agent action: {e}")
                        self.error_count += 1
                    
                    return AgentAction(
                        agent_name=self.name,
                        action_type="none",
                        argument="",
                        path="",
                        thinking=None
                    )
        
        except Exception as e:
            logger.error(f"[{self.name}] Unexpected error in aact: {e}")
            # Return none action instead of raising
            return AgentAction(
                agent_name=self.name,
                action_type="none",
                argument="",
                path="",
                thinking="Encountered an unexpected error, will retry"
            )

    def _format_message_history(self, message_history: list[tuple[str, str, str]]) -> str:
        logger.info(f"[{self.name}] Formatting message history with {len(message_history)} messages")
        formatted_messages = []
        scene_setup = None
        workspace_state = []
        
        for speaker, action, message in message_history:
            logger.debug(f"[{self.name}] Processing history entry: {speaker} - {action}")
            match action:
                case "scene_setup":
                    scene_setup = message
                    logger.info(f"[{self.name}] Found scene setup message")
                case "thinking":
                    formatted_messages.append(f"{speaker} thinking: {message}")
                case "speak":
                    formatted_messages.append(f"{speaker}: {message}")
                case "thought":
                    formatted_messages.append(f"{speaker} thinks: {message}")
                case "non-verbal":
                    formatted_messages.append(f"{speaker} {message}")
                case "browse":
                    formatted_messages.append(f"{speaker} browses documentation: {message}")
                case "browse_action":
                    formatted_messages.append(f"{speaker} browser action: {message}")
                case "read":
                    formatted_messages.append(f"Content from {message} is available in workspace")
                    workspace_state.append(f"File {message} has been read")
                case "write":
                    formatted_messages.append(f"Content has been written to {message}")
                    workspace_state.append(f"File {message} has been updated")
                case "run":
                    formatted_messages.append(f"{speaker} executed command: {message}")
                case "observation data":
                    if "file contents" in message.lower():
                        workspace_state.append(message)
                    else:
                        formatted_messages.append(f"Runtime output: {message}")
                case _:
                    formatted_messages.append(f"{speaker} {action}: {message}")
        
        # Add scene setup at the beginning if it exists
        if scene_setup:
            formatted_messages.insert(0, scene_setup)
            logger.info(f"[{self.name}] Added scene setup to history")
        
        # Add workspace state after scene setup
        if workspace_state:
            formatted_messages.insert(1, "\nWorkspace State:")
            for state in workspace_state[-5:]:  # Only show last 5 workspace states
                formatted_messages.insert(2, f"- {state}")
            formatted_messages.insert(len(workspace_state) + 2, "")
        
        result = "\n".join(formatted_messages)
        logger.info(f"[{self.name}] Final history length: {len(result)} characters")
        return result