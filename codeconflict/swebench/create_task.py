import glob
import json
import os
import re
import time
from tqdm import tqdm
import shutil
import vertexai
from anthropic import AnthropicVertex

model_name = "claude-3-7-sonnet@20250219"

def extract_file_content(model_response):
    """
    Extract file content from the model's response to the collaborative coding challenge prompt.
    
    Args:
        model_response (str): The raw text response from the model
        
    Returns:
        dict: A dictionary with file paths as keys and their content as values
    """
    # Initialize the result dictionary
    result = {
        "base": {},
        "features": {},
        "answer": {}
    }
    
    # Define the pattern to look for files with START and END tags
    file_pattern = r'<([^>]+) START>\s*\n([\s\S]*?)\n<\1 END>'
    
    model_response = model_response.replace("</", "<")
    # Process the response
    matches = re.findall(file_pattern, model_response)
    
    for path, content in matches:
        # Clean up the content (remove extra whitespace at start and end)
        content = content.strip().strip('content:').strip().strip('```python').strip('```').strip()
        
        # Determine which category this file belongs to
        if path.startswith('base/'):
            filename = path.replace('base/', '')
            result["base"][filename] = content
        elif path.startswith('features/'):
            filename = path.replace('features/', '')
            result["features"][filename] = content
        elif path.startswith('answer/'):
            filename = path.replace('answer/', '')
            result["answer"][filename] = content
        else:
            # For any files that don't match the expected patterns
            # Just add them at the top level
            result[path] = content
    
    return result

def check_empty_files(files_dict):
    """
    Check if any category in the files dictionary is empty
    
    Args:
        files_dict: Dictionary of extracted files
        
    Returns:
        bool: True if any required section is empty, False otherwise
    """
    # Check if any main category is empty
    if not files_dict["base"] or not files_dict["features"] or not files_dict["answer"]:
        return True
    
    # Check if required files exist in each category
    if "codebase.py" not in files_dict["base"] or "requirements.txt" not in files_dict["base"]:
        return True
    
    if "feature1.md" not in files_dict["features"] or "feature2.md" not in files_dict["features"]:
        return True
    
    if "codebase.py" not in files_dict["answer"] or "test_feature1.py" not in files_dict["answer"] or "test_feature2.py" not in files_dict["answer"]:
        return True
    
    return False


def save_files_to_directory(index, result, output_dir="clean_task"):
    """
    Save the extracted file content to a directory structure.
    
    Args:
        results (dict): Dictionary containing the results for each task
        output_dir (str): Base output directory name
    """
    # Create the main output directory if it doesn't exist
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    # Create a subdirectory for this task
    task_dir = os.path.join(output_dir, str(index))
    if not os.path.exists(task_dir):
        os.makedirs(task_dir)
    
    # Save metadata about the task
    metadata = {
        "repo": result.get("repo", ""),
        "test_id": result.get("test_id", "")
    }
    with open(os.path.join(task_dir, "metadata.json"), "w") as f:
        json.dump(metadata, f, indent=4)
    
    # Get the files dictionary
    files = result.get("files", {})
    
    # Create and save files for each category
    for category in ["base", "features", "answer"]:
        category_dir = os.path.join(task_dir, category)
        if not os.path.exists(category_dir):
            os.makedirs(category_dir)
        
        # Save each file in this category
        for filename, content in files.get(category, {}).items():
            file_path = os.path.join(category_dir, filename)
            
            # Create parent directories if needed
            parent_dir = os.path.dirname(file_path)
            if parent_dir and not os.path.exists(parent_dir):
                os.makedirs(parent_dir)
            
            # Write the file content
            # content = content.split('```')[0]
            with open(file_path, "w") as f:
                f.write(content)

LOCATION = "us-east5"  # This is important and should not be changed
model = AnthropicVertex(region=LOCATION, project_id="gcp-multi-agent", timeout=1000.0)

output_dir = f"clean_task_{model_name}"
if os.path.exists(output_dir):
    shutil.rmtree(output_dir)

folder = "merged_tasks_verified"
# Try to resume from existing results
results_path = f"{folder}/{model_name}-clean.json"
if os.path.exists(results_path):
    with open(results_path, mode='r', encoding='utf-8') as f:
        results = json.load(f)
else:
    results = {}

files = glob.glob(f"{folder}/*.json")
for file in tqdm(files):

    if "clean" in file:
        continue

    index = file.split("/")[-1].split(".")[0]
    if index in results:
        continue
    
    with open(file, mode='r') as f:
        task = json.load(f)
    
    task1 = "Issue: " + task["feature1"]["prompt"] + "\nHints: " + task["feature1"]["hint_texts"]
    task2 = "Issue: " + task["feature2"]["prompt"] + "\nHints: " + task["feature2"]["hint_texts"]
    patch1 = task["feature1"]["patch"]
    patch2 = task["feature2"]["patch"]
    test_patch1 = task["feature1"]["test_patch"]
    test_patch2 = task["feature2"]["test_patch"]

    prompt = f"""## Overview
You are tasked with analyzing a code merge scenario where two programmers independently implemented different features on the same codebase. Your challenge is to create a simplified, educational example based on this real-world scenario that demonstrates code conflict resolution.

This scenario includes:
* Two feature descriptions
* Two code patches representing each feature implementation
* Two test file patches showing corresponding test updates

The current real-world example is complex and contains redundancies. Your task is to create a concise case study by:
1. Reconstructing and simplifying the original base code that both programmers started with
2. Clarifying and simplifying both feature descriptions, ideally each feature could be described in a single sentence
3. Creating a properly merged implementation that preserves essential logic from both features
4. Developing unit tests to verify the merged implementation functions correctly

## Required Output Format
Please organize your solution using exactly the following structure, and include content in between the <filepath START> and <filepath END> tags:
<base/codebase.py START>
content: [The reconstructed original base code. 
This code should be executable without additional dependencies beyond those specified in requirements.txt]
<base/codebase.py END>

<base/requirements.txt START>
content: [The required Python packages with versions if necessary]
<base/requirements.txt END>

<features/feature1.md START>
content: [A concise, clear description of Feature 1]
<features/feature1.md END>

<features/feature2.md START>
content: [A concise, clear description of Feature 2]
<features/feature2.md END>

<answer/codebase.py START>
content: [The correctly merged implementation incorporating both features]
<answer/codebase.py END>

<answer/test_feature1.py START>
content: [Unit tests that validate the correct functionality of Feature 1 using the unittest package. These tests should import codebase.py and pass all assertions]
<answer/test_feature1.py END>

<answer/test_feature2.py START>
content: [Unit tests that validate the correct functionality of Feature 2 using the unittest package. These tests should import codebase.py and pass all assertions]
<answer/test_feature2.py END>

## Real-World Input Data
The following sections contain the real-world code examples that you should use as reference. Your goal is to create a simplified version that captures the essential aspects of this merge scenario.
<Feature 1 START>
{task1}
<Feature 1 END>

<Feature 2 START>
{task2}
<Feature 2 END>

<Feature 1 Patch START>
{patch1}
<Feature 1 Patch END>

<Feature 2 Patch START>
{patch2}
<Feature 2 Patch END>

<Feature 1 Test Patch START>
{test_patch1}
<Feature 1 Test Patch END>

<Feature 2 Test Patch START>
{test_patch2}
<Feature 2 Test Patch END>

## Success Criteria
Your solution will be evaluated on:
Accuracy - The merged code must correctly implement both features
Simplicity - The example should be easy to understand while preserving key merge challenges
Clarity - Code and documentation should be well-organized and clearly explained
Completeness - All required files must be provided and function correctly
"""

    
    attempts = 0
    max_attempts = 5
    success = False
    while not success and attempts < max_attempts:
        try:
            attempts += 1
            
            completion = model.messages.create(
                messages=[
                    {
                        "role": "user",
                        "content": prompt,
                    }
                ],
                model=model_name,
                max_tokens=50000,
            )
            response = completion.content[0].text

            extracted_files = extract_file_content(response)
            
            if check_empty_files(extracted_files):
                print(f"Warning: Missing required files in response for index {index}. Retrying...")
                time.sleep(5)  # Short delay before retry
                continue
            
            # If we made it here, everything is good
            result = {
                "repo": task["repo"], 
                "test_id": task["test_id"], 
                "response_text": response, 
                "files": extracted_files
            }
            results[index] = result
            
            with open(results_path, mode='w', encoding='utf-8') as f:
                json.dump(results, f, indent=4, ensure_ascii=False)

            save_files_to_directory(index, result, output_dir=output_dir)

            success = True

        except Exception as e:
            print(f"Error at index {index}, attempt {attempts}: {e}")
            if attempts >= max_attempts:
                print(f"Max retries reached for index {index}. Moving to next item.")
            else:
                print(f"Retrying in 5 seconds...")
                time.sleep(5 * attempts)  # Wait before retry
    
    # If we've exhausted retries without success, log the failure but continue with next file
    if not success:
        print(f"Failed to process index {index} after {max_attempts} attempts")