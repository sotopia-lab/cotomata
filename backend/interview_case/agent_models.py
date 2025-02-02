from pydantic import BaseModel, Field
from typing import Dict, Optional, Literal, List, Union
from enum import Enum
from langchain.output_parsers import PydanticOutputParser
from rich import print

class ActionType(str, Enum):
    SPEAK = "speak"
    NONE = "none"
    LEAVE = "leave"

class SpeakArgs(BaseModel):
    content: str = Field(..., description="The message to send to other agents")

# For now we'll just handle the basic actions
ActionArgs = Union[
    SpeakArgs,
    dict,  # for NONE action
]

class AgentResponse(BaseModel):
    """Model for the complete agent response including Chain-of-Thought reasoning"""
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
        
        # For speak actions, show the message
        if self.action == ActionType.SPEAK:
            # Clean up any JSON formatting in the content
            content = self.args.content  # type: ignore
            if isinstance(content, str):
                content = content.replace('{"content":', '').replace('"}', '').strip('"')
                content = content.replace('\n', ' ').strip()
            
            # Format with simple text
            lines = []
            lines.append(formatted_thinking)  # Thinking part
            if content:
                lines.append("→ " + content)  # Speaking part with arrow
            return '\n'.join(lines)
        
        # For other actions, just show the thinking
        return formatted_thinking

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