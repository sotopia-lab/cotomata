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
        logging.FileHandler("pr_analysis.log"),
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

# Create output directory
output_dir = Path("analysis_results")
output_dir.mkdir(exist_ok=True)

# PR Splitting Analysis Prompt
PR_ANALYSIS_PROMPT = """
You are an experienced software developer tasked with determining whether a pull request (PR) can be split into two logical parts. Your goal is to analyze the code changes in the PR and provide a clear assessment of whether it can be divided into two independently testable parts, even if some coordination is needed.

## Input

I will provide you with:
- The diff contents of a PR, showing code additions, deletions, and changes
- Optionally, additional context like PR description, comments, or test files

## Analysis Process

Please perform the following steps in your analysis:

1. **Identify all modified components**:
   - List all files that are being modified
   - For each file, identify the specific functions, methods, or code blocks being changed
   - Note any new functions, methods, classes, or parameters being added

2. **Evaluate logical separation**:
   - Can the changes be logically separated by feature or functionality?
   - Is there a natural division in the code changes?
   - Could different developers work on different aspects with coordination?

3. **Consider testability**:
   - Could each logical part be tested independently?
   - Could the test cases be divided to verify each part separately?
   - Would each part result in functional code when implemented?

## Output Format

Please provide your analysis in the following format:

1. **Summary Assessment**: A clear yes/no statement on whether the PR can be split into two logical parts.

2. **Reasoning**: Explain the key factors that led to your decision.

3. **If YES**:
   - Describe how the PR could be split (Part 1 would include... Part 2 would include...)
   - Explain the logical separation between the parts
   - Suggest how the test cases might be divided
   - Note any coordination that would be needed between developers
   - CLEARLY split the test cases into two parts testing the two parts of the PR

4. **If NO**:
   - Explain why the PR cannot be logically split
   - Identify the specific aspects that make it a cohesive unit
   - Explain why it would be impractical to test parts independently

Remember, it's acceptable if:
- Both parts modify the same files or even the same functions
- Some communication is needed between implementors
- There might be merge conflicts if developed in parallel
- The parts have some dependencies

The main criteria are logical separation and independent testability of each part.
"""

def analyze_pr(diff_content, pr_description=None, test_patch=None, pass_to_pass=None, fail_to_pass=None):
    """
    Analyze a PR using OpenAI's GPT-4o model to determine if it can be split.
    
    Args:
        diff_content (str): The diff content of the PR
        pr_description (str, optional): Additional PR context
        test_patch (str, optional): Test patch content
        pass_to_pass (str, optional): PASS_TO_PASS content
        fail_to_pass (str, optional): FAIL_TO_PASS content
    
    Returns:
        dict: The analysis result
    """
    # Prepare input content
    input_content = f"## PR Diff\n\n```\n{diff_content}\n```\n"
    
    if pr_description:
        input_content += f"\n## PR Description\n\n{pr_description}\n"
        
    if test_patch:
        input_content += f"\n## Test Patch\n\n```\n{test_patch}\n```\n"
        
    if pass_to_pass:
        input_content += f"\n## PASS_TO_PASS (Test that passes before and after fix)\n\n```\n{pass_to_pass}\n```\n"
        
    if fail_to_pass:
        input_content += f"\n## FAIL_TO_PASS (Test that fails before but passes after fix)\n\n```\n{fail_to_pass}\n```\n"
    
    try:
        # Make API call to OpenAI
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": PR_ANALYSIS_PROMPT},
                {"role": "user", "content": input_content}
            ],
            temperature=0.0
        )
        
        # Extract and return the analysis
        analysis = response.choices[0].message.content
        return {
            "analysis": analysis,
            "can_be_split": "yes" in analysis.lower().split("summary assessment")[1].split("reasoning")[0].lower(),
            "raw_response": response.model_dump(),
        }
    except Exception as e:
        logger.error(f"Error analyzing PR: {e}")
        return {"error": str(e)}

def process_example(i, example, total_examples, all_results):
    """Worker function to process a single example"""
    try:
        # Extract PR content based on the actual dataset structure
        repo_name = example.get("repo", "unknown_repo")
        instance_id = example.get("instance_id", "unknown_id")
        patch = example.get("patch", "")
        problem_statement = example.get("problem_statement", "")
        test_patch = example.get("test_patch", "")
        pass_to_pass = example.get("PASS_TO_PASS", "")
        fail_to_pass = example.get("FAIL_TO_PASS", "")
        
        # Create a unique identifier for this PR
        pr_id = f"{repo_name}_{instance_id}".replace("/", "_")
        
        # Thread-safe logging
        logger.info(f"Processing PR {i+1}/{total_examples}: {pr_id}")
        
        # Check if this PR has already been analyzed
        output_file = output_dir / f"{pr_id}.json"
        if output_file.exists():
            logger.info(f"Skipping {pr_id} - already analyzed")
            # Load existing result to include in summary
            try:
                with open(output_file, "r") as f:
                    result = json.load(f)
                result_summary = {
                    "pr_id": pr_id,
                    "repo": repo_name,
                    "instance_id": instance_id,
                    "can_be_split": result.get("can_be_split", False)
                }
                with results_lock:
                    all_results.append(result_summary)
                return result_summary
            except Exception as e:
                logger.error(f"Error loading existing result for {pr_id}: {e}")
                return None
            
        # Analyze the PR with additional test information
        analysis_result = analyze_pr(
            patch, 
            problem_statement,
            test_patch,
            pass_to_pass,
            fail_to_pass
        )
        
        # Add metadata to the result
        analysis_result["metadata"] = {
            "repo": repo_name,
            "instance_id": instance_id,
            "base_commit": example.get("base_commit", ""),
            "version": example.get("version", ""),
            "difficulty": example.get("difficulty", ""),
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        
        # Create result summary
        result_summary = {
            "pr_id": pr_id,
            "repo": repo_name,
            "instance_id": instance_id,
            "can_be_split": analysis_result.get("can_be_split", False)
        }
        
        # Thread-safe update of results list
        with results_lock:
            all_results.append(result_summary)
        
        # Save the result
        with open(output_file, "w") as f:
            json.dump(analysis_result, f, indent=2)
        
        logger.info(f"Analysis saved to {output_file}")
        
        return result_summary
        
    except Exception as e:
        logger.error(f"Error processing example {i}: {e}")
        return None

def main():
    # Load dataset
    logger.info("Loading SWE-bench Verified dataset...")
    try:
        ds = load_dataset("princeton-nlp/SWE-bench_Verified")
        logger.info(f"Dataset loaded successfully. Found {len(ds['test'])} entries in the test split.")
    except Exception as e:
        logger.error(f"Error loading dataset: {e}")
        return
    
    # List to collect all processed results
    all_results = []
    
    # Use indexing to access items in the dataset
    total_examples = len(ds['test'])
    # For testing with a smaller set, use: min(20, total_examples)
    num_examples_to_process = total_examples
    
    # Process PRs in parallel using ThreadPoolExecutor
    with concurrent.futures.ThreadPoolExecutor(max_workers=16) as executor:
        # Submit all tasks
        future_to_index = {
            executor.submit(process_example, i, ds['test'][i], num_examples_to_process, all_results): i 
            for i in range(num_examples_to_process)
        }
        
        # Process results as they complete
        for future in tqdm(concurrent.futures.as_completed(future_to_index), 
                          total=len(future_to_index), 
                          desc="Processing PRs"):
            idx = future_to_index[future]
            try:
                # This will raise an exception if the task raised an exception
                result = future.result()
                if result:
                    logger.info(f"Completed analysis of PR at index {idx}")
            except Exception as e:
                logger.error(f"Task for example {idx} generated an exception: {e}")
    
    # Generate summary of PRs that can be split
    splittable_prs = [pr for pr in all_results if pr.get("can_be_split", False)]
    
    # Log summary statistics
    logger.info(f"Analysis complete! Processed {len(all_results)} PRs.")
    if all_results:
        percentage = len(splittable_prs) / len(all_results) * 100
        logger.info(f"Found {len(splittable_prs)} PRs that can be split ({percentage:.1f}%).")
    else:
        logger.info("No results were processed.")
    
    # Save the list of splittable PRs
    summary_file = output_dir / "splittable_prs_summary.json"
    with open(summary_file, "w") as f:
        json.dump({
            "total_analyzed": len(all_results),
            "total_splittable": len(splittable_prs),
            "percentage_splittable": f"{len(splittable_prs)/max(1, len(all_results))*100:.1f}%",
            "splittable_prs": splittable_prs
        }, f, indent=2)
    
    # Also save as a simple CSV for easy viewing
    summary_csv = output_dir / "splittable_prs_summary.csv"
    with open(summary_csv, "w") as f:
        f.write("PR ID,Repository,Instance ID\n")
        for pr in splittable_prs:
            f.write(f"{pr['pr_id']},{pr['repo']},{pr['instance_id']}\n")
    
    logger.info(f"Summary of splittable PRs saved to {summary_file} and {summary_csv}")

if __name__ == "__main__":
    main()
