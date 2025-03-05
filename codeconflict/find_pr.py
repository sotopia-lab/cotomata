import requests
import time
import json
from datetime import datetime
import os
from collections import defaultdict

class GitHubPRAnalyzer:
    def __init__(self, repo_owner, repo_name, token=None):
        """
        Initialize the GitHub PR analyzer.
        
        Args:
            repo_owner (str): Owner of the repository (e.g., 'astropy')
            repo_name (str): Name of the repository (e.g., 'astropy')
            token (str, optional): GitHub personal access token for API authentication
        """
        self.repo_owner = repo_owner
        self.repo_name = repo_name
        self.base_url = f"https://api.github.com/repos/{repo_owner}/{repo_name}"
        self.headers = {}
        
        if token:
            self.headers["Authorization"] = f"token {token}"
        
        # Add headers to identify the script
        self.headers["Accept"] = "application/vnd.github.v3+json"
        self.headers["User-Agent"] = "GitHub-PR-Analyzer"
        
        # Cache for PR data
        self.pr_cache = {}
        # Cache for file changes
        self.file_changes_cache = {}
    
    def check_rate_limit(self):
        """
        Check the current GitHub API rate limit status.
        
        Returns:
            tuple: (remaining requests, reset time in seconds)
        """
        url = "https://api.github.com/rate_limit"
        response = requests.get(url, headers=self.headers)
        
        if response.status_code != 200:
            return (0, 3600)  # Default to 0 remaining and 1 hour reset
            
        data = response.json()
        remaining = data["rate"]["remaining"]
        reset_time = data["rate"]["reset"]
        current_time = int(time.time())
        seconds_to_reset = max(0, reset_time - current_time)
        
        return (remaining, seconds_to_reset)
    
    def handle_rate_limit(self):
        """
        Check and handle rate limit by waiting if necessary.
        
        Returns:
            bool: True if we can proceed, False if we should abort
        """
        remaining, seconds_to_reset = self.check_rate_limit()
        
        if remaining <= 5:  # Keep a small buffer
            if seconds_to_reset > 0:
                wait_minutes = seconds_to_reset / 60
                print(f"Rate limit nearly exhausted. Reset in {wait_minutes:.1f} minutes.")
                
                if seconds_to_reset > 600:  # If more than 10 minutes
                    print("Rate limit reset time too long. Consider adding a GitHub token.")
                    if input("Continue anyway? (y/n): ").lower() != 'y':
                        return False
                else:
                    print(f"Waiting {seconds_to_reset} seconds for rate limit to reset...")
                    time.sleep(seconds_to_reset + 5)  # Add 5 seconds as buffer
                    print("Continuing after rate limit reset")
                    
        return True
        
    def get_pull_requests(self, state="closed", max_pages=10, per_page=100):
        """
        Fetch pull requests from the repository.
        
        Args:
            state (str): PR state ('open', 'closed', or 'all')
            max_pages (int): Maximum number of pages to fetch
            per_page (int): Number of PRs per page
            
        Returns:
            list: List of pull request data
        """
        all_prs = []
        url = f"{self.base_url}/pulls"
        params = {
            "state": state,
            "per_page": per_page,
            "sort": "created",
            "direction": "desc"
        }
        
        # Check rate limit before starting
        if not self.handle_rate_limit():
            print("Aborting due to rate limit concerns")
            return all_prs
            
        for page in range(1, max_pages + 1):
            params["page"] = page
            response = requests.get(url, headers=self.headers, params=params)
            
            if response.status_code == 403 and "rate limit exceeded" in response.text.lower():
                print("Rate limit exceeded during PR fetching")
                if not self.handle_rate_limit():
                    break
                # Try again after handling rate limit
                response = requests.get(url, headers=self.headers, params=params)
                
            if response.status_code != 200:
                print(f"Error fetching PRs: {response.status_code}")
                print(response.text)
                break
                
            prs_page = response.json()
            if not prs_page:
                break
                
            all_prs.extend(prs_page)
            print(f"Fetched page {page} with {len(prs_page)} PRs. Total PRs: {len(all_prs)}")
            
            # Check if we've reached the last page
            if len(prs_page) < per_page:
                break
                
            # Respect GitHub's rate limits
            time.sleep(1)
        
        # Store PRs in cache
        for pr in all_prs:
            self.pr_cache[pr["number"]] = pr
            
        return all_prs
    
    def get_pr_files(self, pr_number):
        """
        Get the files modified in a specific PR.
        
        Args:
            pr_number (int): Pull request number
            
        Returns:
            list: List of file data including filename and patch
        """
        # Check cache first
        if pr_number in self.file_changes_cache:
            return self.file_changes_cache[pr_number]
            
        url = f"{self.base_url}/pulls/{pr_number}/files"
        all_files = []
        page = 1
        
        while True:
            # Check rate limit before making the request
            if page % 10 == 1:  # Check every 10 pages
                if not self.handle_rate_limit():
                    print(f"Aborting file fetch for PR #{pr_number} due to rate limit")
                    return []
            
            params = {"page": page, "per_page": 100}
            response = requests.get(url, headers=self.headers, params=params)
            
            if response.status_code == 403 and "rate limit exceeded" in response.text.lower():
                print(f"Rate limit exceeded while fetching files for PR #{pr_number}")
                if not self.handle_rate_limit():
                    return []
                # Try again after handling rate limit
                response = requests.get(url, headers=self.headers, params=params)
            
            if response.status_code != 200:
                print(f"Error fetching PR files for PR #{pr_number}: {response.status_code}")
                print(response.text)
                return []
                
            files_page = response.json()
            if not files_page:
                break
                
            all_files.extend(files_page)
            
            # Check if we've reached the last page
            if len(files_page) < 100:
                break
                
            page += 1
            time.sleep(0.5)  # Respect rate limits
        
        # Store in cache
        self.file_changes_cache[pr_number] = all_files
        return all_files

    
    def find_prs(self):
        """
        Find PRs in a specific repository.
            
        Returns:
            dict: Dict of PR pairs
        """
        # Get all PRs first
        print("Fetching pull requests...")
        prs = self.get_pull_requests(state="closed", max_pages=1)
        
        # Sort PRs by merged_at date (most recent first)
        merged_prs = [pr for pr in prs if pr.get("merged_at")]
        merged_prs.sort(key=lambda x: x.get("merged_at", ""), reverse=True)
        
        print(f"Analyzing {len(merged_prs)} merged PRs...")
        
        # File to PR mapping for quick lookup
        file_to_prs = defaultdict(list)
        pr_information = {}
        
        # Get file changes for each PR and store with merge timestamp for chronological ordering
        for pr in merged_prs:
            pr_number = pr["number"]
            merged_at = datetime.fromisoformat(pr.get("merged_at").replace('Z', '+00:00')) if pr.get("merged_at") else None
            
            if not merged_at:
                continue
                
            files = self.get_pr_files(pr_number)
            
            name = f"{self.repo_owner}__{self.repo_name}_{pr_number}"
            pr_information[name] = {}
            del pr["requested_reviewers"]
            del pr["requested_teams"]
            del pr["labels"]
            del pr["milestone"]
            del pr["head"]
            del pr["base"]
            pr_information[name]["pr"] = pr
            pr_information[name]["files"] = files
        
        with open(f"pr_information_{self.repo_owner}__{self.repo_name}.json", "w") as f:
            f.write(json.dumps(pr_information, indent=4))


def main():
    # GitHub personal access token (if available)
    token = os.environ.get("GITHUB_TOKEN")
    
    # Direct token input option
    if not token:
        print("No GitHub token found in environment variables.")
        use_manual_token = input("Would you like to enter a token manually? (y/n): ").lower() == 'y'
        if use_manual_token:
            token = input("Enter your GitHub token: ").strip()
    
    # Initialize analyzer for astropy/astropy
    analyzer = GitHubPRAnalyzer("astropy", "astropy", token)
    
    analyzer.find_prs()
    

if __name__ == "__main__":
    main()