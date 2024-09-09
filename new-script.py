import os
import re
import sys
import time
from collections import defaultdict
from github import Github
from dotenv import load_dotenv
from github.GithubException import RateLimitExceededException

# Load environment variables
load_dotenv()
access_token = os.getenv('ACCESS_TOKEN')

# Initialize GitHub client
g = Github(access_token)
repo = g.get_repo("nodejs/node")

# Configuration
max_files_to_check = 5000  
max_depth = 6  
max_commits_to_process = 200  
qualitative_commits_count = 10  # Number of commits for qualitative analysis

def get_keywords():
    """Returns a list of keywords related to testing."""
    return [
        r'\btest(s)?\b', r'\bteste\b', r'\btest cases?\b', r'\badd(ed)? test\b', 
        r'\bupdate(d)? test\b', r'\bremove(d)? test\b', r'\bfix\b', r'\bassert\b', r'\bintegration\b'
    ]

def check_commit(commit_sha, repo, test_files_set):
    """Check the details of a specific commit, focusing on test-related changes, with retries."""
    retries = 3
    for attempt in range(retries):
        try:
            commit = repo.get_commit(commit_sha)
            break  # If successful, break out of retry loop
        except RateLimitExceededException as e:
            print(f"Rate limit exceeded. Retrying in 60 seconds... ({attempt + 1}/{retries})")
            time.sleep(60)  # Wait before retrying
        except Exception as e:
            print(f"Error fetching commit {commit_sha}: {e}")
            return None  # Skip this commit after failed retries
    else:
        print(f"Failed to fetch commit {commit_sha} after {retries} attempts.")
        return None

    changed_files = commit.files
    result = []
    for file in changed_files:
        patch = file.patch or ""
        if file.filename in test_files_set or contains_test_code(patch):
            result.append({
                'filename': file.filename,
                'status': file.status,
                'changes': file.changes,
                'patch': patch
            })
    
    if result:
        return {
            'commit_sha': commit_sha,
            'message': commit.commit.message,
            'files': result,
            'related_to_tests': True,
            'objective': determine_commit_objective(commit.commit.message, changed_files)
        }

    return {
        'commit_sha': commit_sha,
        'message': commit.commit.message,
        'files': [],
        'related_to_tests': False,
        'objective': "No test files involved"
    }

def contains_test_code(patch):
    """Check if a code patch contains test-related code."""
    if not isinstance(patch, str):
        return False
    test_code_patterns = [r'\bassert\b', r'\bexpect\b', r'\bit\(', r'\bdescribe\(', r'\btest\(', r'\bmock\(', r'\bspy\(']
    return any(re.search(pattern, patch, re.IGNORECASE) for pattern in test_code_patterns)

def determine_commit_objective(commit_message, changed_files):
    """Determine the objective of the commit based on its message and files changed."""
    if 'add test' in commit_message.lower():
        return 'Adding new test cases'
    elif 'update test' in commit_message.lower():
        return 'Updating existing test cases'
    elif 'remove test' in commit_message.lower():
        return 'Removing test cases'
    elif any(file.filename.lower().endswith(ext) for file in changed_files for ext in ['.test.js', '.spec.js', '.test.py', '.spec.py', '.feature']):
        return 'Changes in test files'
    return 'No specific test objective identified'

def find_test_files(repo):
    """Find files related to testing in specified directories with limits on file count and depth."""
    contents = repo.get_contents("")
    test_files_set = set()
    files_processed = 0
    directories_to_process = [("", 0)]  # Store (directory path, current depth)
    processed_directories = set()

    while directories_to_process and files_processed < max_files_to_check:
        current_dir, current_depth = directories_to_process.pop()
        if current_dir in processed_directories or current_depth > max_depth:
            continue
        processed_directories.add(current_dir)

        try:
            current_contents = repo.get_contents(current_dir)
        except Exception as e:
            print(f"Failed to get contents of {current_dir}: {e}")
            continue

        for file_content in current_contents:
            if file_content.type == "dir":
                if is_test_directory(file_content.path):
                    directories_to_process.append((file_content.path, current_depth + 1))
            else:
                if is_test_file(file_content.path):
                    test_files_set.add(file_content.path)
                    files_processed += 1

            # Print progress
            progress = (files_processed / max_files_to_check) * 100
            print(f"Scanning for test files... Progress: {progress:.2f}%", end="\r")

    return test_files_set

def is_test_file(filename):
    """Check if a file is related to testing based on its filename or extension."""
    test_extensions = [".test.js", ".spec.js", ".test.py", ".spec.py", ".feature", ".test.ts", ".spec.ts"]
    test_patterns = ["test", "spec", "unittest", "integration", "e2e", "fixture"]
    
    return filename.endswith(tuple(test_extensions)) or any(pattern in filename.lower() for pattern in test_patterns)

def is_test_directory(path):
    """Check if a directory path is related to testing."""
    test_directories = ["tests", "spec", "test", "unittests"]
    return any(dir in path.lower() for dir in test_directories)

def generate_report(test_files_set, output_file, commit_messages, total_commits, top_contributors, test_related_commit_count):
    """Generate a summary report of test-related commits and files."""
    with open(output_file, 'w') as file:
        file.write("====================================\n")
        file.write("         Test-Related Commits Report\n")
        file.write("====================================\n")

        file.write(f"\nTotal Commits in Repository: {total_commits}\n")  
        file.write(f"Total Commits Processed: {len(commit_messages)}\n")
        file.write(f"Test-Related Commits Found: {test_related_commit_count}\n")  

        file.write("\nTop 10 Contributors for Test-Related Commits:\n")
        file.write("--------------------------------------------\n")
        for author, count in top_contributors:
            file.write(f" - {author}: {count} commits related to tests\n")


        file.write("\nTest Files Found:\n")
        file.write("-----------------\n")
        for test_file in test_files_set:
            file.write(f" - {test_file}\n")
        
        file.write("\nTest-Related Commits:\n")
        file.write("---------------------\n")
        for commit_info in commit_messages:
            file.write(f"Commit SHA: {commit_info['commit_sha']}\n")
            file.write(f"Message: {commit_info['message']}\n")
            file.write("Files Altered:\n")
            for file_detail in commit_info['files']:
                file.write(f"  - {file_detail['filename']}: {file_detail['status']} ({file_detail['changes']} changes)\n")
            file.write("--------------------------------------------------\n")

def generate_qualitative_report(qualitative_commits, output_file):
    """Generate a detailed qualitative report of the top commits."""
    with open(output_file, 'a') as file:
        file.write("\n\n====================================\n")
        file.write("     Qualitative Analysis of Commits\n")
        file.write("====================================\n")
        
        for commit_info in qualitative_commits:
            commit_url = f"https://github.com/{repo.full_name}/commit/{commit_info['commit_sha']}"
            file.write(f"Commit SHA: {commit_info['commit_sha']}\n")
            file.write(f"Commit URL: {commit_url}\n")
            file.write(f"Commit Message: {commit_info['message']}\n")
            file.write(f"Related to Tests: {'Yes' if commit_info['related_to_tests'] else 'No'}\n")
            file.write(f"Objective: {commit_info['objective']}\n")
            file.write("Files Altered:\n")
            for file_detail in commit_info['files']:
                file.write(f"  - {file_detail['filename']}: {file_detail['status']} ({file_detail['changes']} changes)\n")
            file.write("--------------------------------------------------\n")

def process_commits(repo, test_files_set, max_commits_to_process):
    commit_messages = []
    qualitative_commits = []
    commits = repo.get_commits()
    total_commits = commits.totalCount

    test_related_commit_count = 0 

    analyzed_commits = 0
    author_commit_count = defaultdict(int)

    for commit in commits:
        if analyzed_commits >= max_commits_to_process:
            break

        commit_sha = commit.sha
        commit_details = check_commit(commit_sha, repo, test_files_set)

        if commit_details is not None and commit_details['related_to_tests']:
            commit_messages.append(commit_details)
            test_related_commit_count += 1

            author = commit.commit.author.name or "Unknown"
            author_commit_count[author] += 1  


            if len(qualitative_commits) < qualitative_commits_count:
                qualitative_commits.append(commit_details)

        analyzed_commits += 1
        progress = (analyzed_commits / max_commits_to_process) * 100
        
        # Clear the line before printing progress
        sys.stdout.write("\033[K")  # ANSI code to clear the line
        print(f"\rCommit analysis progress: {progress:.2f}%", end="")

        # Throttle the requests if processing too many commits quickly
        if analyzed_commits % 100 == 0:
            print("\nPausing for 10 seconds to avoid API rate limits...")
            time.sleep(10)

    # Ensure the progress ends with a clean line
    print()

    top_contributors = sorted(author_commit_count.items(), key=lambda x: x[1], reverse=True)[:10]


    return commit_messages, qualitative_commits, total_commits, top_contributors, test_related_commit_count

def main():
    output_file = "test_changes_report.txt"
    test_files_set = find_test_files(repo)
    
    commit_messages, qualitative_commits, total_commits, top_contributors, test_related_commit_count = process_commits(repo, test_files_set, max_commits_to_process)

    print("Generating final report... please wait.")
    generate_report(test_files_set, output_file, commit_messages, total_commits, top_contributors, test_related_commit_count)
    generate_qualitative_report(qualitative_commits, output_file)
    print("Final report completed.")

if __name__ == "__main__":
    main()

# Close the GitHub client
g.close()
