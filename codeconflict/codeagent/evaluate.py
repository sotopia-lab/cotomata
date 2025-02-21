from typing import List, Tuple, Dict, Any
import sys
import os
from multiprocessing import Pool
from statistics import mean, stdev
from datetime import datetime
from tqdm import tqdm
import random
from functools import partial

# Import simulate_conversation directly from the module
from simulate import simulate_conversation

def run_simulation_batch(args: Tuple[int, int]) -> Tuple[bool, int, float]:
    """Run a single simulation with fixed turns and specified max_attempts
    
    Args:
        args: Tuple of (seed, max_attempts)
    
    Returns:
        Tuple of (success, turns_taken, reward_score)
    """
    seed, max_attempts = args
    try:
        # Set a unique random seed for each simulation
        random.seed(seed)
        result = simulate_conversation(turns=2, max_attempts=max_attempts)
        return result['success'], result['turns_taken'], result.get('reward_score', 0.0)
    except Exception as e:
        print(f"Error in simulation: {str(e)}")
        return False, 0, 0.0

def run_parallel_simulations(num_runs: int, max_attempts: int, num_workers: int) -> List[Tuple[bool, int, float]]:
    """Run multiple simulations in parallel
    
    Args:
        num_runs: Number of simulations to run
        max_attempts: Maximum attempts for each simulation
        num_workers: Number of parallel workers
        
    Returns:
        List of simulation results
    """
    with Pool(processes=num_workers) as pool:
        # Generate unique seeds for each run
        seeds = [random.randint(0, 1000000) for _ in range(num_runs)]
        args = list(zip(seeds, [max_attempts] * num_runs))
        
        # Run simulations in parallel
        results = list(tqdm(
            pool.imap(run_simulation_batch, args),
            total=num_runs,
            desc=f"Runs (max_attempts={max_attempts})",
            position=1,
            leave=False
        ))
    return results

def evaluate_simulations() -> Dict[str, Any]:
    """Run simulations with fixed turns=2 and evaluate performance at different max_attempts.
    Each configuration is run multiple times to calculate mean and standard deviation.
    
    Returns:
        dict: Contains success statistics for each max_attempts configuration
    """
    results = {}
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    num_runs = 10  # Increased number of runs for better statistical significance
    max_turns = 2  # Fixed number of turns
    num_workers = 10  # Use all available CPU cores
    
    # Set a master seed for reproducibility
    random.seed(42)
    
    try:
        # Main progress bar for different max_attempts configurations
        with tqdm(total=3, desc="Evaluating configurations", position=0) as pbar:
            for max_attempts in [1, 2, 3]:
                print(f"\n=== Evaluating with max_attempts={max_attempts} ===\n")
                
                # Run simulations in parallel
                simulation_results = run_parallel_simulations(num_runs, max_attempts, num_workers)
                
                # Process results
                successes = []
                turns = []
                rewards = []
                
                for success, turns_taken, reward_score in simulation_results:
                    successes.append(1 if success else 0)
                    if success:
                        turns.append(turns_taken)
                        rewards.append(reward_score)
                
                # Calculate statistics
                success_rate = mean(successes) if successes else 0
                success_std = stdev(successes) if len(successes) > 1 else 0
                mean_turns = mean(turns) if turns else 0
                turns_std = stdev(turns) if len(turns) > 1 else 0
                mean_reward = mean(rewards) if rewards else 0
                reward_std = stdev(rewards) if len(rewards) > 1 else 0
                
                results[f'max_attempts_{max_attempts}'] = {
                    'success_rate': success_rate,
                    'success_std': success_std,
                    'mean_turns': mean_turns,
                    'turns_std': turns_std,
                    'mean_reward': mean_reward,
                    'reward_std': reward_std,
                    'successes': successes,
                    'turns': turns,
                    'rewards': rewards
                }
                
                # Print results with more detail
                print(f"\n=== Results for max_attempts={max_attempts} ===")
                print(f"Success Rate: {success_rate * 100:.1f}% ± {success_std * 100:.1f}%")
                print(f"Number of successful runs: {sum(successes)} out of {len(successes)}")
                if turns:
                    print(f"Average Turns to Success: {mean_turns:.1f} ± {turns_std:.1f}")
                    print(f"Average Reward Score: {mean_reward:.1f} ± {reward_std:.1f}")
                    print(f"Success distribution: {turns}")
                else:
                    print("No successful runs recorded")
                print()
                
                pbar.update(1)
        
        # Add metadata to results
        results['metadata'] = {
            'timestamp': timestamp,
            'num_runs': num_runs,
            'max_turns': max_turns,
            'num_workers': num_workers
        }
        
        return results
    
    except Exception as e:
        print(f"Error during evaluation: {str(e)}")
        return {'error': str(e), 'metadata': {'timestamp': timestamp}}

def main():
    evaluate_simulations()

if __name__ == '__main__':
    main()