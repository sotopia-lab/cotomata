from pydantic import BaseModel, Field
from typing import Dict, Optional, Literal, List, Union
from enum import Enum
from langchain.output_parsers import PydanticOutputParser
from rich import print

class ActionType(str, Enum):
    SPEAK = "speak"
    THOUGHT = "thought"
    NONE = "none"
    NON_VERBAL = "non-verbal"
    BROWSE = "browse"
    BROWSE_ACTION = "browse_action"
    READ = "read"
    WRITE = "write"
    RUN = "run"
    LEAVE = "leave"

class SpeakArgs(BaseModel):
    content: str = Field(..., description="The message to send to other agents")

class ThoughtArgs(BaseModel):
    content: str = Field(..., description="The thought or plan to record")

class NonVerbalArgs(BaseModel):
    content: str = Field(..., description="The non-verbal action to perform")

class BrowseArgs(BaseModel):
    url: str = Field(..., description="The URL to open")

class BrowseActionArgs(BaseModel):
    command: str = Field(
        ...,
        description="The browser command to execute as a string. Available commands:\n"
        "- goto(url: str) - Navigate to a URL\n"
        "- go_back() - Navigate to previous page\n"
        "- go_forward() - Navigate to next page\n"
        "- noop(wait_ms: float = 1000) - Wait for specified milliseconds\n"
        "- scroll(delta_x: float, delta_y: float) - Scroll horizontally/vertically\n"
        "- fill(bid: str, value: str) - Fill form field\n"
        "- select_option(bid: str, options: str | list[str]) - Select dropdown option(s)\n"
        "- click(bid: str, button: str = 'left', modifiers: list = []) - Click element\n"
        "- dblclick(bid: str, button: str = 'left', modifiers: list = []) - Double click\n"
        "- hover(bid: str) - Hover over element\n"
        "- press(bid: str, key_comb: str) - Press key combination\n"
        "- focus(bid: str) - Focus element\n"
        "- clear(bid: str) - Clear input field\n"
        "- drag_and_drop(from_bid: str, to_bid: str) - Perform drag and drop\n"
        "- upload_file(bid: str, file: str | list[str]) - Upload file(s)"
    )

class ReadArgs(BaseModel):
    path: str = Field(..., description="The path of the file to read")

class WriteArgs(BaseModel):
    path: str = Field(..., description="The path of the file to write")
    content: str = Field(..., description="The content to write to the file")

class RunArgs(BaseModel):
    command: str = Field(..., description="The command to run in the shell")

# For now we'll just handle the basic actions
ActionArgs = Union[
    SpeakArgs,
    ThoughtArgs,
    NonVerbalArgs,
    BrowseArgs,
    BrowseActionArgs,
    ReadArgs,
    WriteArgs,
    RunArgs,
    dict,  # for NONE and LEAVE actions
]

class AgentResponse(BaseModel):
    """Model for the complete agent response including Chain-of-Thought reasoning"""
    # reflection: Reflect oh how the other agent is peforming
    # prediction on next step based on inetrviewer's performance 
    # if the other agent is not performing well, try to figure out why
    # state mangement for each agent -> 

    thinking: str = Field(
        ..., 
        description="Chain-of-Thought reasoning explaining the agent's decision process"
    )
    action: ActionType = Field(
        ...,
        description="The type of action to perform"
    )
    args: ActionArgs = Field(
        ...,
        description="Arguments specific to the chosen action type"
    )

    class Config:
        use_enum_values = True

    def __str__(self) -> str:
        # Format the thinking part
        formatted_thinking = self.thinking.replace('{"thinking":', '').replace('"}', '').strip('"')
        formatted_thinking = formatted_thinking.replace('\n', ' ').strip()
        
        lines = [formatted_thinking]  # Always start with thinking
        
        # Format different action types
        match self.action:
            case ActionType.SPEAK:
                content = self.args.content  # type: ignore
                if isinstance(content, str):
                    content = content.replace('{"content":', '').replace('"}', '').strip('"')
                    content = content.replace('\n', ' ').strip()
                    lines.append("→ says: " + content)
            
            case ActionType.THOUGHT:
                content = self.args.content  # type: ignore
                if isinstance(content, str):
                    content = content.replace('{"content":', '').replace('"}', '').strip('"')
                    content = content.replace('\n', ' ').strip()
                    lines.append("→ thinks: " + content)
            
            case ActionType.NON_VERBAL:
                content = self.args.content  # type: ignore
                if isinstance(content, str):
                    lines.append("→ " + content)
            
            case ActionType.BROWSE:
                url = self.args.url  # type: ignore
                if isinstance(url, str):
                    lines.append("→ browses: " + url)
            
            case ActionType.BROWSE_ACTION:
                command = self.args.command  # type: ignore
                if isinstance(command, str):
                    lines.append("→ browser action: " + command)
            
            case ActionType.READ:
                path = self.args.path  # type: ignore
                if isinstance(path, str):
                    lines.append("→ reads: " + path)
            
            case ActionType.WRITE:
                path = self.args.path  # type: ignore
                content = self.args.content  # type: ignore
                if isinstance(path, str) and isinstance(content, str):
                    lines.append(f"→ writes to {path}: {content[:50]}...")
            
            case ActionType.RUN:
                command = self.args.command  # type: ignore
                if isinstance(command, str):
                    lines.append("→ runs: " + command)
            
            case ActionType.NONE:
                lines.append("→ waits")
            
            case ActionType.LEAVE:
                lines.append("→ leaves the conversation")
        
        return '\n'.join(lines)

class AgentResponseOutputParser(PydanticOutputParser):
    def __init__(self):
        super().__init__(pydantic_object=AgentResponse)

    def parse(self, text: str) -> AgentResponse:
        try:
            # Clean up the text before parsing
            text = text.replace('\n', ' ')  # Replace newlines with spaces
            text = ' '.join(text.split())   # Normalize whitespace
            text = text.replace('}{', '}, {')  # Fix joined JSON objects
            
            # Remove any markdown code block markers
            text = text.replace('```json', '').replace('```', '')
            
            # Try to find the JSON object
            start = text.find('{')
            end = text.rfind('}')
            if start != -1 and end != -1:
                text = text[start:end + 1]
            
            return super().parse(text)
        except Exception as e:
            print(f"Parse error: {str(e)}")
            raise 