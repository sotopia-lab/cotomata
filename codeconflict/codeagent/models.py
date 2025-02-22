from typing import Literal, Optional
from pydantic import BaseModel, Field

class AgentMessage(BaseModel):
    action: Literal['speak', 'leave'] = Field(
        description="The type of message action: 'speak' for communication, 'leave' for exiting conversation"
    )
    content: Optional[str] = Field(
        default=None,
        description="The message content when speaking, not required when leaving"
    )

class AgentAction(BaseModel):
    action: Literal['read', 'write', 'execute'] = Field(
        description="The type of action to perform: 'read' for file reading, 'write' for file modification, 'execute' for running commands"
    )
    command: str | None = Field(
        default=None,
        description="The shell command to execute when action is 'execute'"
    )
    path: str | None = Field(
        default=None,
        description="The file path to read from or write to when action is 'read' or 'write' This MUST be a valid exisitng path in the workspace"
    )
    content: str | None = Field(
        default=None,
        description="The content to write when action is 'write'"
    )
    start_line: int | None = Field(
        default=None,
        description="The starting line number (0-based) for line-specific write operations. If not provided with end_line, the entire file will be overwritten"
    )
    end_line: int | None = Field(
        default=None,
        description="The ending line number (0-based) for line-specific write operations. Must be provided if start_line is set"
    )
    continue_action: bool | None = Field(
        default=None,
        description="Indicates if the agent needs to continue with more actions (True) or is done (False)"
    )