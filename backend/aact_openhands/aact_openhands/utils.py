from enum import Enum
from pydantic import Field

from typing import  Optional

from aact.messages import DataModel
from aact.messages.registry import DataModelFactory

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
        description="the utterance if choose to speak, the expression or gesture if \
            choose non-verbal communication, or the physical action if choose action"
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
