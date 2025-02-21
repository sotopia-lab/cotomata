from typing import List, Tuple, Optional, Dict, Any
from .agent import CodeWeaverAgent
from .models import AgentAction
from .utils import extract_message_content

async def run_planning_phase(agent1: CodeWeaverAgent, agent2: CodeWeaverAgent, turns: int = 2) -> Optional[str]:
    """Execute the planning phase of the conversation between two agents"""
    print("\n=== Planning Phase ===")
    current_message = "Let's discuss how we can structure our code to output both our messages when merged. What's your approach?"
    # print(f"\nInitial Question: {current_message}\n")

    for i in range(turns):
        # print(f"\n--- Planning Turn {i + 1} ---")
        response1 = await agent1.respond(current_message)
        if not response1:
            # print("[Failed to generate response]")
            break

        # Convert response to string format for conversation flow
        current_message = extract_message_content(response1)
        if "leaves" in current_message:  # Check if agent1 leaves
            break

        response2 = await agent2.respond(current_message)
        if not response2:
            # print("[Failed to generate response]")
            break

        # Convert response to string format for conversation flow
        current_message = extract_message_content(response2)
        if "leaves" in current_message:  # Check if agent2 leaves
            break

    return current_message

async def run_coding_phase(agent1: CodeWeaverAgent, agent2: CodeWeaverAgent) -> Tuple[List[Any], List[Any]]:
    """Execute the coding phase of the conversation between two agents in parallel"""
    print("\n=== Coding Phase ===")
    # Create a shared prompt template for both agents
    coding_phase_prompt_template = (
        "You are now in the coding phase. Based on the previous discussion, implement ONLY your part of the code "
        "that outputs 'hello I am {agent_name}'. Do NOT implement the other agent's part - this will cause merge conflicts!\n\n"
        "Your responses should be structured as actions:\n"
        "- Use 'read' action with path when you need to read a file\n"
        "- Use 'write' action with path and content when you want to modify a file\n"
        "- Use 'execute' action with command when you need to run a shell command\n\n"
        "Important:\n"
        "1. Only implement your own feature\n"
        "2. Do not include other agent's code\n"
        "3. Assume the other agent will implement their part separately\n"
        "4. Your code should work when merged with the other agent's code\n\n"
        "Set continue_action to True if you need to perform more actions, or False when you're done."
    )

    # Update agents with coding phase prompts and response format
    agent1.response_format = AgentAction
    agent1.system_prompt = coding_phase_prompt_template.format(agent_name="agent1")

    agent2.response_format = AgentAction
    agent2.system_prompt = coding_phase_prompt_template.format(agent_name="agent2")
    
    current_message = "Now, let's implement our code based on our discussion. Please share your implementation using structured actions."

    # print("\n--- Agent 1's Implementation ---")
    agent1_responses = []
    while True:
        response = await agent1.respond(current_message)
        if not response:
            # print("[Failed to generate response]")
            break
        try:
            # action = AgentAction.model_validate_json(response)
            agent1_responses.append(response)
            if not response.continue_action:
                break
            current_message = "Continue with your next action."
        except Exception as e:
            # print(f"[Invalid action format: {e}]")
            break

    # print("\n--- Agent 2's Implementation ---")
    agent2_responses = []
    current_message = "Now, let's implement our code based on our discussion. Please share your implementation using structured actions."
    while True:
        response = await agent2.respond(current_message)
        if not response:
            # print("[Failed to generate response]")
            break
        try:
            # action = AgentAction.model_validate_json(response)
            agent2_responses.append(response)
            if not response.continue_action:
                break
            current_message = "Continue with your next action."
        except Exception as e:
            # print(f"[Invalid action format: {e}]")
            break

    return agent1_responses, agent2_responses

async def run_review_phase(agent1: CodeWeaverAgent, agent2: CodeWeaverAgent) -> Tuple[Optional[str], Optional[str]]:
    """Execute the review phase of the conversation between two agents"""
    # Update agents with code review prompts
    agent1.system_prompt = (
        "You are now in the code review phase. Review both implementations and ensure they will work "
        "together to achieve both goals. Suggest any necessary modifications."
    )

    agent2.system_prompt = (
        "You are now in the code review phase. Review both implementations and ensure they will work "
        "together to achieve both goals. Suggest any necessary modifications."
    )

    # print("\n=== Code Comparison Phase ===")
    review_message = "Let's review our implementations and ensure they will work together. Any suggestions for modifications?"
    
    # print("\n--- Final Review ---")
    agent1_review = await agent1.respond(review_message)
    agent2_review = await agent2.respond(agent1_review)

    return agent1_review, agent2_review