from typing import Literal, Optional
from pydantic import BaseModel

class AgentMessage(BaseModel):
    action: Literal['speak', 'leave']
    content: Optional[str] = None

class AgentAction(BaseModel):
    action: Literal['read', 'write', 'execute']
    command: str | None = None
    path: str | None = None
    content: str | None = None
    continue_action: bool | None = None  # Indicates if the agent needs to continue with more actions