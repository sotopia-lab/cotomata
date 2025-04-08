import os
import json
import re
import shutil

def save_files_to_directory(results, output_dir="clean_task"):
    """
    Save the extracted file content to a directory structure.
    
    Args:
        results (dict): Dictionary containing the results for each task
        output_dir (str): Base output directory name
    """
    # Create the main output directory if it doesn't exist
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    # Process each result
    for index, result in results.items():
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
            json.dump(metadata, f, indent=2)
        
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

# Example usage
if __name__ == "__main__":
    # Load your results from a JSON file if you have one
    # Otherwise, you can pass your results dictionary directly
    if os.path.exists("clean_task"):
        shutil.rmtree("clean_task")

    try:
        with open("./merged_tasks_verified/clean.json", "r") as f:
            results = json.load(f)
        save_files_to_directory(results)
        print("Files have been successfully saved to the 'clean_task' directory.")
    except FileNotFoundError:
        print("Please provide your results dictionary or create a 'results.json' file.")