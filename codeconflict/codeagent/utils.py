from typing import Any
from pydantic import BaseModel
from .models import AgentMessage

def format_agent_response(agent_name: str, response: BaseModel | Any) -> str:
    """Convert agent response models to human-readable string format"""
    if isinstance(response, AgentMessage):
        return f"\n{agent_name} {response.action}s" + (f": {response.content}" if response.content else "")
    
    # Handle AgentAction format
    if hasattr(response, 'action'):
        if response.action == 'read':
            return f"\n{agent_name} reads {response.path}"
        elif response.action == 'write':
            return f"\n{agent_name} writes \n\n {response.content} \n\n  in {response.path}"
        elif response.action == 'execute':
            return f"\n{agent_name} executes command: {response.command}"
    
    return str(response)

def extract_message_content(response: Any) -> str:
    """Extract string content from agent responses for conversation history"""
    if isinstance(response, str):
        return response
    elif isinstance(response, BaseModel):
        return format_agent_response('Agent', response)
    return str(response)