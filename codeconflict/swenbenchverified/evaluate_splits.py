import os
import json
import logging
import argparse
from pathlib import Path
from openai import OpenAI
from tqdm import tqdm
from datasets import load_dataset

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def evaluate_split(task_data, client, patch=None, test_patch=None):
    """
    Evaluate whether a PR split makes sense using an LLM.
    
    Args:
        task_data (dict): The loaded task data
        client: OpenAI client instance
        patch (str, optional): The code patch showing actual changes
        test_patch (str, optional): The test patch showing test changes
        
    Returns:
        dict: The evaluation result from the LLM
    """
    # Extract relevant information
    repo = task_data.get("repo", "Unknown")
    test_id = task_data.get("test_id", "Unknown")
    
    # Construct a prompt for the LLM
    prompt = f"I need you to evaluate whether the following software development task split makes sense:\n\n"
    prompt += f"Repository: {repo}\n"
    prompt += f"Test ID: {test_id}\n\n"
    
    # Add feature details
    if "feature1" in task_data:
        prompt += "Feature 1:\n"
        prompt += f"Description: {task_data['feature1'].get('prompt', 'No description')}\n"
        prompt += f"Entry point: {task_data['feature1'].get('entrypoint', 'Not specified')}\n"
        if "tests" in task_data["feature1"]:
            prompt += f"Tests: {task_data['feature1']['tests']}\n\n"
        else:
            prompt += "\n"
    
    if "feature2" in task_data:
        prompt += "Feature 2:\n"
        prompt += f"Description: {task_data['feature2'].get('prompt', 'No description')}\n"
        prompt += f"Entry point: {task_data['feature2'].get('entrypoint', 'Not specified')}\n"
        if "tests" in task_data["feature2"]:
            prompt += f"Tests: {task_data['feature2']['tests']}\n\n"
        else:
            prompt += "\n"
    
    # Add collaboration points if available
    if "collaboration_points" in task_data:
        prompt += "Collaboration Points:\n"
        prompt += f"Shared Resources: {task_data['collaboration_points'].get('shared_resources', 'None')}\n"
        prompt += f"Integration Strategy: {task_data['collaboration_points'].get('integration_strategy', 'None')}\n"
        prompt += f"Communication Needs: {task_data['collaboration_points'].get('communication_needs', 'None')}\n\n"
    
    # Add overall tests if available
    if "overall_tests" in task_data:
        prompt += "Overall Tests:\n"
        if "FAIL_TO_PASS" in task_data["overall_tests"]:
            prompt += f"Failing tests that should pass after implementation: {task_data['overall_tests']['FAIL_TO_PASS']}\n"
        if "PASS_TO_PASS" in task_data["overall_tests"]:
            prompt += f"Tests that should continue to pass: {task_data['overall_tests']['PASS_TO_PASS']}\n\n"
    
    # Add code patch if available
    if patch:
        # Truncate patch if it's too large to avoid token limits
        MAX_PATCH_SIZE = 8000  # Reduced from 15000 to keep prompt size manageable
        if len(patch) > MAX_PATCH_SIZE:
            truncated_patch = patch[:MAX_PATCH_SIZE] + "\n... [TRUNCATED: patch too large, showing first portion only] ..."
            prompt += "\n## Code Patch (truncated)\n```diff\n" + truncated_patch + "\n```\n\n"
        else:
            prompt += "\n## Code Patch\n```diff\n" + patch + "\n```\n\n"
    
    # Add test patch if available
    if test_patch:
        # Truncate test patch if it's too large
        MAX_TEST_PATCH_SIZE = 5000  # Reduced from 10000 to keep prompt size manageable
        if len(test_patch) > MAX_TEST_PATCH_SIZE:
            truncated_test_patch = test_patch[:MAX_TEST_PATCH_SIZE] + "\n... [TRUNCATED: test patch too large, showing first portion only] ..."
            prompt += "\n## Test Patch (truncated)\n```diff\n" + truncated_test_patch + "\n```\n\n"
        else:
            prompt += "\n## Test Patch\n```diff\n" + test_patch + "\n```\n\n"
    
    # Add the evaluation request with focus on independence
    prompt += "Your primary task is to evaluate whether these features can be implemented independently AND each represents a reasonable, standalone feature, BUT they also REQUIRE coordination between developers.\n\n"
    prompt += "Focus on these specific criteria:\n"
    prompt += "1. Can Feature 1 be implemented WITHOUT requiring Feature 2, and does Feature 1 provide MEANINGFUL VALUE on its own?\n"
    prompt += "2. Can Feature 2 be implemented WITHOUT requiring Feature 1, and does Feature 2 provide MEANINGFUL VALUE on its own?\n"
    prompt += "3. Would implementing only one feature without the other still provide users with a complete, useful capability?\n"
    prompt += "4. Are these truly separate features that could reasonably exist independently, rather than just parts of the same logical feature?\n"
    prompt += "5. CRUCIALLY: Would implementing these features blindly/independently likely cause MERGE CONFLICTS or technical clashes?\n"
    prompt += "6. Do the features modify shared resources or overlapping areas of code that would require coordination?\n"
    prompt += "7. VERIFY that both features involve actual code changes, not just test modifications. If one or both features are purely test changes, they are not valid features.\n\n"
    prompt += "IMPORTANT REQUIREMENTS:\n"
    prompt += "- Each feature must be meaningful on its own (not just a partial implementation)\n"
    prompt += "- Features should be technically implementable separately\n"
    prompt += "- Features must involve ACTUAL CODE changes, not just test modifications\n"
    prompt += "- BUT features MUST have enough overlap/shared concerns that they would require coordination\n"
    prompt += "- If developers implemented these features blindly without awareness of each other, it should likely cause merge conflicts\n\n"
    prompt += "WHEN IN DOUBT: Always err towards recommending 'single' rather than 'split'. Only recommend 'split' when you are highly confident all criteria are fully satisfied.\n\n"
    prompt += "Analyze the code patches carefully to determine if there are overlapping changes to the same files or functions.\n\n"
    prompt += "Provide your recommendation with supporting reasons in this format:\n"
    prompt += "- recommendation: 'single' or 'split'\n"
    prompt += "- confidence: a number from 1-10 indicating how confident you are in this recommendation\n"
    prompt += "- reasoning: detailed explanation of why you made this recommendation\n"
    prompt += "- independence_analysis: assessment of how each feature could stand alone as a reasonable, complete feature\n"
    prompt += "- feature_validation: confirmation that both features involve actual code changes, not just test modifications\n"
    prompt += "- coordination_needs: specific areas where coordination would be required and potential merge conflicts"
    
    # Log prompt size to check if it's getting too large
    logger.info(f"Prompt size for {test_id}: {len(prompt)} characters")
    
    # Make API call to OpenAI with a capable model
    logger.info(f"Requesting evaluation for {test_id}")
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o",  # Using a more capable model for evaluation
            messages=[
                {"role": "system", "content": "You are a software development expert who evaluates feature splits. The IDEAL split has these characteristics: (1) Each feature is a reasonable, standalone feature with its own value; (2) Features can be implemented separately without requiring the other; (3) The features modify overlapping code/resources such that they would cause merge conflicts if implemented blindly without coordination; and (4) Both features involve actual code changes, not just test modifications. Be conservative and recommend 'split' ONLY if ALL characteristics are CLEARLY present. If you have ANY doubts about ANY of these criteria, err towards recommending 'single'. Provide your response in JSON format."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"},
        )
        
        # Extract and parse the response
        result_text = response.choices[0].message.content
        result = json.loads(result_text)
        
        return result
    except Exception as e:
        logger.error(f"API call failed: {e}")
        # If the error is related to token limit, we might need to further reduce the prompt
        if "maximum context length" in str(e) or "token limit" in str(e):
            logger.warning("Token limit exceeded. Retrying with smaller patch sizes...")
            # Retry with much smaller patch sizes
            if patch:
                MAX_PATCH_SIZE = 3000
                truncated_patch = patch[:MAX_PATCH_SIZE] + "\n... [TRUNCATED due to token limit] ..."
                prompt = prompt.replace(patch, truncated_patch)
            if test_patch and "Test Patch" in prompt:
                MAX_TEST_PATCH_SIZE = 1500
                truncated_test_patch = test_patch[:MAX_TEST_PATCH_SIZE] + "\n... [TRUNCATED due to token limit] ..."
                if "Test Patch (truncated)" in prompt:
                    # Replace the already truncated test patch
                    start_idx = prompt.find("## Test Patch (truncated)")
                    end_idx = prompt.find("```\n\n", start_idx)
                    if start_idx >= 0 and end_idx >= 0:
                        prompt = prompt[:start_idx] + f"## Test Patch (truncated further)\n```diff\n{truncated_test_patch}\n```\n\n" + prompt[end_idx+5:]
            
            # Retry with the reduced prompt
            logger.info(f"Retrying with reduced prompt size: {len(prompt)} characters")
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "You are a software development expert who evaluates feature splits. The IDEAL split has these characteristics: (1) Each feature is a reasonable, standalone feature with its own value; (2) Features can be implemented separately without requiring the other; (3) The features modify overlapping code/resources such that they would cause merge conflicts if implemented blindly without coordination; and (4) Both features involve actual code changes, not just test modifications. Be conservative and recommend 'split' ONLY if ALL characteristics are CLEARLY present. If you have ANY doubts about ANY of these criteria, err towards recommending 'single'. Provide your response in JSON format."},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"},
            )
            
            # Extract and parse the response from retry
            result_text = response.choices[0].message.content
            result = json.loads(result_text)
            
            return result
        else:
            # Re-raise if it's not a token limit issue
            raise

def main():
    parser = argparse.ArgumentParser(description='Evaluate PR task splits using LLM')
    parser.add_argument('--split_dir', type=str, default='split_tasks', 
                        help='Directory containing split tasks')
    parser.add_argument('--output_dir', type=str, default='evaluations',
                        help='Directory to save evaluation results')
    parser.add_argument('--limit', type=int, default=None,
                        help='Limit the number of tasks to evaluate')
    parser.add_argument('--force', action='store_true',
                        help='Force re-evaluation of already evaluated tasks')
    args = parser.parse_args()
    
    # Initialize the OpenAI client
    client = OpenAI()
    
    # Get the absolute paths
    base_dir = Path(__file__).parent
    split_dir = base_dir / args.split_dir
    output_dir = base_dir / args.output_dir
    
    # Ensure the output directory exists
    output_dir.mkdir(exist_ok=True, parents=True)
    
    # Load the SWE-bench dataset
    logger.info("Loading SWE-bench Verified dataset...")
    try:
        ds = load_dataset("princeton-nlp/SWE-bench_Verified")
        logger.info(f"Dataset loaded successfully. Found {len(ds['test'])} entries in the test split.")
    except Exception as e:
        logger.error(f"Error loading dataset: {e}")
        logger.warning("Proceeding without patch information. Evaluations may be less accurate.")
        ds = None
    
    # Get all task files
    task_files = list(split_dir.glob('*_task.json'))
    logger.info(f"Found {len(task_files)} task files to evaluate")
    
    # Apply limit if specified
    if args.limit is not None and args.limit > 0:
        task_files = task_files[:args.limit]
        logger.info(f"Limited to {len(task_files)} task files")
    
    # Process each task
    for task_file in tqdm(task_files, desc="Evaluating splits"):
        task_id = task_file.stem.replace('_task', '')
        output_file = output_dir / f"{task_id}_evaluation.json"
        
        # Skip if already evaluated and not force flag
        if output_file.exists() and not args.force:
            logger.info(f"Skipping {task_id}, already evaluated (use --force to re-evaluate)")
            continue
        
        try:
            # Load the task
            with open(task_file, 'r') as f:
                task_data = json.load(f)
            
            # Get patch and test_patch from the dataset if available
            patch = None
            test_patch = None
            
            if ds is not None:
                # Extract repo and instance_id from test_id (format: repo_instance_id)
                test_id = task_data.get("test_id", "")
                if test_id:
                    parts = test_id.split("_", 1)
                    if len(parts) == 2:
                        repo = parts[0]
                        instance_id = parts[1]
                        
                        # Find matching entry in dataset
                        for example in ds["test"]:
                            if example.get("repo") == repo and example.get("instance_id") == instance_id:
                                patch = example.get("patch", "")
                                test_patch = example.get("test_patch", "")
                                logger.info(f"Found patch information for {test_id}")
                                break
                        else:
                            logger.warning(f"No matching entry found in dataset for {test_id}")
            
            # Evaluate the split
            evaluation = evaluate_split(task_data, client, patch, test_patch)
            
            # Add metadata
            evaluation['task_id'] = task_id
            evaluation['original_file'] = str(task_file)
            evaluation['has_patch_info'] = bool(patch)
            
            # Save the evaluation
            with open(output_file, 'w') as f:
                json.dump(evaluation, f, indent=2)
            
            logger.info(f"Evaluated {task_id}")
            
        except Exception as e:
            logger.error(f"Error evaluating {task_id}: {e}")
    
    logger.info("Evaluation complete")

if __name__ == "__main__":
    main()
