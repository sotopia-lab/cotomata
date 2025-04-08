import glob
import json
import os
import re
from tqdm import tqdm
import vertexai
from vertexai.generative_models import GenerativeModel, HarmCategory, HarmBlockThreshold
from anthropic import AnthropicVertex


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
    
    # Process the response
    matches = re.findall(file_pattern, model_response)
    
    for path, content in matches:
        # Clean up the content (remove extra whitespace at start and end)
        content = content.strip()
        
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

# # Init Vertex AI
# PROJECT_ID = "gcp-multi-agent"
# vertexai.init(project=PROJECT_ID, location="us-central1")
# # model_name = "gemini-2.0-flash-lite"
# model_name = "gemini-2.5-pro-exp-03-25"
# model = GenerativeModel(model_name)

LOCATION = "us-east5"  # This is important and should not be changed
client = AnthropicVertex(region=LOCATION, project_id="gcp-multi-agent", timeout=1000.0,)
model_name = "claude-3-7-sonnet@20250219"

folder = "merged_tasks_verified"
# Try to resume from existing results
results_path = f"{folder}/clean.json"
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
content: [The reconstructed original base code. Include all necessary files under base/. 
This code should be executable without additional dependencies beyond those specified in requirements.txt.]
<base/codebase.py END>

<base/requirements.txt START>
content: [The required Python packages with versions if necessary.]
<base/requirements.txt END>

<features/feature1.md START>
content: [A concise, clear description of Feature 1]
<features/feature1.md END>

<features/feature2.md START>
content: [A concise, clear description of Feature 2]
<features/feature2.md END>

<answer/codebase.py START>
content: [The correctly merged implementation incorporating both features. 
Include all necessary files under answer/]
<answer/codebase.py END>

<answer/test.py START>
content: [Comprehensive unit tests that verify both features work correctly.
Tests should import codebase.py and pass all assertions]
<answer/test.py END>

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

    try:
        # response = model.generate_content(prompt,
        #         safety_settings={
        #             HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
        #             HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
        #             HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
        #             HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
        #         },
        #     )
        
        # results[index] = {"repo": task["repo"], "test_id": task["test_id"], "response_text": response.text, "files": extract_file_content(response.text)}

        response = client.messages.create(
                messages=[
                    {
                        "role": "user",
                        "content": prompt,
                    }
                ],
                model=model_name,
                max_tokens=40000,
            )

        results[index] = {"repo": task["repo"], "test_id": task["test_id"], "response_text": response.content[0].text, "files": extract_file_content(response.content[0].text)}

        # Save after each successful inference
        with open(results_path, mode='w', encoding='utf-8') as f:
            json.dump(results, f, indent=4, ensure_ascii=False)

    except Exception as e:
        print(f"Error at index {index}: {e}")
        print("Saving progress and exiting.")
        with open(results_path, mode='w', encoding='utf-8') as f:
            json.dump(results, f, indent=4, ensure_ascii=False)
        break  # Exit and allow re-run later to resume

    
    