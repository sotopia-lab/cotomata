import os
import sys
from difflib import SequenceMatcher
import tempfile

# Add project root to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from codeconflict.codeagent.agent import CodeWeaverAgent
from codeconflict.codeagent.phases import run_planning_phase, run_coding_phase, run_review_phase

def validate_code_execution(agent1_code: str, agent2_code: str) -> bool:
    """Execute the combined code and validate both agents' outputs are present.
    
    Args:
        agent1_code: Code from the first agent
        agent2_code: Code from the second agent
        
    Returns:
        bool: True if both outputs are present, False otherwise
    """
    try:
        # It'll be the same code since no merge conflict (simple case right now)
        combined_code = agent1_code
        
        # Create a temporary file with a unique name
        with tempfile.NamedTemporaryFile(prefix='agent_', suffix='.py', delete=False) as temp_file:
            temp_filename = temp_file.name
            temp_file.write(combined_code.encode())
        
        try:
            # Capture the output
            import subprocess
            result = subprocess.run(['python3', temp_filename], capture_output=True, text=True)
            output = result.stdout
            
            # Check if both outputs are present
            return 'hello I am agent1' in output and 'hello I am agent2' in output
        finally:
            # Always clean up the temporary file
            try:
                os.unlink(temp_filename)
            except OSError:
                pass  # Handle case where file was already deleted
                
    except Exception as e:
        print(f'Error executing code: {e}')
        return False
    
def simulate_conversation(turns: int = 2, max_attempts: int = 3) -> dict:
    """Simulate a conversation between two software engineer agents
    
    Returns:
        dict: Contains success status, number of turns taken, and reward score
    """
    attempt = 1
    conflict_info = None
    reward_score = 0  # Initialize reward score

    while attempt <= max_attempts:
        # Initialize two software engineer agents with planning phase prompts
        base_prompt = "Goal: Write code in main.py to output 'hello I am {agent}' in a way that works with {other}'s code.\n" \
                    "Workspace: You are working in a shared codebase with a single file main.py where both agents " \
                    "need to implement their outputs in a compatible way."
        
        if conflict_info:
            # Add agent-specific conflict info to their respective prompts
            if "SWE1" == agent1.name:  # Using agent1's name property
                base_prompt += f"\n\nPrevious attempt resulted in merge conflicts:\n{agent1_merge_conflict}\n" \
                             f"Please adjust your approach to avoid these conflicts."
            else:
                base_prompt += f"\n\nPrevious attempt resulted in merge conflicts:\n{agent2_merge_conflict}\n" \
                             f"Please adjust your approach to avoid these conflicts."

        agent1 = CodeWeaverAgent(
            "SWE1",
            base_prompt.format(agent="agent1", other="agent2")
        )

        agent2 = CodeWeaverAgent(
            "SWE2",
            base_prompt.format(agent="agent2", other="agent1")
        )

        # Execute each phase of the conversation
        run_planning_phase(agent1, agent2, turns)
        agent1_code, agent2_code = run_coding_phase(agent1, agent2)
        
        agent1_code, agent2_code = agent1_code[-1].content, agent2_code[-1].content

        # Check for merge conflicts
        if agent1_code and agent2_code:
            agent1_merge_conflict = create_intelligent_conflict(agent1_code, agent2_code)
            agent2_merge_conflict = create_intelligent_conflict(agent2_code, agent1_code)
            
            # If there are no conflicts, validate the code execution
            if agent1_merge_conflict == "No conflicts" and agent2_merge_conflict == "No conflicts":
                reward_score += 1  # Add 1 point for no merge conflicts
                if validate_code_execution(agent1_code, agent2_code):
                    reward_score += 2  # Add 2 points for successful code validation
                    break
                else:
                    # Code doesn't produce expected output, continue to next attempt if possible
                    if attempt < max_attempts:
                        attempt += 1
                        continue
                    else:
                        return {'success': False, 'turns_taken': attempt, 'reason': 'Code validation failed', 'reward_score': reward_score}
            
            # If we have conflicts and haven't exceeded max attempts, update conflict info and continue
            if attempt < max_attempts:
                # Store conflicts separately for each agent
                agent1_merge_conflict = create_intelligent_conflict(agent1_code, agent2_code)
                agent2_merge_conflict = create_intelligent_conflict(agent2_code, agent1_code)
                attempt += 1
            else:
                return {'success': False, 'turns_taken': attempt, 'reward_score': reward_score}

    # If we've broken out of the loop successfully
    return {'success': True, 'turns_taken': attempt, 'reward_score': reward_score}

from difflib import SequenceMatcher
import textwrap

def create_intelligent_conflict(string1, string2, branch_name="feature-branch", context_size=0):
    """
    Creates an intelligent Git-style merge conflict by detecting actual differences
    between strings and maintaining surrounding context.
    """
    # Split strings into lines
    lines1 = string1.splitlines()
    lines2 = string2.splitlines()
    
    # Use SequenceMatcher to find differences
    matcher = SequenceMatcher(None, lines1, lines2)
    
    # Check if strings are identical
    if matcher.ratio() == 1.0:
        return "No conflicts"
    
    result = []
    last_end = 0
    has_conflicts = False
    
    for op, i1, i2, j1, j2 in matcher.get_opcodes():
        # If there's a difference (not 'equal')
        if op != 'equal':
            has_conflicts = True
            # Add context before
            context_start = max(0, i1 - context_size)
            if context_start > last_end:
                result.extend(lines1[last_end:context_start])
                if context_start > last_end + 1:
                    result.append('...')
            
            # Add the conflict markers and different content
            result.append('<<<<<<< HEAD')
            result.extend(lines1[i1:i2])
            result.append('=======')
            result.extend(lines2[j1:j2])
            result.append(f'>>>>>>> {branch_name}')
            
            last_end = i2
    
    # If no conflicts were found
    if not has_conflicts:
        return "No conflicts"
    
    # Add any remaining content
    if last_end < len(lines1):
        if len(lines1) - last_end > context_size:
            result.append('...')
        result.extend(lines1[last_end:])
    
    return '\n'.join(result)


if __name__ == '__main__':
    simulate_conversation()