import sys
from enum import Enum
from pydantic import Field, BaseModel
from typing import Optional, List, Dict, Any, AsyncGenerator
import asyncio
from datetime import datetime, timedelta
import json
import time

from aact import Message, NodeFactory
from aact.messages import Text, Tick, DataModel
from aact.messages.registry import DataModelFactory

from .base_agent import BaseAgent
from .generate import agenerate_chunked
from .generate import StrOutputParser

def print_divider():
    print("\n" + "="*50)

class AgentState(Enum):
    IDLE = "idle"
    LISTENING = "listening"
    THINKING = "thinking"
    SPEAKING = "speaking"

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
    urgency: float = Field(
        description="how urgent this action is (0-1)", default=0.5
    )

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

@NodeFactory.register("llm_agent_async")
class AsyncLLMAgent(BaseAgent[AgentAction | Tick | Text, AgentAction]):
    def __init__(
        self,
        input_text_channels: list[str],
        input_tick_channel: str,
        input_env_channels: list[str],
        output_channel: str,
        agent_name: str,
        goal: str,
        model_name: str,
        redis_url: str,
        min_response_delay: float = 1.0,
        attention_threshold: float = 0.7,
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
        self.message_history: list[tuple[str, str, str, float]] = []
        self.name = agent_name
        self.model_name = model_name
        self.goal = goal
        self.state = AgentState.IDLE
        self.last_action_time = datetime.now()
        self.last_message_time = time.time()  # Use time.time() for consistency
        self.min_response_delay = min_response_delay
        self.attention_threshold = attention_threshold
        self.current_generation: Optional[AsyncGenerator[AgentAction, None]] = None
        self.message_queue: asyncio.Queue[AgentAction] = asyncio.Queue()
        self.silence_threshold = 20.0  # Seconds before forcing action
        self.consecutive_errors = 0
        self.messages_processed = 0
        self.accumulated_json = ""
        self.output_parser = StrOutputParser()  # Initialize the output parser
        
        print(f"Initialized {self.name} with model {self.model_name}")
        print(f"Input channels: {input_text_channels}")
        print(f"Output channel: {output_channel}")
        print(f"Goal: {goal}")

        # Start the message queue processor
        asyncio.create_task(self.process_message_queue())

    async def send(self, message: AgentAction) -> None:
        print(f"[{self.name}] Sending: {message.to_natural_language()}")
        if str(message.action_type) in ("speak", "thought"):
            print(f"[{self.name}] Publishing to {self.output_channel}")
            await self.r.publish(
                self.output_channel,
                Message[AgentAction](data=message).model_dump_json(),
            )
        elif str(message.action_type) in ("browse", "browse_action", "write", "read", "run"):
            print(f"[{self.name}] Publishing to Agent:Runtime")
            await self.r.publish(
                "Agent:Runtime",
                Message[AgentAction](data=message).model_dump_json(),
            )

    def _format_message_history(self) -> str:
        return "\n".join(
            f"{speaker} {action} {message} (urgency: {urgency:.1f})"
            for speaker, action, message, urgency in self.message_history
        )

    def get_action_template(self) -> str:
        action_list = ", ".join(f'"{a}"' for a in ActionType)
        return f"""You are {{agent_name}} in a conversation. Your goal is: {{goal}}

Current conversation state:
{{message_history}}

Your current state is: {self.state.value}

Please decide your next action. Consider:
1. The urgency of your response (0-1)
2. Whether others are speaking (if so, consider listening)
3. The natural flow of conversation
4. Your progress towards your goal

Your response must be JSON with:
- action_type: one of [{action_list}]
- argument: your message or action
- urgency: float between 0-1 indicating how urgent this action is

Remember to:
- Use "thought" sparingly (max 2 times)
- Keep responses natural and contextual
- Consider timing and interruptions
- Stay focused on your goal

Respond with ONLY valid JSON."""

    async def process_message_queue(self):
        print(f"\n[{self.name}] Message queue processor started\n")
        while True:
            try:
                print(f"\n[{self.name}] Waiting for messages in queue (processed so far: {self.messages_processed})...")
                message = await asyncio.wait_for(self.message_queue.get(), timeout=30.0)
                
                print(f"\n{'='*50}")
                print(f"[{self.name}] AACT called with message type: {type(message).__name__}")
                print(f"[{self.name}] Current state: {self.state}")
                print(f"[{self.name}] Message history length: {len(self.message_history)}")
                
                if isinstance(message, Text):
                    print(f"[{self.name}] Processing Text: {message.text[:100]}...")
                    self.message_history.append(f"{self.name} observation {message.text}")
                    print(f"[{self.name}] Added observation to history")
                    
                    if len(self.message_history) == 1:
                        print(f"[{self.name}] Forcing initial response after scene setup")
                        template = self.get_action_template()
                        input_values = {
                            "agent_name": self.name,
                            "goal": self.goal,
                            "message_history": self._format_message_history()
                        }
                        await self.generate_response(template, input_values)
                    
                elif isinstance(message, AgentAction):
                    if message.agent_name != self.name:
                        print(f"[{self.name}] Processing message from {message.agent_name}")
                        self.message_history.append(f"{message.agent_name} {message.to_natural_language()}")
                        
                        if self.state in [AgentState.IDLE, AgentState.THINKING]:
                            template = self.get_action_template()
                            input_values = {
                                "agent_name": self.name,
                                "goal": self.goal,
                                "message_history": self._format_message_history()
                            }
                            await self.generate_response(template, input_values)
                        
                elif isinstance(message, Tick):
                    time_since_last = time.time() - self.last_message_time
                    if time_since_last > self.silence_threshold:
                        print(f"[{self.name}] No messages for {time_since_last:.1f}s, forcing response")
                        template = self.get_action_template()
                        input_values = {
                            "agent_name": self.name,
                            "goal": self.goal,
                            "message_history": self._format_message_history()
                        }
                        await self.generate_response(template, input_values)
                    else:
                        print(f"[{self.name}] Skipping response generation (only {time_since_last:.1f}s since last action)")
                
                self.messages_processed += 1
                self.consecutive_errors = 0
                
            except asyncio.TimeoutError:
                print(f"[{self.name}] No messages received for 30s")
                continue
                
            except Exception as e:
                print(f"[{self.name}] Queue processing error: {str(e)}")
                self.consecutive_errors += 1
                if self.consecutive_errors >= 3:
                    print(f"[{self.name}] Too many consecutive errors, resetting state")
                    self.state = AgentState.IDLE
                    self.consecutive_errors = 0
                continue

    async def generate_response(self, template: str, input_values: dict) -> None:
        print(f"[{self.name}] Starting response generation")
        print(f"[{self.name}] Previous state: {self.state}")
        self.state = AgentState.THINKING
        print(f"[{self.name}] New state: {self.state}")
        print(f"[{self.name}] Generated template with {len(self.message_history)} messages in history")
        print(f"[{self.name}] Message history: {self.message_history}")
        print(f"[{self.name}] Starting chunked generation with model: {self.model_name}")
        
        try:
            async for chunk in agenerate_chunked(
                model_name=self.model_name,
                template=template,
                input_values=input_values,
                output_parser=self.output_parser,
                chunk_size=50,
                temperature=0.7,
                fixed_model_version=None
            ):
                print(f"[{self.name}] Received chunk: {chunk}")
                self.accumulated_json += chunk
                try:
                    action_data = json.loads(self.accumulated_json)
                    if all(k in action_data for k in ["agent_name", "action_type", "argument"]):
                        action = AgentAction(
                            agent_name=action_data["agent_name"],
                            action_type=ActionType[action_data["action_type"].upper()],
                            argument=action_data["argument"],
                            path=action_data.get("path", ""),
                            urgency=action_data.get("urgency", 0.5)
                        )
                        await self.send(action)
                        self.accumulated_json = ""  # Reset after successful parse
                        self.state = AgentState.IDLE
                        self.last_message_time = time.time()
                        print(f"[{self.name}] Successfully sent action and reset state")
                        return
                except json.JSONDecodeError:
                    continue  # Keep accumulating chunks
                except Exception as e:
                    print(f"[{self.name}] Error processing chunk: {str(e)}")
                    continue
        except Exception as e:
            print(f"[{self.name}] Error in generate_response: {str(e)}")
            self.state = AgentState.IDLE

    async def aact(self, message: AgentAction | Tick | Text) -> AgentAction:
        print_divider()
        print(f"[{self.name}] AACT called with message type: {type(message).__name__}")
        print(f"[{self.name}] Current state: {self.state}")
        print(f"[{self.name}] Message history length: {len(self.message_history)}")
        
        try:
            match message:
                case DataModelFactory():
                    print(f"[{self.name}] Processing DataModelFactory message")
                    if isinstance(message, Text):  # Check if it's actually a Text message
                        text = message.text
                        print(f"[{self.name}] Processing scene text: {text[:100]}...")
                        self.message_history.append((self.name, "observation", text, 0.3))
                        self.last_message_time = datetime.now()
                        print(f"[{self.name}] Added scene text to history")
                        
                        # Force initial response after receiving scene text
                        print(f"[{self.name}] Forcing initial response after scene setup")
                        asyncio.create_task(self.generate_response())
                    return AgentAction(
                        agent_name=self.name,
                        action_type=ActionType.NONE,
                        argument="",
                        path="",
                        urgency=0.0
                    )
                    
                case Text(text=text):
                    print(f"[{self.name}] Processing Text: {text[:100]}...")
                    try:
                        if "BrowserOutputObservation" in text:
                            text = text.split("BrowserOutputObservation", 1)[1][:100]
                        self.message_history.append((self.name, "observation", text, 0.3))
                        self.last_message_time = datetime.now()
                        print(f"[{self.name}] Added observation to history")
                        
                        # Force initial response after receiving scene text
                        if len(self.message_history) == 1:
                            print(f"[{self.name}] Forcing initial response after scene setup")
                            asyncio.create_task(self.generate_response())
                            
                    except Exception as e:
                        print(f"[{self.name}] Error processing Text message: {str(e)}")
                    return AgentAction(
                        agent_name=self.name,
                        action_type=ActionType.NONE,
                        argument="",
                        path="",
                        urgency=0.0
                    )

                case AgentAction(agent_name=agent_name, action_type=action_type, argument=text, urgency=urgency):
                    print(f"[{self.name}] Processing AgentAction:")
                    print(f"  - From: {agent_name}")
                    print(f"  - Action: {action_type}")
                    print(f"  - Text: {text[:100]}...")
                    print(f"  - Urgency: {urgency}")
                    
                    if agent_name != self.name:
                        try:
                            self.message_history.append((agent_name, str(action_type), text, urgency))
                            self.last_message_time = datetime.now()
                            print(f"[{self.name}] Added message to history")
                            
                            if urgency > self.attention_threshold:
                                old_state = self.state
                                self.state = AgentState.LISTENING
                                print(f"[{self.name}] State change: {old_state} -> {self.state} (high urgency)")
                            
                            print(f"[{self.name}] Triggering response generation")
                            template = self.get_action_template()
                            input_values = {
                                "agent_name": self.name,
                                "goal": self.goal,
                                "message_history": self._format_message_history()
                            }
                            asyncio.create_task(self.generate_response(template, input_values))
                        except Exception as e:
                            print(f"[{self.name}] Error processing AgentAction: {str(e)}")
                    return AgentAction(
                        agent_name=self.name,
                        action_type=ActionType.NONE,
                        argument="",
                        path="",
                        urgency=0.0
                    )

                case Tick():
                    print(f"[{self.name}] Processing Tick")
                    try:
                        time_since_last = (datetime.now() - self.last_action_time).total_seconds()
                        time_since_message = (datetime.now() - self.last_message_time).total_seconds()
                        print(f"[{self.name}] Time since last action: {time_since_last:.2f}s")
                        print(f"[{self.name}] Time since last message: {time_since_message:.2f}s")
                        
                        # Only force action if we have messages in history
                        if len(self.message_history) > 0 and time_since_message >= self.silence_threshold:
                            print(f"[{self.name}] Long silence detected ({time_since_message:.2f}s), forcing action")
                            if self.state != AgentState.SPEAKING and self.state != AgentState.THINKING:
                                print(f"[{self.name}] Initiating forced response generation")
                                template = self.get_action_template()
                                input_values = {
                                    "agent_name": self.name,
                                    "goal": self.goal,
                                    "message_history": self._format_message_history()
                                }
                                asyncio.create_task(self.generate_response(template, input_values))
                        
                        if (
                            len(self.message_history) > 0  # Only generate if we have context
                            and self.state == AgentState.IDLE
                            and time_since_last >= self.min_response_delay
                        ):
                            print(f"[{self.name}] Initiating response generation from IDLE")
                            asyncio.create_task(self.generate_response())
                        else:
                            print(f"[{self.name}] Skipping response generation:")
                            print(f"  - State: {self.state}")
                            print(f"  - Message history length: {len(self.message_history)}")
                            print(f"  - Delay check: {time_since_last:.2f}s < {self.min_response_delay}s")
                    except Exception as e:
                        print(f"[{self.name}] Error processing Tick: {str(e)}")
                    
                    return AgentAction(
                        agent_name=self.name,
                        action_type=ActionType.NONE,
                        argument="",
                        path="",
                        urgency=0.0
                    )
        except Exception as e:
            print(f"[{self.name}] Unhandled error in aact: {str(e)}")

        return AgentAction(
            agent_name=self.name,
            action_type=ActionType.NONE,
            argument="",
            path="",
            urgency=0.0
        ) 