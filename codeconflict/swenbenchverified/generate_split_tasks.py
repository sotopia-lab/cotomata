#!/usr/bin/env python3
import os
import json
import time
from pathlib import Path
from datasets import load_dataset
from openai import OpenAI
from tqdm import tqdm
import logging
import concurrent.futures
from threading import Lock

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("task_generation.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Create a lock for thread-safe operations
results_lock = Lock()

# Initialize OpenAI client
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
if not os.environ.get("OPENAI_API_KEY"):
    logger.error("OpenAI API key not found. Please set the OPENAI_API_KEY environment variable.")
    exit(1)

# Paths
ANALYSIS_DIR = Path("analysis_results_relaxed")
SUMMARY_FILE = ANALYSIS_DIR / "splittable_prs_summary.json"
OUTPUT_DIR = Path("split_tasks")
OUTPUT_DIR.mkdir(exist_ok=True)

# Enhanced prompt for splitting the problem statement with collaborative approach
SPLIT_PROMPT = """
You are an AI assistant tasked with splitting a pull request (PR) into two logical parts. The PR has been analyzed and determined to be splittable. Your task is to take the original problem statement, tests, and test patches, and split them between the two parts in a way that encourages collaboration.

Here's the analysis of how the PR should be split:

{analysis}

Project information:
- Repository: {repo}
- Difficulty rating: {difficulty}

I need you to split the following information into two distinct feature parts that require collaboration:
1. The problem statement
2. The test cases (both those that pass before and after the fix, and those that fail before but pass after)
3. The test patch showing how test files are modified

IMPORTANT: Feature prompts must be STRICTLY based on the problem statement only. Do NOT include any test information in the feature prompts.
- The feature1 and feature2 "prompt" fields should ONLY contain information from the original problem statement.
- Test information should ONLY be included in the "tests" fields for each feature.
- Developers should not have access to test information through the prompts.

Carefully analyze the full code patch provided at the end of this prompt. This contains the actual code changes in diff format and is crucial for understanding how to split the PR effectively.

DO NOT add any synthetic content or make up information. Simply divide the existing content between the two features based on the analysis.
DO NOT miss any information from the input problem statement or tests.

IMPORTANT: After reviewing the content, if you determine that the PR CANNOT be meaningfully split into collaborative features despite the initial analysis, return a JSON with "can_be_split": false and include a "reason" field explaining why.

Format your response as a valid JSON object with this exact structure:
```
{{
  "can_be_split": true,
  "feature1": {{
    "prompt": "Feature 1 problem statement - STRICTLY based on the original problem statement only, NO test information",
    "hint_texts": "Description of what Part 1 includes, extracted from the analysis",
    "entrypoint": "Detailed information about which files and functions need to be modified for this feature",
    "tests": {{
      "FAIL_TO_PASS": "Tests for feature 1 that fail before but pass after the fix",
      "PASS_TO_PASS": "Tests for feature 1 that pass before and after the fix"
    }}
  }},
  "feature2": {{
    "prompt": "Feature 2 problem statement - STRICTLY based on the original problem statement only, NO test information",
    "hint_texts": "Description of what Part 2 includes, extracted from the analysis",
    "entrypoint": "Detailed information about which files and functions need to be modified for this feature",
    "tests": {{
      "FAIL_TO_PASS": "Tests for feature 2 that fail before but pass after the fix",
      "PASS_TO_PASS": "Tests for feature 2 that pass before and after the fix"
    }}
  }},
  "collaboration_points": {{
    "shared_resources": "List of files, data structures, or components that both features need to interact with",
    "integration_strategy": "How the two features need to work together to create a complete solution",
    "communication_needs": "What the developers implementing each feature need to discuss"
  }}
}}
```

If the PR cannot be properly split, return:
```
{{
  "can_be_split": false,
  "reason": "Detailed explanation of why this PR cannot be meaningfully split into collaborative features"
}}
```

Here's the content to split:

## Problem Statement
{problem_statement}

## Tests that FAIL before but PASS after the fix
```
{fail_to_pass}
```

## Tests that PASS before and after the fix
```
{pass_to_pass}
```

## Test Patch
```
{test_patch}
```

Remember, your goal is to divide the existing content logically between the two features without adding new information.

IMPORTANT GUIDELINES FOR COLLABORATIVE SPLITTING:
- The feature prompts MUST ONLY contain information from the original problem statement
- Do NOT include any test information or test cases in the feature prompts
- Split features into parts that are FUNCTIONALLY TESTABLE individually but share some resources or components
- Create intentional "integration points" where code from both features must work together
- Include shared state, files, or data structures that both features must interact with
- Design feature1 to expose APIs or interfaces that feature2 will consume
- Each feature should pass its individual tests, but complete integration requires coordination
- Split along functional boundaries while maintaining some interdependencies
- Both feature prompts MUST be equally detailed and comprehensive
- Each feature prompt should include:
  * Detailed description of what needs to be fixed (at least 3-4 sentences)
  * Expected behavior after the fix with examples
  * Any error messages or logs related to the feature (ONLY if they appear in the problem statement)
- The hint_texts should be comprehensive and include specific implementation guidance
- The entrypoint field must include:
  * Specific file paths that need modification
  * Function or method names that need to be changed
  * Line numbers or code blocks if available in the analysis
  * A clear starting point for implementation
"""

def extract_file_info(patch):
    """
    Extract detailed file and function information from the patch.
    
    Args:
        patch (str): The diff patch
        
    Returns:
        dict: Information about modified files and functions
    """
    if not patch:
        return {}
        
    file_info = {}
    current_file = None
    function_context = []
    
    for line in patch.splitlines():
        # Track file changes
        if line.startswith('+++ b/') or line.startswith('--- a/'):
            file_path = line[6:]
            if '+++ b/' in line:
                current_file = file_path
                file_info[current_file] = {
                    'functions': set(),
                    'changes': []
                }
        
        # Track function context
        if current_file and line.startswith('@@ '):
            context = line.split('@@')[1].strip()
            if context:
                function_context = [context]
                
        # Track actual changes
        if current_file and (line.startswith('+') or line.startswith('-')) and not (line.startswith('+++ ') or line.startswith('--- ')):
            # Try to identify function names
            code_line = line[1:].strip()
            if 'def ' in code_line:
                func_name = code_line.split('def ')[1].split('(')[0].strip()
                if current_file and func_name:
                    file_info[current_file]['functions'].add(func_name)
                    
            # Add the change with context
            if current_file:
                file_info[current_file]['changes'].append({
                    'line': line,
                    'context': function_context[-1] if function_context else ''
                })
    
    # Convert sets to lists for JSON serialization
    for file_path in file_info:
        file_info[file_path]['functions'] = list(file_info[file_path]['functions'])
        
    return file_info

def split_pr_content(analysis_text, problem_statement, fail_to_pass, pass_to_pass, repo, difficulty, patch=None, test_patch=None):
    """
    Use OpenAI's GPT model to split the PR content between two collaborative features.
    
    Args:
        analysis_text (str): The analysis of how the PR should be split
        problem_statement (str): The original problem statement
        fail_to_pass (str): Tests that fail before but pass after the fix
        pass_to_pass (str): Tests that pass before and after the fix
        repo (str): The repository name
        difficulty (str): The difficulty rating of the PR
        patch (str, optional): The diff patch to extract file paths and function names
        test_patch (str, optional): The test patch showing changes to test files
        
    Returns:
        dict: Split content for feature1 and feature2 with collaboration points, or
              a dict with {'can_be_split': False, 'reason': '...'} if the model determines it cannot be split
    """
    try:
        # Extract detailed file information from the patch
        file_info = extract_file_info(patch)
        
        # Prepare the prompt
        prompt = SPLIT_PROMPT.format(
            analysis=analysis_text,
            problem_statement=problem_statement,
            fail_to_pass=fail_to_pass,
            pass_to_pass=pass_to_pass,
            test_patch=test_patch or "No test patch available",
            repo=repo,
            difficulty=difficulty
        )
        
        # Add the full patch to the prompt, with size limit to avoid token overflow
        MAX_PATCH_SIZE = 50000  # Characters, approximately 12500 tokens
        if patch:
            if len(patch) > MAX_PATCH_SIZE:
                logger.warning(f"Patch is very large ({len(patch)} chars), truncating to {MAX_PATCH_SIZE} chars to avoid token limit")
                truncated_patch = patch[:MAX_PATCH_SIZE] + "\n... [TRUNCATED: patch too large, showing first portion only] ..."
                prompt += "\n\n## Full Code Patch (truncated)\n```\n" + truncated_patch + "\n```\n"
            else:
                logger.info(f"Including full code patch in prompt (length: {len(patch)} chars)")
                prompt += "\n\n## Full Code Patch\n```\n" + patch + "\n```\n"
        else:
            logger.warning("No code patch available to include in prompt")
        
        # Add file and function information to the prompt
        if file_info:
            prompt += "\n\nDetailed file and function modifications:\n"
            for file_path, details in file_info.items():
                prompt += f"\nFile: {file_path}\n"
                if details['functions']:
                    prompt += f"Modified functions: {', '.join(details['functions'])}\n"
                prompt += f"Number of changes: {len(details['changes'])}\n"
                
                # Include a sample of the changes
                if details['changes']:
                    prompt += "Sample changes:\n"
                    for change in details['changes'][:5]:  # Limit to 5 sample changes
                        prompt += f"  {change['line']}\n"
        
        logger.info(f"Preparing to split PR content with collaborative approach")
        
        # Make API call to OpenAI with a more capable model
        response = client.chat.completions.create(
            model="o3-mini",
            reasoning_effort="high",
            messages=[
                {"role": "system", "content": "You are a specialized assistant that helps split software development tasks into logical parts that require collaboration."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"},
        )
        
        # Extract and parse the response
        result_text = response.choices[0].message.content
        result = json.loads(result_text)
        
        # Check if the model decided this PR cannot be split
        if 'can_be_split' in result and result['can_be_split'] == False:
            logger.info(f"Model determined PR cannot be split: {result.get('reason', 'No reason provided')}")
            return result
            
        logger.info(f"Generated collaborative split for PR")
        
        return result
    except Exception as e:
        logger.error(f"Error splitting PR content: {e}")
        return None

def process_pr(pr_id, dataset):
    """
    Process a single PR to generate a split task.
    """
    try:
        # Load the analysis result
        analysis_file = ANALYSIS_DIR / f"{pr_id}.json"
        if not analysis_file.exists():
            logger.warning(f"Analysis file not found for {pr_id}")
            return False
            
        with open(analysis_file, "r") as f:
            analysis_result = json.load(f)
            
        # Check if the PR is marked as splittable
        if not analysis_result.get("can_be_split", False):
            logger.warning(f"PR {pr_id} is marked as not splittable")
            return False
            
        # Get the PR data from the dataset
        repo, instance_id = pr_id.replace("_", "/", 1).split("_", 1)
        
        # Find the matching example in the dataset
        for i, example in enumerate(dataset["test"]):
            if example.get("repo") == repo and example.get("instance_id") == instance_id:
                pr_data = example
                break
        else:
            logger.warning(f"PR {pr_id} not found in dataset")
            return False
            
        # Extract PR content
        base_commit = pr_data.get("base_commit", "")
        patch = pr_data.get("patch", "")
        test_patch = pr_data.get("test_patch", "")
        problem_statement = pr_data.get("problem_statement", "")
        pass_to_pass = pr_data.get("PASS_TO_PASS", "")
        fail_to_pass = pr_data.get("FAIL_TO_PASS", "")
        difficulty = pr_data.get("difficulty", "")
        
        # Use LLM to split the content, passing additional context including test_patch
        split_results = split_pr_content(
            analysis_result.get("analysis", ""),
            problem_statement,
            fail_to_pass,
            pass_to_pass,
            repo,
            difficulty,
            patch,
            test_patch
        )
        
        if not split_results:
            logger.error(f"Failed to split content for {pr_id}")
            return False
            
        # Check if the model determined the PR cannot be split
        if 'can_be_split' in split_results and split_results['can_be_split'] == False:
            reason = split_results.get('reason', 'No reason provided')
            logger.warning(f"Model determined PR {pr_id} cannot be split: {reason}")
            
            # Save the skip decision to a separate file
            skip_file = OUTPUT_DIR / f"{pr_id}_skipped.json"
            with open(skip_file, "w") as f:
                json.dump({
                    "pr_id": pr_id,
                    "repo": repo,
                    "can_be_split": False,
                    "reason": reason
                }, f, indent=2)
                
            logger.info(f"Saved skip decision for {pr_id} at {skip_file}")
            return False
            
        # Check for required fields in the response
        required_fields = ["feature1", "feature2", "collaboration_points"]
        for field in required_fields:
            if field not in split_results:
                logger.error(f"Missing required field '{field}' in split results for {pr_id}")
                return False
                
        # Create the task object
        task = {
            "repo": repo,
            "test_id": f"{repo}_{instance_id}",
            "base_commit": base_commit,
            # "patch": patch,
            # "test_patch": test_patch,
            "difficulty": difficulty,
            "feature1": {
                "prompt": split_results.get("feature1", {}).get("prompt", ""),
                "hint_texts": split_results.get("feature1", {}).get("hint_texts", ""),
                "entrypoint": split_results.get("feature1", {}).get("entrypoint", ""),
                "tests": split_results.get("feature1", {}).get("tests", {"FAIL_TO_PASS": [], "PASS_TO_PASS": []})
            },
            "feature2": {
                "prompt": split_results.get("feature2", {}).get("prompt", ""),
                "hint_texts": split_results.get("feature2", {}).get("hint_texts", ""),
                "entrypoint": split_results.get("feature2", {}).get("entrypoint", ""),
                "tests": split_results.get("feature2", {}).get("tests", {"FAIL_TO_PASS": [], "PASS_TO_PASS": []})
            },
            "collaboration_points": split_results.get("collaboration_points", {
                "shared_resources": "",
                "integration_strategy": "",
                "communication_needs": ""
            }),
            "overall_tests": {
                "FAIL_TO_PASS": fail_to_pass,
                "PASS_TO_PASS": pass_to_pass
            }
        }
        
        # Save the task to a file
        output_file = OUTPUT_DIR / f"{pr_id}_task.json"
        with open(output_file, "w") as f:
            json.dump(task, f, indent=2)
            
        logger.info(f"Generated collaborative task file for {pr_id} at {output_file}")
        return True
        
    except Exception as e:
        logger.error(f"Error generating task for {pr_id}: {e}")
        return False

def process_pr_worker(args):
    """Worker function for parallel processing"""
    pr_id, dataset = args
    return pr_id, process_pr(pr_id, dataset)

def main():
    # Load the list of splittable PRs
    if not SUMMARY_FILE.exists():
        logger.error(f"Summary file not found at {SUMMARY_FILE}")
        return
        
    with open(SUMMARY_FILE, "r") as f:
        summary = json.load(f)
        
    splittable_prs = summary.get("splittable_prs", [])
    logger.info(f"Found {len(splittable_prs)} PRs that can be split")
    
    # Load the dataset
    logger.info("Loading SWE-bench Verified dataset...")
    try:
        ds = load_dataset("princeton-nlp/SWE-bench_Verified")
        logger.info(f"Dataset loaded successfully. Found {len(ds['test'])} entries in the test split.")
    except Exception as e:
        logger.error(f"Error loading dataset: {e}")
        return
        
    # Process PRs in parallel
    successful_count = 0
    failed_count = 0
    skipped_count = 0
    
    # Create a list of arguments for each worker
    worker_args = [(pr.get("pr_id"), ds) for pr in splittable_prs]
    
    # Use ThreadPoolExecutor for parallel processing
    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
        # Process results as they complete
        for pr_id, success in tqdm(
            executor.map(process_pr_worker, worker_args),
            total=len(worker_args),
            desc="Generating collaborative task files"
        ):
            results.append((pr_id, success))
            if success:
                successful_count += 1
            else:
                # Check if this was skipped by the model or failed due to other reasons
                skip_file = OUTPUT_DIR / f"{pr_id}_skipped.json"
                if skip_file.exists():
                    skipped_count += 1
                else:
                    failed_count += 1
    
    # Gather statistics on feature prompts and collaboration points
    prompt_lengths = {"feature1": [], "feature2": []}
    collab_points = []
    
    for pr_id, success in results:
        if success:
            task_file = OUTPUT_DIR / f"{pr_id}_task.json"
            if task_file.exists():
                with open(task_file, "r") as f:
                    task = json.load(f)
                    prompt_lengths["feature1"].append(len(task["feature1"]["prompt"]))
                    prompt_lengths["feature2"].append(len(task["feature2"]["prompt"]))
                    
                    # Check if collaboration points are present
                    if "collaboration_points" in task:
                        collab_len = sum(len(task["collaboration_points"].get(key, "")) 
                                     for key in ["shared_resources", "integration_strategy", "communication_needs"])
                        collab_points.append(collab_len)
    
    # Calculate statistics
    if prompt_lengths["feature1"] and prompt_lengths["feature2"]:
        avg_feature1_length = sum(prompt_lengths["feature1"]) / len(prompt_lengths["feature1"])
        avg_feature2_length = sum(prompt_lengths["feature2"]) / len(prompt_lengths["feature2"])
        max_feature1_length = max(prompt_lengths["feature1"])
        max_feature2_length = max(prompt_lengths["feature2"])
        min_feature1_length = min(prompt_lengths["feature1"])
        min_feature2_length = min(prompt_lengths["feature2"])
        
        avg_collab_len = sum(collab_points) / len(collab_points) if collab_points else 0
        
        logger.info(f"Generated {successful_count} collaborative task files successfully")
        logger.info(f"Skipped {skipped_count} PRs that the model determined could not be split")
        logger.info(f"Failed to generate {failed_count} task files due to errors")
        logger.info(f"Feature1 prompt length - Avg: {avg_feature1_length:.1f}, Min: {min_feature1_length}, Max: {max_feature1_length}")
        logger.info(f"Feature2 prompt length - Avg: {avg_feature2_length:.1f}, Min: {min_feature2_length}, Max: {max_feature2_length}")
        logger.info(f"Average collaboration points length: {avg_collab_len:.1f}")
        logger.info(f"Average ratio: {max(avg_feature1_length, avg_feature2_length) / min(avg_feature1_length, avg_feature2_length):.2f}")
    else:
        logger.info(f"Generated {successful_count} collaborative task files successfully")
        logger.info(f"Skipped {skipped_count} PRs that the model determined could not be split")
        logger.info(f"Failed to generate {failed_count} task files due to errors")

if __name__ == "__main__":
    main()