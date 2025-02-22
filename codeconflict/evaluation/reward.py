import tempfile
import os

class RewardSystem:
    def __init__(self, docker_env):
        """Initialize the reward system.
        
        Args:
            docker_env: Docker environment instance
        """
        self.docker_env = docker_env
        self.rewards = {
            'agent1': {
                'output_evaluation': 0.0,
                'merge_success': 0.0,
                'combined_output': 0.0,
                'total': 0.0
            },
            'agent2': {
                'output_evaluation': 0.0,
                'merge_success': 0.0,
                'combined_output': 0.0,
                'total': 0.0
            }
        }
    
    async def evaluate_agent_outputs(self, agent1_workspace: str = "/workspace/agent1workspace", 
                                   agent2_workspace: str = "/workspace/agent2workspace") -> tuple[float, float]:
        """Evaluate each agent's output independently and return their rewards.
        
        Args:
            agent1_workspace: Path to agent1's workspace
            agent2_workspace: Path to agent2's workspace
            
        Returns:
            tuple[float, float]: Rewards for agent1 and agent2 respectively
        """
        try:
            # Execute main.py for agent1
            agent1_result = await self.docker_env.execute_command(f"cd {agent1_workspace} && python3 main.py")
            agent1_output = agent1_result.get('stdout', '')
            
            # Execute main.py for agent2
            agent2_result = await self.docker_env.execute_command(f"cd {agent2_workspace} && python3 main.py")
            agent2_output = agent2_result.get('stdout', '')
            
            # Calculate rewards
            agent1_reward = 0.0
            agent2_reward = 0.0
            
            # Agent 1 evaluation
            if 'hello I am agent1' in agent1_output:
                agent1_reward += 5.0
            if 'hello I am agent2' in agent1_output:
                agent1_reward -= 1.0
                
            # Agent 2 evaluation
            if 'hello I am agent2' in agent2_output:
                agent2_reward += 5.0
            if 'hello I am agent1' in agent2_output:
                agent2_reward -= 1.0
            
            # Store rewards in the dictionary
            self.rewards['agent1']['output_evaluation'] = agent1_reward
            self.rewards['agent2']['output_evaluation'] = agent2_reward
            
            # Update total rewards
            self.rewards['agent1']['total'] += agent1_reward
            self.rewards['agent2']['total'] += agent2_reward
                
            return agent1_reward, agent2_reward
            
        except Exception as e:
            print(f'Error evaluating agent outputs: {e}')
            return 0.0, 0.0

    def record_merge_success(self, success: bool = True, agent1_conflicts: dict = None, agent2_conflicts: dict = None) -> None:
        """Record rewards for merge results.
        
        Args:
            success: Whether the merge was successful
            agent1_conflicts: Conflict information for agent1 if merge failed
            agent2_conflicts: Conflict information for agent2 if merge failed
        """
        if success:
            reward = 2.0
            self.rewards['agent1']['merge_success'] = reward
            self.rewards['agent2']['merge_success'] = reward
            self.rewards['agent1']['total'] += reward
            self.rewards['agent2']['total'] += reward
        elif agent1_conflicts and agent2_conflicts:
            conflict_scores = self.calculate_conflict_scores(agent1_conflicts, agent2_conflicts)
            self.rewards['agent1']['merge_success'] = conflict_scores['agent1_score']
            self.rewards['agent2']['merge_success'] = conflict_scores['agent2_score']
            self.rewards['agent1']['total'] += conflict_scores['agent1_score']
            self.rewards['agent2']['total'] += conflict_scores['agent2_score']
            
    def calculate_conflict_scores(self, agent1_conflicts: dict, agent2_conflicts: dict) -> dict:
        """Calculate conflict responsibility scores for both agents based on their diff outputs.
        Returns negative scores where more negative means more responsibility for conflicts.
        """
        def extract_changes(diff_output):
            # Split the diff into sections
            lines = diff_output['stdout'].split('\n')
            head_changes = []
            remote_changes = []
            current_section = None
            
            for line in lines:
                if line.startswith('<<<<<<< HEAD'):
                    current_section = 'head'
                elif line.startswith('======='):
                    current_section = 'remote'
                elif line.startswith('>>>>>>>'):
                    current_section = None
                elif current_section == 'head' and line.startswith('+'):
                    head_changes.append(line[1:])
                elif current_section == 'remote' and line.startswith('+'):
                    remote_changes.append(line[1:])
                    
            return head_changes, remote_changes

        # Extract changes from both perspectives
        agent1_head, agent1_remote = extract_changes(agent1_conflicts)
        agent2_head, agent2_remote = extract_changes(agent2_conflicts)
        
        def calculate_complexity(changes):
            raw_score = 0
            for change in changes:
                # Base score for each line
                raw_score -= 1
                
                # Additional penalties for structural changes
                if 'def ' in change:
                    raw_score -= 3
                if 'class ' in change:
                    raw_score -= 4
                if 'import ' in change:
                    raw_score -= 2
                    
                # Penalty for line length
                raw_score -= len(change) / 50  # Additional penalty for very long lines
            
            # Scale score between 0 and -2
            if raw_score == 0:
                return 0
            # Find the maximum possible score for normalization
            max_score = max(
                abs(raw_score),  # Current score
                len(changes) * (1 + 4 + len(max(changes, default='')) / 50)  # Max possible score
            )
            return (raw_score / max_score) * -2

        # Calculate final scores
        agent1_score = calculate_complexity(agent1_head)
        agent2_score = calculate_complexity(agent2_head)
        
        return {
            'agent1_score': agent1_score,
            'agent2_score': agent2_score,
            'explanation': {
                'agent1_changes': len(agent1_head),
                'agent2_changes': len(agent2_head)
            }
        }

    async def validate_combined_output(self, base_workspace: str = "/workspace/base") -> tuple[float, float]:
        """Validate the combined output from both agents and award rewards.
        
        Args:
            base_workspace: Path to base workspace with merged code
            
        Returns:
            tuple[float, float]: Additional rewards for agent1 and agent2 respectively
        """
        try:
            # Execute main.py in base workspace
            result = await self.docker_env.execute_command(f"cd {base_workspace} && python3 main.py")
            output = result.get('stdout', '')
            
            # Check if both agent outputs are present
            agent1_present = 'hello I am agent1' in output
            agent2_present = 'hello I am agent2' in output
            
            # Award 5 points to each agent if both outputs are present
            if agent1_present and agent2_present:
                reward = 5.0
                self.rewards['agent1']['combined_output'] = reward
                self.rewards['agent2']['combined_output'] = reward
                self.rewards['agent1']['total'] += reward
                self.rewards['agent2']['total'] += reward
                return reward, reward
                
            return 0.0, 0.0
            
        except Exception as e:
            print(f'Error validating combined output: {e}')
            return 0.0, 0.0

    def get_rewards(self) -> dict:
        """Get the current rewards dictionary.
        
        Returns:
            dict: The current rewards for both agents across all stages
        """
        return self.rewards
