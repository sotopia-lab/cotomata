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

# Prompt for splitting the problem statement
SPLIT_PROMPT = """
You are an AI assistant tasked with splitting a pull request (PR) into two logical parts. The PR has been analyzed and determined to be splittable. Your task is to take the original problem statement and tests, and split them between the two parts.

Here's the analysis of how the PR should be split:

{analysis}

I need you to split the following information into two distinct feature parts:
1. The problem statement
2. The test cases (both those that pass before and after the fix, and those that fail before but pass after)

DO NOT add any synthetic content or make up information. Simply divide the existing content between the two features based on the analysis.
DO NOT miss any information from the input problem statement or tests.
Format your response as a valid JSON object with this exact structure:
```
{{
  "feature1": {{
    "prompt": "Feature 1 problem statement",
    "hint_texts": "Description of what Part 1 includes, extracted from the analysis",
    "entrypoint": "Detailed information about which files and functions need to be modified for this feature",
    "tests": {{
      "FAIL_TO_PASS": "Tests for feature 1 that fail before but pass after the fix",
      "PASS_TO_PASS": "Tests for feature 1 that pass before and after the fix"
    }}
  }},
  "feature2": {{
    "prompt": "Feature 2 problem statement",
    "hint_texts": "Description of what Part 2 includes, extracted from the analysis",
    "entrypoint": "Detailed information about which files and functions need to be modified for this feature",
    "tests": {{
      "FAIL_TO_PASS": "Tests for feature 2 that fail before but pass after the fix",
      "PASS_TO_PASS": "Tests for feature 2 that pass before and after the fix"
    }}
  }}
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

Remember, your goal is to divide the existing content logically between the two features without adding new information.

IMPORTANT GUIDELINES FOR SPLITTING:
- Both feature prompts MUST be equally detailed and comprehensive
- Include ALL relevant information from the problem statement in the respective feature prompts
- Each feature prompt should include:
  * Detailed description of what needs to be fixed (at least 3-4 sentences)
  * All available reproduction steps and examples that demonstrate the issue
  * Expected behavior after the fix with examples
  * Any error messages or logs related to the feature
- The hint_texts should be comprehensive and include specific implementation guidance
- The entrypoint field must include:
  * Specific file paths that need modification
  * Function or method names that need to be changed
  * Line numbers or code blocks if available in the analysis
  * A clear starting point for implementation
- Ensure both features have approximately equal level of detail
- When splitting error messages or examples, include the full context to ensure clarity
- Include any details about testing or verification
"""

def split_pr_content(analysis_text, problem_statement, fail_to_pass, pass_to_pass, patch=None):
    """
    Use OpenAI's GPT model to split the PR content between two features.
    
    Args:
        analysis_text (str): The analysis of how the PR should be split
        problem_statement (str): The original problem statement
        fail_to_pass (str): Tests that fail before but pass after the fix
        pass_to_pass (str): Tests that pass before and after the fix
        patch (str, optional): The diff patch to extract file paths and function names
        
    Returns:
        dict: Split content for feature1 and feature2
    """
    try:
        # Prepare the prompt
        prompt = SPLIT_PROMPT.format(
            analysis=analysis_text,
            problem_statement=problem_statement,
            fail_to_pass=fail_to_pass,
            pass_to_pass=pass_to_pass
        )
        
        # Extract file paths and function names from patch if available
        if patch:
            file_paths = []
            for line in patch.splitlines():
                if line.startswith('+++ b/') or line.startswith('--- a/'):
                    file_path = line[6:]
                    if file_path not in file_paths:
                        file_paths.append(file_path)
            
            if file_paths:
                prompt += "\n\nThe PR modifies these files which may be helpful for the entrypoint information:\n"
                for file_path in file_paths:
                    prompt += f"- {file_path}\n"
        
        logger.info(f"Preparing to split PR content")
        
        # Make API call to OpenAI with a more capable model
        response = client.chat.completions.create(
            model="o3-mini",
            messages=[
                {"role": "system", "content": "You are a specialized assistant that helps split software development tasks into logical parts."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"},
            # temperature=0.2  # Lower temperature for more consistent outputs
        )
        
        # Extract and parse the response
        result_text = response.choices[0].message.content
        result = json.loads(result_text)
        logger.info(f"Result: {result}")
        
        return result
    except Exception as e:
        logger.error(f"Error splitting PR content: {e}")
        return None

def validate_split_features(split_results):
    """
    Validate that the split features are sufficiently detailed and balanced.
    
    Args:
        split_results (dict): The split features
        
    Returns:
        bool: True if the features are valid, False otherwise
    """
    if not split_results:
        return False
        
    # Check if both features exist
    if "feature1" not in split_results or "feature2" not in split_results:
        logger.warning("Split results missing feature1 or feature2")
        return False
        
    # Check if all required fields exist
    for feature_key in ["feature1", "feature2"]:
        feature = split_results.get(feature_key, {})
        if not all(key in feature for key in ["prompt", "hint_texts", "entrypoint", "tests"]):
            logger.warning(f"{feature_key} missing required fields")
            return False
            
    # Check if prompts are sufficiently detailed
    min_prompt_length = 150  # Minimum characters for a useful prompt
    feature1_prompt_len = len(split_results["feature1"]["prompt"])
    feature2_prompt_len = len(split_results["feature2"]["prompt"])
    
    if feature1_prompt_len < min_prompt_length or feature2_prompt_len < min_prompt_length:
        logger.warning(f"Prompt length too short: feature1={feature1_prompt_len}, feature2={feature2_prompt_len}")
        return False
        
    # Check if prompts are relatively balanced (one isn't much longer than the other)
    ratio = max(feature1_prompt_len, feature2_prompt_len) / max(1, min(feature1_prompt_len, feature2_prompt_len))
    if ratio > 5:  # If one prompt is more than 5x longer than the other
        logger.warning(f"Prompts are severely imbalanced: ratio={ratio}")
        return False
        
    return True

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
        
        # Use LLM to split the content, passing the patch for additional context
        split_results = split_pr_content(
            analysis_result.get("analysis", ""),
            problem_statement,
            fail_to_pass,
            pass_to_pass,
            patch
        )
        
        # Validate that the split results are sufficiently detailed and balanced
        if not validate_split_features(split_results):
            logger.error(f"Failed validation for {pr_id} - split features are not sufficiently detailed or balanced")
            return False
        
        if not split_results:
            logger.error(f"Failed to split content for {pr_id}")
            return False
            
        # Create the task object
        task = {
            "repo": repo,
            "test_id": f"{repo}_{instance_id}",
            "base_commit": base_commit,
            "patch": patch,
            "test_patch": test_patch,
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
            "overall_tests": {
                "FAIL_TO_PASS": fail_to_pass,
                "PASS_TO_PASS": pass_to_pass
            }
        }
        
        # Save the task to a file
        output_file = OUTPUT_DIR / f"{pr_id}_task.json"
        with open(output_file, "w") as f:
            json.dump(task, f, indent=2)
            
        logger.info(f"Generated task file for {pr_id} at {output_file}")
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
    validation_failed_count = 0
    
    # Create a list of arguments for each worker
    worker_args = [(pr.get("pr_id"), ds) for pr in splittable_prs]
    
    # Use ThreadPoolExecutor for parallel processing
    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
        # Process results as they complete
        for pr_id, success in tqdm(
            executor.map(process_pr_worker, worker_args),
            total=len(worker_args),
            desc="Generating task files"
        ):
            results.append((pr_id, success))
            if success:
                successful_count += 1
            else:
                failed_count += 1
    
    # Gather statistics on feature prompts
    prompt_lengths = {"feature1": [], "feature2": []}
    for pr_id, success in results:
        if success:
            task_file = OUTPUT_DIR / f"{pr_id}_task.json"
            if task_file.exists():
                with open(task_file, "r") as f:
                    task = json.load(f)
                    prompt_lengths["feature1"].append(len(task["feature1"]["prompt"]))
                    prompt_lengths["feature2"].append(len(task["feature2"]["prompt"]))
    
    # Calculate statistics
    if prompt_lengths["feature1"] and prompt_lengths["feature2"]:
        avg_feature1_length = sum(prompt_lengths["feature1"]) / len(prompt_lengths["feature1"])
        avg_feature2_length = sum(prompt_lengths["feature2"]) / len(prompt_lengths["feature2"])
        max_feature1_length = max(prompt_lengths["feature1"])
        max_feature2_length = max(prompt_lengths["feature2"])
        min_feature1_length = min(prompt_lengths["feature1"])
        min_feature2_length = min(prompt_lengths["feature2"])
        
        logger.info(f"Generated {successful_count} task files successfully")
        logger.info(f"Failed to generate {failed_count} task files")
        logger.info(f"Feature1 prompt length - Avg: {avg_feature1_length:.1f}, Min: {min_feature1_length}, Max: {max_feature1_length}")
        logger.info(f"Feature2 prompt length - Avg: {avg_feature2_length:.1f}, Min: {min_feature2_length}, Max: {max_feature2_length}")
        logger.info(f"Average ratio: {max(avg_feature1_length, avg_feature2_length) / min(avg_feature1_length, avg_feature2_length):.2f}")
    else:
        logger.info(f"Generated {successful_count} task files successfully")
        logger.info(f"Failed to generate {failed_count} task files")

if __name__ == "__main__":
    main() 