#!/usr/bin/env python3
import os
import sys
import subprocess
import shutil
import logging
import unittest
from pathlib import Path
import tempfile
import json
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("validation_results.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class RepositoryValidator:
    def __init__(self, base_path):
        # Store the original working directory and convert base_path to absolute path
        self.original_dir = os.getcwd()
        self.base_path = Path(os.path.abspath(base_path))
        self.results = {
            "total_repos": 0,
            "step1_success": 0,
            "step2_success": 0,
            "step3_success": 0,
            "failed_repos": {}
        }
        self.test_files = ["test_feature1.py", "test_feature2.py"]
        self.venv_dirs = {}  # Dictionary to store virtual environment paths for each repository

    def validate_all_repositories(self):
        """Validate all repositories in the base path."""
        repos = [d for d in self.base_path.iterdir() if d.is_dir()]
        self.results["total_repos"] = len(repos)
        
        logger.info(f"Found {len(repos)} repositories to validate")
        
        for repo_path in repos:
            logger.info(f"\n{'='*50}\nValidating repository: {repo_path.name}\n{'='*50}")
            self.validate_repository(repo_path)
        
        self._summarize_results()

    def validate_repository(self, repo_path):
        """Run the three-step validation process on a single repository."""
        repo_name = repo_path.name
        self.results["failed_repos"][repo_name] = {
            "status": "PASS", 
            "errors": {},
            "test_results": {
                "positive": {},
                "negative": {}
            }
        }
        
        # Ensure we're using absolute paths
        repo_path = Path(os.path.abspath(str(repo_path)))
        logger.info(f"Validating repository at: {repo_path}")
        
        try:
            # Step 1: Dependency Check
            step1_result = self._step1_dependency_check(repo_path)
            if not step1_result["success"]:
                self.results["failed_repos"][repo_name]["status"] = "FAIL_STEP1"
                self.results["failed_repos"][repo_name]["errors"]["step1"] = step1_result["error"]
                return
            
            self.results["step1_success"] += 1
            
            # Step 2: Positive Test
            step2_result = self._step2_positive_test(repo_path)
            if not step2_result["success"]:
                self.results["failed_repos"][repo_name]["status"] = "FAIL_STEP2"
                self.results["failed_repos"][repo_name]["errors"]["step2"] = step2_result["error"]
                return
            
            self.results["step2_success"] += 1
            
            # Step 3: Negative Test
            step3_result = self._step3_negative_test(repo_path)
            if not step3_result["success"]:
                self.results["failed_repos"][repo_name]["status"] = "FAIL_STEP3"
                self.results["failed_repos"][repo_name]["errors"]["step3"] = step3_result["error"]
                return
            
            self.results["step3_success"] += 1
        
        finally:
            # Clean up virtual environment for this repository
            if repo_name in self.venv_dirs and os.path.exists(self.venv_dirs[repo_name]):
                logger.info(f"Cleaning up virtual environment for {repo_name}")
                shutil.rmtree(self.venv_dirs[repo_name], ignore_errors=True)

    def _step1_dependency_check(self, repo_path):
        """Install dependencies from requirements.txt and check for errors."""
        logger.info("STEP 1: Checking dependencies...")
        original_dir = os.getcwd()
        repo_name = repo_path.name
        
        req_file = repo_path / "base" / "requirements.txt"
        if not req_file.exists():
            logger.error(f"requirements.txt not found in {repo_path}/base/")
            return {"success": False, "error": "requirements.txt not found"}
        
        # Create a virtual environment for this repository
        venv_dir = tempfile.mkdtemp(prefix=f"venv_{repo_name}_")
        self.venv_dirs[repo_name] = venv_dir
        
        try:
            # Create virtual environment
            logger.info(f"Creating virtual environment at {venv_dir}")
            venv_cmd = [sys.executable, "-m", "venv", venv_dir]
            proc = subprocess.run(venv_cmd, capture_output=True, text=True)
            if proc.returncode != 0:
                return {"success": False, "error": f"Failed to create virtual environment: {proc.stderr}"}
            
            # Determine pip path
            pip_path = os.path.join(venv_dir, "bin", "pip") if not sys.platform.startswith("win") else os.path.join(venv_dir, "Scripts", "pip.exe")
            
            # Install dependencies
            logger.info(f"Installing dependencies from {req_file}")
            pip_cmd = [pip_path, "install", "-r", str(req_file)]
            proc = subprocess.run(pip_cmd, capture_output=True, text=True)
            
            if proc.returncode != 0:
                logger.error(f"Dependency installation failed: {proc.stderr}")
                return {"success": False, "error": proc.stderr}
            
            # Also install unittest (just in case)
            pip_cmd = [pip_path, "install", "unittest2"]
            subprocess.run(pip_cmd, capture_output=True, text=True)
            
            logger.info("Dependency check successful")
            return {"success": True}
        
        except Exception as e:
            logger.error(f"Error in dependency check: {str(e)}")
            return {"success": False, "error": str(e)}
        
        finally:
            # Make sure we return to the original directory
            if os.getcwd() != original_dir:
                os.chdir(original_dir)

    def _step2_positive_test(self, repo_path):
        """Run answer/test_feature*.py files and verify all features pass with answer/codebase.py."""
        logger.info("STEP 2: Running positive tests...")
        
        all_tests_passed = True
        test_errors = {}
        original_dir = os.getcwd()
        repo_name = repo_path.name
        
        try:
            # Change to the answer directory using absolute path
            answer_dir = os.path.abspath(str(repo_path / "answer"))
            if not os.path.exists(answer_dir):
                logger.error(f"Answer directory not found: {answer_dir}")
                return {"success": False, "error": "Answer directory not found"}
                
            os.chdir(answer_dir)
            logger.info(f"Changed to directory: {answer_dir}")
            
            any_tests_found = False
            for test_file_name in self.test_files:
                test_file = repo_path / "answer" / test_file_name
                
                if not test_file.exists():
                    logger.warning(f"Test file not found: {test_file}")
                    continue
                    
                any_tests_found = True
                logger.info(f"Running positive test: {test_file_name}")
                test_result = self._run_unittest(str(test_file), repo_name)
                
                # Store individual test results
                self.results["failed_repos"][repo_path.name]["test_results"]["positive"][test_file_name] = {
                    "success": test_result["success"]
                }
                
                if test_result["success"]:
                    logger.info(f"Positive test {test_file_name} passed successfully")
                else:
                    all_tests_passed = False
                    error_msg = test_result["error"]
                    test_errors[test_file_name] = error_msg
                    logger.error(f"Positive test {test_file_name} failed: {error_msg}")
            
            if not any_tests_found:
                logger.error("No test files were found in the answer directory")
                return {"success": False, "error": "No test files found"}
                
            if all_tests_passed and any_tests_found:
                logger.info("All positive tests passed successfully")
                return {"success": True}
            else:
                return {"success": False, "error": test_errors}
        
        except Exception as e:
            logger.error(f"Error running positive tests: {str(e)}")
            return {"success": False, "error": {"general": str(e)}}
        
        finally:
            # Return to the original directory
            os.chdir(original_dir)
            logger.debug(f"Changed back to directory: {original_dir}")

    def _step3_negative_test(self, repo_path):
        """
        Copy answer/test_feature*.py files to base/ directory, 
        then verify features fail with base/codebase.py.
        """
        logger.info("STEP 3: Running negative tests...")
        
        all_tests_failed_as_expected = True
        test_errors = {}
        original_dir = os.getcwd()
        copied_files = []
        repo_name = repo_path.name
        
        try:
            any_tests_found = False
            for test_file_name in self.test_files:
                answer_test_file = repo_path / "answer" / test_file_name
                base_test_file = repo_path / "base" / test_file_name
                
                if not answer_test_file.exists():
                    logger.warning(f"Test file not found: {answer_test_file}")
                    continue
                    
                any_tests_found = True
                
                # Copy the test file to base directory
                shutil.copy2(str(answer_test_file), str(base_test_file))
                copied_files.append(base_test_file)
                
                # Run the tests in base directory and expect them to fail
                try:
                    # Change to the base directory using absolute path
                    base_dir = os.path.abspath(str(repo_path / "base"))
                    if not os.path.exists(base_dir):
                        logger.error(f"Base directory not found: {base_dir}")
                        return {"success": False, "error": "Base directory not found"}
                        
                    os.chdir(base_dir)
                    logger.info(f"Changed to directory: {base_dir}")
                    
                    logger.info(f"Running negative test: {test_file_name}")
                    test_result = self._run_unittest(str(base_test_file), repo_name)
                    
                    # Store individual test results
                    self.results["failed_repos"][repo_path.name]["test_results"]["negative"][test_file_name] = {
                        "success": not test_result["success"]  # For negative tests, success means the test failed
                    }
                    
                    # For negative tests, we expect them to fail
                    if test_result["success"]:
                        all_tests_failed_as_expected = False
                        test_errors[test_file_name] = "Test unexpectedly passed (should fail)"
                        logger.error(f"Negative test {test_file_name} unexpectedly passed (it should fail)")
                    else:
                        logger.info(f"Negative test {test_file_name} failed as expected")
                
                finally:
                    # Return to the original directory after each test
                    os.chdir(original_dir)
            
            if not any_tests_found:
                logger.error("No test files were found in the answer directory for negative testing")
                return {"success": False, "error": "No test files found"}
                
            if all_tests_failed_as_expected and any_tests_found:
                logger.info("All negative tests failed as expected")
                return {"success": True}
            else:
                return {"success": False, "error": test_errors}
        
        except Exception as e:
            logger.error(f"Error running negative tests: {str(e)}")
            return {"success": False, "error": {"general": str(e)}}
        
        finally:
            # Clean up the copied test files
            for file_path in copied_files:
                if file_path.exists():
                    file_path.unlink()
                    
            # Make sure we're back in the original directory
            if os.getcwd() != original_dir:
                os.chdir(original_dir)
                logger.debug(f"Changed back to directory: {original_dir}")

    def _run_unittest(self, test_file_path, repo_name=None):
        """Run unittest on the given test file, using the virtual environment if available."""
        if repo_name and repo_name in self.venv_dirs:
            # Get the path to the Python interpreter in the virtual environment
            if sys.platform.startswith("win"):
                python_path = os.path.join(self.venv_dirs[repo_name], "Scripts", "python.exe")
            else:
                python_path = os.path.join(self.venv_dirs[repo_name], "bin", "python")
            
            logger.info(f"Running test with virtual environment: {python_path}")
            cmd = [python_path, test_file_path]
        else:
            logger.info(f"Running test with system Python: {sys.executable}")
            cmd = [sys.executable, test_file_path]
        
        proc = subprocess.run(cmd, capture_output=True, text=True)
        
        if proc.returncode == 0:
            return {"success": True}
        else:
            return {"success": False, "error": proc.stderr or proc.stdout}

    def _summarize_results(self):
        """Summarize the validation results."""
        total = self.results["total_repos"]
        if total == 0:
            logger.warning("No repositories were validated.")
            return
        
        step1_pct = (self.results["step1_success"] / total) * 100
        step2_pct = (self.results["step2_success"] / total) * 100
        step3_pct = (self.results["step3_success"] / total) * 100
        
        logger.info("\n\n" + "="*50)
        logger.info("VALIDATION SUMMARY")
        logger.info("="*50)
        logger.info(f"Total repositories validated: {total}")
        logger.info(f"Step 1 (Dependency Check) success rate: {step1_pct:.2f}% ({self.results['step1_success']}/{total})")
        logger.info(f"Step 2 (Positive Test) success rate: {step2_pct:.2f}% ({self.results['step2_success']}/{total})")
        logger.info(f"Step 3 (Negative Test) success rate: {step3_pct:.2f}% ({self.results['step3_success']}/{total})")
        logger.info(f"Repositories that passed all checks: {self.results['step3_success']}/{total} ({step3_pct:.2f}%)")
        
        # Save detailed results to JSON
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        with open(f"validation_results_{timestamp}.json", "w") as f:
            json.dump(self.results, f, indent=4)
        
        logger.info(f"Detailed results saved to validation_results_{timestamp}.json")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        base_dir = sys.argv[1]
    else:
        base_dir = "."
    
    base_dir = "./clean_task_claude-3-7-sonnet@20250219"
    
    # Check if custom test file names are provided as additional arguments
    if len(sys.argv) > 2:
        validator = RepositoryValidator(base_dir)
        validator.test_files = sys.argv[2:]
        logger.info(f"Using custom test files: {validator.test_files}")
    else:
        validator = RepositoryValidator(base_dir)
        logger.info(f"Using default test files: {validator.test_files}")
    
    validator.validate_all_repositories()