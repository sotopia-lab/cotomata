import tempfile
import os

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
    
    

# Naive validation check    
def validate_agent_code(code: str, agent_name: str, other_agent_name: str) -> bool:
    """
    Validate that the agent's code only implements their own part.
    
    Args:
        code: The code to validate
        agent_name: The name of the current agent
        other_agent_name: The name of the other agent
        
    Returns:
        bool: True if code is valid (only implements own part), False otherwise
    """
    # Check if code contains the other agent's name or implementation
    if other_agent_name in code:
        print(f"Warning: {agent_name} tried to implement {other_agent_name}'s part!")
        return False
    return True
