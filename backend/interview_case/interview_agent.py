import logging
import sys
from enum import Enum
from rich.logging import RichHandler
from pydantic import Field

from typing import Optional

from aact import Message, NodeFactory
from aact.messages import Text, Tick, DataModel
from aact.messages.registry import DataModelFactory

from .base_agent import BaseAgent  # type: ignore[import-untyped]
from .generate import agenerate, agenerate_agent_response # type: ignore[import-untyped]

import json

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


@DataModelFactory.register("agent_action")
class AgentAction(DataModel):
    agent_name: str = Field(description="the name of the agent")
    thinking: Optional[str] = Field(description="The agent's internal thought process and reasoning before taking action")
    action_type: ActionType = Field(
        description="type of action you want to take"
    )
    argument: str = Field(
        description="required argument for the action type"
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


@NodeFactory.register("llm_agent")
class LLMAgent(BaseAgent[AgentAction | Tick | Text, AgentAction]): # type: ignore[misc]
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
        self.message_history: list[tuple[str, str, str]] = []
        self.name = agent_name
        self.model_name = model_name
        self.goal = goal

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

    def _format_message_history(
        self, message_history: list[tuple[str, str, str]]
    ) -> str:
        ## TODO: akhatua Fix the mapping of action to be gramatically correct
        return "\n".join(
            (f"{speaker} {action} {message}")
            for speaker, action, message in message_history
        )

    def get_action_template(self, selected_actions: list[ActionType]) -> str:
        """
        Returns the action template string with selected actions.

        Args:
            selected_actions (list[ActionType]): List of ActionType enum members to include in the template.

        Returns:
            str: The action template with the selected actions.
        """
        base_template = """ You are talking to another agent.
        You are {agent_name}.\n
        {message_history}\nand you plan to {goal}.
        ## Action
        What is your next thought or action? Your response must be in a structured format that includes:
        1. Your internal thought process and reasoning about what action to take
        2. The action type and its details

        Available actions are:
        """

        action_descriptions = {
            str(
                ActionType.SPEAK
            ): """`speak` - you can talk to the other agents to share information or ask them something. Arguments:
                * `content` - the message to send to the other agents (should be short)""",
            str(
                ActionType.THOUGHT
            ): """`thought` - only use this rarely to make a plan, set a goal, record your thoughts. Arguments:
                * `content` - the message you send yourself to organize your thoughts (should be short). You cannot think more than 2 turns.""",
            str(
                ActionType.NONE
            ): """`none` - you can choose not to take an action if you are waiting for some data""",
            str(
                ActionType.NON_VERBAL
            ): """`non-verbal` - you can choose to do a non verbal action
                * `content` - the non veral action you want to send to other agents. eg: smile, shrug, thumbs up""",
            str(ActionType.BROWSE): """`browse` - opens a web page. Arguments:
                * `url` - the URL to open, when you browse the web you must use `none` action until you get some information back. When you get the information back you must summarize the article and explain the article to the other agents.""",
            str(
                ActionType.BROWSE_ACTION
            ): """`browse_action` - actions you can take on a web browser
                * `content` - the content to run. You have 15 available contents. These contents must be a single string value of content
                    Options for `content`:
                        `content` = goto(url: str)
                            Description: Navigate to a url.
                            Examples:
                                goto('http://www.example.com')

                        `content` = go_back()
                            Description: Navigate to the previous page in history.
                            Examples:
                                go_back()

                        `content` = go_forward()
                            Description: Navigate to the next page in history.
                            Examples:
                                go_forward()

                        `content` = noop(wait_ms: float = 1000)
                            Description: Do nothing, and optionally wait for the given time (in milliseconds).
                            You can use this to get the current page content and/or wait for the page to load.
                            Examples:
                                noop()
                                noop(500)

                        `content` = scroll(delta_x: float, delta_y: float)
                            Description: Scroll horizontally and vertically. Amounts in pixels, positive for right or down scrolling, negative for left or up scrolling. Dispatches a wheel event.
                            Examples:
                                scroll(0, 200)
                                scroll(-50.2, -100.5)

                        `content` = fill(bid, value)
                            Description: Fill out a form field. It focuses the element and triggers an input event with the entered text. It works for <input>, <textarea> and [contenteditable] elements.
                            Examples:
                                fill('237', 'example value')
                                fill('45', 'multi-line\nexample')
                                fill('a12', 'example with "quotes"')

                        `content` = select_option(bid: str, options: str | list[str])
                            Description: Select one or multiple options in a <select> element. You can specify option value or label to select. Multiple options can be selected.
                            Examples:
                                select_option('a48', 'blue')
                                select_option('c48', ['red', 'green', 'blue'])

                        `content`= click(bid: str, button: Literal['left', 'middle', 'right'] = 'left', modifiers: list[typing.Literal['Alt', 'Control', 'ControlOrMeta', 'Meta', 'Shift']] = [])
                            Description: Click an element.
                            Examples:
                                click('a51')
                                click('b22', button='right')
                                click('48', button='middle', modifiers=['Shift'])

                        `content` = dblclick(bid: str, button: Literal['left', 'middle', 'right'] = 'left', modifiers: list[typing.Literal['Alt', 'Control', 'ControlOrMeta', 'Meta', 'Shift']] = [])
                            Description: Double click an element.
                            Examples:
                                dblclick('12')
                                dblclick('ca42', button='right')
                                dblclick('178', button='middle', modifiers=['Shift'])

                        `content` = hover(bid: str)
                            Description: Hover over an element.
                            Examples:
                                hover('b8')

                        `content` = press(bid: str, key_comb: str)
                            Description: Focus the matching element and press a combination of keys. It accepts the logical key names that are emitted in the keyboardEvent.key property of the keyboard events: Backquote, Minus, Equal, Backslash, Backspace, Tab, Delete, Escape, ArrowDown, End, Enter, Home, Insert, PageDown, PageUp, ArrowRight, ArrowUp, F1 - F12, Digit0 - Digit9, KeyA - KeyZ, etc. You can alternatively specify a single character you'd like to produce such as "a" or "#". Following modification shortcuts are also supported: Shift, Control, Alt, Meta, ShiftLeft, ControlOrMeta. ControlOrMeta resolves to Control on Windows and Linux and to Meta on macOS.
                            Examples:
                                press('88', 'Backspace')
                                press('a26', 'ControlOrMeta+a')
                                press('a61', 'Meta+Shift+t')

                        `content` = focus(bid: str)
                            Description: Focus the matching element.
                            Examples:
                                focus('b455')

                        `content` = clear(bid: str)
                            Description: Clear the input field.
                            Examples:
                                clear('996')

                        `content` = drag_and_drop(from_bid: str, to_bid: str)
                            Description: Perform a drag & drop. Hover the element that will be dragged. Press left mouse button. Move mouse to the element that will receive the drop. Release left mouse button.
                            Examples:
                                drag_and_drop('56', '498')

                        `content`=  upload_file(bid: str, file: str | list[str])
                            Description: Click an element and wait for a "filechooser" event, then select one or multiple input files for upload. Relative file paths are resolved relative to the current working directory. An empty list clears the selected files.
                            Examples:
                                upload_file('572', '/home/user/my_receipt.pdf')
                                upload_file('63', ['/home/bob/Documents/image.jpg', '/home/bob/Documents/file.zip'])""",
            str(ActionType.READ): """`read` - reads the content of a file. Arguments:
                * `path` - the path of the file to read""",
            str(ActionType.WRITE): """`write` - writes the content to a file. Arguments:
                * `path` - the path of the file to write
                * `content` - the content to write to the file""",
            str(
                ActionType.RUN
            ): """`run` - runs a content on the content line in a Linux shell. Arguments:
                * `content` - the command to run""",
            str(
                ActionType.LEAVE
            ): """`leave` - if your goals have been completed or abandoned, and you're absolutely certain that you've completed your task and have tested your work, use the leave action to stop working.""",
        }

        selected_action_descriptions = "\n\n".join(
            f"[{i+1}] {action_descriptions[str(action)]}"
            for i, action in enumerate(selected_actions)
            if str(action) in action_descriptions
        )

        return (
            base_template
            + selected_action_descriptions
            + """
                You must prioritize actions that move you closer to your goal. Communicate briefly when necessary and focus on executing tasks effectively. Always consider the next actionable step to avoid unnecessary delays.
                Again, you must reply with JSON, and only with JSON.
            """
        )

    async def aact(self, message: AgentAction | Tick | Text) -> AgentAction:
        match message:
            case Text(text=text):
                if "BrowserOutputObservation" in text:
                    self.message_history.append(
                        (
                            self.name,
                            "observation data",
                            "BrowserOutputObservation received.",
                        )
                    )
                    text = text.split("BrowserOutputObservation", 1)[1][:100]
                self.message_history.append((self.name, "observation data", text))
                return AgentAction(
                    agent_name=self.name, action_type="none", argument="", path="", thinking=""
                )
            case Tick():
                self.count_ticks += 1
                if self.count_ticks % self.query_interval == 0:
                    try:
                        template = self.get_action_template(
                            [action for action in ActionType]
                        )
                        
                        agent_action = await agenerate_agent_response(
                            template=template,
                            model_name=self.model_name,
                            agent_name=self.name,
                            history=self._format_message_history(self.message_history),
                            goal=self.goal,
                            temperature=0.7,
                        )
                        
                    except Exception as e:
                        print(f"Error during agenerate: {e}")
                    

                    # Convert structured output to the expected format
                    agent_action = json.dumps({
                        "thinking": str(agent_action.thinking).strip(),
                        "action": str(agent_action.action).strip(),
                        "args": {
                            "content": (agent_action.args.content or "").strip(),
                            "path": (agent_action.args.path or "").strip(),
                            "url": (agent_action.args.url or "").strip()
                        }
                    })     
                                    
                    try:
                        data = json.loads(agent_action)
                        action = data["action"]
                        if action == "thought":
                            content = data["args"]["content"]
                            self.message_history.append((self.name, action, content))
                            return AgentAction(
                                thinking=data["thinking"],
                                agent_name=self.name,
                                action_type="thought",
                                argument=content,
                                path="",
                            )

                        elif action == "speak":
                            content = data["args"]["content"]
                            self.message_history.append((self.name, action, content))
                            return AgentAction(
                                thinking=data["thinking"],
                                agent_name=self.name,
                                action_type=action,
                                argument=content,
                                path="",
                            )

                        elif action == "non-verbal":
                            content = data["args"]["content"]
                            self.message_history.append((self.name, action, content))
                            return AgentAction(
                                thinking=data["thinking"],
                                agent_name=self.name,
                                action_type=action,
                                argument=content,
                                path="",
                            )

                        elif action == "browse":
                            url = data["args"]["url"]
                            self.message_history.append((self.name, action, url))
                            return AgentAction(
                                thinking=data["thinking"],
                                agent_name=self.name,
                                action_type=action,
                                argument=url,
                                path="",
                            )

                        elif action == "browse_action":
                            content = data["args"]["content"]
                            self.message_history.append((self.name, action, content))
                            return AgentAction(
                                thinking=data["thinking"],
                                agent_name=self.name,
                                action_type=action,
                                argument=content,
                                path="",
                            )

                        elif action == "run":
                            content = data["args"]["content"]
                            self.message_history.append((self.name, action, content))
                            return AgentAction(
                                thinking=data["thinking"],
                                agent_name=self.name,
                                action_type=action,
                                argument=content,
                                path="",
                            )

                        elif action == "write":
                            path = data["args"]["path"]
                            content = data["args"]["content"]
                            self.message_history.append((self.name, action, content))
                            return AgentAction(
                                thinking=data["thinking"],
                                agent_name=self.name,
                                action_type=action,
                                argument=content,
                                path=path,
                            )

                        elif action == "read":
                            path = data["args"]["path"]
                            self.message_history.append((self.name, action, path))
                            return AgentAction(
                                thinking=data["thinking"],
                                agent_name=self.name,
                                action_type=action,
                                argument="Nan",
                                path=path,
                            )

                        elif action == "none":
                            return AgentAction(
                                thinking=data["thinking"],
                                agent_name=self.name,
                                action_type="none",
                                argument="",
                                path="",
                            )
                        elif action == "leave":
                            print("Terminating the program as per the leave action.")
                        else:
                            print(f"Unknown action: {action}")
                    except json.JSONDecodeError as e:
                        print(f"Error decoding JSON: {e}")
                else:
                    return AgentAction(
                        agent_name=self.name, action_type="none", argument="", path="", thinking=""
                    )
            case AgentAction(
                agent_name=agent_name, action_type=action_type, argument=text, thinking=thinking
            ):
                if action_type == "speak":
                    self.message_history.append((agent_name, str(action_type), text))
                return AgentAction(
                    agent_name=self.name, action_type="none", argument="", path="", thinking=""
                )
        raise ValueError(f"Unexpected message type: {type(message)}")