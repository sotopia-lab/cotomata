from pydantic import BaseModel, Field, field_validator
from typing import Dict, Optional, Literal, List, Union
from enum import Enum
from langchain.output_parsers import PydanticOutputParser
from rich import print
import os

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
    type: Literal["speak"] = "speak"
    content: str = Field(..., description="The message to send to other agents")

class ThoughtArgs(BaseModel):
    type: Literal["thought"] = "thought"
    content: str = Field(..., description="The thought or plan to record")

class NonVerbalArgs(BaseModel):
    type: Literal["non_verbal"] = "non_verbal"
    content: str = Field(..., description="The non-verbal action to perform")

class BrowseArgs(BaseModel):
    type: Literal["browse"] = "browse"
    url: str = Field(..., description="The URL to open")

class BrowseActionArgs(BaseModel):
    type: Literal["browse_action"] = "browse_action"
    command: str = Field(
        ...,
        description=(
            "The browser command to execute as a string. Available commands:\n"
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
    )

class ReadArgs(BaseModel):
    type: Literal["read"] = "read"
    path: str = Field(..., description="The path of the file to read")

class WriteArgs(BaseModel):
    type: Literal["write"] = "write"
    path: str = Field(..., description="The path of the file to write")
    content: str = Field(..., description="The content to write to the file")

class RunArgs(BaseModel):
    type: Literal["run"] = "run"
    command: str = Field(..., description="The command to run in the shell")


# For actions like NONE and LEAVE, you can define dedicated models or use a simple dict if appropriate.
class NoneArgs(BaseModel):
    type: Literal["none"] = "none"

class LeaveArgs(BaseModel):
    type: Literal["leave"] = "leave"

# Update the union to include the new models
ActionArgs = Union[
    SpeakArgs,
    ThoughtArgs,
    NonVerbalArgs,
    BrowseArgs,
    BrowseActionArgs,
    ReadArgs,
    WriteArgs,
    RunArgs,
    NoneArgs,   # for NONE action
    LeaveArgs,  # for LEAVE action
]

class AgentArgs(BaseModel):
    content: Optional[str] = Field(
        None, 
        description="Content for speak, thought, non-verbal, write actions, shell commands, browse_action and run actions"
    )
    path: Optional[str] = Field(
        None, 
        description="File path for read and write actions"
    )
    url: Optional[str] = Field(
        None, 
        description="URL for browse action"
    )
    
    @field_validator('path')
    def validate_path(cls, v):
        if v is not None:
            # Basic path validation
            if not v or v.isspace():
                raise ValueError("Path cannot be empty")
            
            # Check for invalid characters and patterns
            invalid_chars = '<>:"|?*'
            if any(char in v for char in invalid_chars):
                raise ValueError(f"Path contains invalid characters. Cannot use: {invalid_chars}")
            
            # Check for potentially dangerous patterns
            dangerous_patterns = [
                '..',        # Directory traversal
                '~/',       # Home directory
                '//',       # Double slashes
                '\\',       # Windows backslashes
                '/etc/',    # System directories
                '/root/',
                '/dev/',
                '/proc/'
            ]
            if any(pattern in v for pattern in dangerous_patterns):
                raise ValueError("Path contains invalid or dangerous patterns")
            
            # Enforce reasonable length
            if len(v) > 255:
                raise ValueError("Path is too long (max 255 characters)")
        return v


class AgentResponse(BaseModel):
    """
    Model for the complete agent response including Chain-of-Thought reasoning.
    """
    thinking: str = Field(
        ..., 
        description="Chain-of-Thought reasoning explaining the agent's decision process"
    )
    # Assuming ActionType is defined elsewhere. It should probably be a Literal or Enum.
    action: str = Field(
        ..., 
        description="The type of action to perform"
    )
    args: AgentArgs = Field(
        ..., 
        description="Arguments specific to the chosen action type (optional command, content, path, or url)"
    )

    class Config:
        # Use the discriminator field "type" for the ActionArgs union
        schema_extra = {
            "discriminator": "type"
        }


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