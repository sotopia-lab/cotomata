import os
import sys
import asyncio
from typing import Dict, Tuple

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from codeconflict.environment.docker_env import DockerEnv
from codeconflict.codeagent.agent import CodeWeaverAgent
from codeconflict.environment.phases import run_planning_phase, run_coding_phase

async def run_merge_phase(docker_env: DockerEnv) -> Tuple[Dict, Dict]:
    """Execute merge operations and return conflict information"""
    await docker_env.commit_changes("Agent 1 changes", working_dir="/workspace/agent1workspace")
    await docker_env.commit_changes("Agent 2 changes", working_dir="/workspace/agent2workspace")
    
    await docker_env.merge_branch("b2", working_dir="/workspace/agent1workspace")
    await docker_env.merge_branch("b1", working_dir="/workspace/agent2workspace")
    
    agent1_conflicts = await docker_env.code_diff(working_dir="/workspace/agent1workspace")
    agent2_conflicts = await docker_env.code_diff(working_dir="/workspace/agent2workspace")
    
    return agent1_conflicts, agent2_conflicts

async def simulate_conversation(turns: int = 2, max_attempts: int = 3) -> dict:
    """Simulate a conversation between two software engineer agents"""
    attempt = 1
    conflict_info = None
    reward_score = 0
    docker_env = DockerEnv()

    while attempt <= max_attempts:
        base_prompt = (
            "Goal: Write code in main.py to output 'hello I am {agent}' in a way that works with {other}'s code.\n"
            "Workspace: You are working in a shared codebase with a single file main.py where both agents "
            "need to implement their outputs in a compatible way."
        )
        
        agent1_prompt = base_prompt + (f"\n\nPrevious merge conflicts:\n{conflict_info['agent1']}" if conflict_info else "")
        agent2_prompt = base_prompt + (f"\n\nPrevious merge conflicts:\n{conflict_info['agent2']}" if conflict_info else "")

        agent1 = CodeWeaverAgent("SWE1", agent1_prompt.format(agent="agent1", other="agent2"))
        agent2 = CodeWeaverAgent("SWE2", agent2_prompt.format(agent="agent2", other="agent1"))

        await run_planning_phase(agent1, agent2, turns)
        await run_coding_phase(agent1, agent2)

        try:
            agent1_conflicts, agent2_conflicts = await run_merge_phase(docker_env)
            
            if "Automatic merge went well" in str(agent1_conflicts):
                reward_score += 1
                break
            else:
                conflict_info = {
                    "agent1": agent1_conflicts['stdout'],
                    "agent2": agent2_conflicts['stdout']
                }
                await docker_env.merge_abort(working_dir="/workspace/agent1workspace")
                await docker_env.merge_abort(working_dir="/workspace/agent2workspace")

        except Exception:
            pass

        attempt += 1

    await docker_env.close()
    return {'success': reward_score > 0, 'turns_taken': attempt, 'reward_score': reward_score}

if __name__ == '__main__':
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(simulate_conversation())
    finally:
        loop.close()