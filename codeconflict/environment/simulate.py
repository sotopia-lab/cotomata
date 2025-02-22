import os
import sys
import asyncio
from typing import Dict, Tuple

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from codeconflict.environment.docker_env import DockerEnv
from codeconflict.codeagent.agent import CodeWeaverAgent
from codeconflict.environment.phases import run_planning_phase, run_coding_phase
from codeconflict.evaluation.reward import RewardSystem

async def run_merge_phase(docker_env: DockerEnv) -> Tuple[Dict, Dict]:
    """Execute merge operations and return conflict information"""
    await docker_env.commit_changes("Agent 1 changes", working_dir="/workspace/agent1workspace")
    await docker_env.commit_changes("Agent 2 changes", working_dir="/workspace/agent2workspace")
    
    agent1_conflicts = await docker_env.merge_branch("b2", working_dir="/workspace/agent1workspace")
    agent2_conflicts = await docker_env.merge_branch("b1", working_dir="/workspace/agent2workspace")
    
    print("Agent 1 merge results:", agent1_conflicts)
    print("Agent 2 merge results:", agent2_conflicts)
    
    if "Automatic merge went well" in str(agent1_conflicts):
        return agent1_conflicts, agent2_conflicts
    
    agent1_conflicts = await docker_env.code_diff(working_dir="/workspace/agent1workspace")
    agent2_conflicts = await docker_env.code_diff(working_dir="/workspace/agent2workspace")
    
    print("Agent 1 conflicts:", agent1_conflicts)
    print("Agent 2 conflicts:", agent2_conflicts)
    
    return agent1_conflicts, agent2_conflicts

async def simulate_conversation(turns: int = 2, max_attempts: int = 1) -> dict:
    """Simulate a conversation between two software engineer agents"""
    attempt = 0
    conflict_info = None
    docker_env = DockerEnv()
    reward_system = RewardSystem(docker_env)

    while attempt <= max_attempts:
        attempt += 1
        base_prompt = (
            "Goal: Write code in main.py to output 'hello I am {agent_name}' in a way that works with {other_name}'s code.\n\n"
            "Critical Requirements:\n"
            "1. You MUST write your code ONLY in main.py - this is the ONLY file that will be tested\n"
            "2. The code will be tested by running 'python3 main.py'\n"
            "3. You need to coordinate with {other_name} to avoid merge conflicts\n\n"
            "Suggested Strategies:\n"
            "1. Agree on specific line numbers for each agent's code\n"
            "2. Leave placeholder comments/lines for the other agent\n"
            "3. Use clear code structure that allows both outputs to work together\n"
            "4. Consider using functions or classes to organize the code\n\n"
            "Remember: Your goal is to implement your part in a way that will merge smoothly with {other_name}'s code."
        )
        
        agent1_prompt = base_prompt + (f"\n\nPrevious merge conflicts:\n{conflict_info['agent1']}" if conflict_info else "")
        agent2_prompt = base_prompt + (f"\n\nPrevious merge conflicts:\n{conflict_info['agent2']}" if conflict_info else "")

        agent1 = CodeWeaverAgent("SWE1", agent1_prompt.format(agent_name="agent1", other_name="agent2"))
        agent2 = CodeWeaverAgent("SWE2", agent2_prompt.format(agent_name="agent2", other_name="agent1"))

        await run_planning_phase(agent1, agent2, turns)
        await run_coding_phase(agent1, agent2)
        
        # Evaluate individual agent outputs before merge
        await reward_system.evaluate_agent_outputs()

        try:
            agent1_conflicts, agent2_conflicts = await run_merge_phase(docker_env)
            # print(f"Agent 1 conflicts: {agent1_conflicts}")
            # print(f"Agent 2 conflicts: {agent2_conflicts}")
            
            if "Automatic merge went well" in str(agent1_conflicts):
                reward_system.record_merge_success(success=True)
                
                # since no merge conflicts pull into main
                x = await docker_env.merge_main(branch_name="b1", working_dir="/workspace/agent1workspace")
                print("Merging branch b1 into main...", x)
                x = await docker_env.merge_main(branch_name="b2", working_dir="/workspace/agent2workspace")
                print("Merging branch b2 into main...", x)  
                x = await docker_env.pull_base()
                print("Pulling base...", x)
                break
            else:
                conflict_info = {
                    "agent1": agent1_conflicts['stdout'],
                    "agent2": agent2_conflicts['stdout']
                }
                reward_system.record_merge_success(success=False, agent1_conflicts=agent1_conflicts, agent2_conflicts=agent2_conflicts)
                await docker_env.merge_abort(working_dir="/workspace/agent1workspace")
                await docker_env.merge_abort(working_dir="/workspace/agent2workspace")
                
                
        except Exception:
            pass
        print(f"Attempt {attempt} failed. Retrying...")
        print(reward_system.get_rewards())

        
    # Validate combined output and award additional rewards
    await reward_system.validate_combined_output()

    await docker_env.close()
    rewards = reward_system.get_rewards()
    total_reward_score = (rewards['agent1']['total'] + rewards['agent2']['total']) / 2
    output = {
        'success': total_reward_score > 0,
        'turns_taken': attempt,
        'reward_score': total_reward_score,
        'rewards': rewards
    }
    print(output)
    return output

if __name__ == '__main__':
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(simulate_conversation())
    finally:
        loop.close()