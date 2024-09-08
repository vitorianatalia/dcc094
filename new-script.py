import os
import re
from github import Github
from dotenv import load_dotenv
from collections import defaultdict

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
    return ["test", "teste", "tests", "add test", "update test", "remove test", "test case", "fixture"]

def check_commit(commit_sha, repo):
    """Check the details of a specific commit, focusing on test-related changes."""
    commit = repo.get_commit(commit_sha)
    changed_files = commit.files

    result = []
    for file in changed_files:
        patch = file.patch or ""
        if contains_test_code(patch):
            result.append({
                'filename': file.filename,
                'status': file.status,
                'changes': file.changes,
                'patch': patch
            })
    
    # Determine if the commit is related to tests
    commit_message = commit.commit.message
    related_to_tests = any(keyword in commit_message.lower() for keyword in get_keywords())
    objective = determine_commit_objective(commit_message, changed_files)
    
    return {
        'commit_sha': commit_sha,
        'message': commit_message,
        'files': result,
        'related_to_tests': related_to_tests,
        'objective': objective
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
    test_extensions = [".test.js", ".spec.js", ".test.py", ".spec.py", ".feature"]
    test_patterns = ["test", "spec", "unittest", "integration", "e2e"]
    
    return any(filename.endswith(ext) for ext in test_extensions) or any(pattern in filename.lower() for pattern in test_patterns)

def is_test_directory(path):
    """Check if a directory path is related to testing."""
    test_directories = ["tests", "spec", "test", "unittests"]
    return any(dir in path.lower() for dir in test_directories)

def generate_report(test_files_set, output_file, commit_messages):
    """Generate a summary report of test-related commits and files."""
    with open(output_file, 'w') as file:
        file.write("Test-Related Commits Report\n")
        file.write("------------------------------\n")
        
        file.write("\nTest files found:\n")
        for test_file in test_files_set:
            file.write(f" - {test_file}\n")
        
        file.write("\nTest-Related Commits:\n")
        for commit_info in commit_messages:
            file.write(f" - Commit: {commit_info['message']}\n")
            file.write(f"   Files altered:\n")
            for file_detail in commit_info['files']:
                file.write(f"     - {file_detail['filename']}: {file_detail['status']} with {file_detail['changes']} changes\n")
            file.write("------------------------------\n")

def generate_qualitative_report(qualitative_commits, output_file):
    """Generate a detailed qualitative report of the top commits."""
    with open(output_file, 'a') as file:
        file.write("\nQualitative Analysis of Commits\n")
        file.write("------------------------------\n")
        
        for commit_info in qualitative_commits:
            commit_url = f"https://github.com/{repo.full_name}/commit/{commit_info['commit_sha']}"
            file.write(f"Commit SHA: {commit_info['commit_sha']}\n")
            file.write(f"Commit URL: {commit_url}\n")
            file.write(f"Commit Message: {commit_info['message']}\n")
            file.write(f"Related to Tests: {'Yes' if commit_info['related_to_tests'] else 'No'}\n")
            file.write(f"Objective: {commit_info['objective']}\n")
            file.write("Files Altered:\n")
            for file_detail in commit_info['files']:
                file.write(f"  - {file_detail['filename']}: {file_detail['status']} with {file_detail['changes']} changes\n")
            file.write("------------------------------\n")

def main():
    output_file = "test_changes_report.txt"
    commit_messages = []
    qualitative_commits = []
    test_files_set = set()

    commits = repo.get_commits()
    total_commits = min(commits.totalCount, max_commits_to_process) if max_commits_to_process else commits.totalCount
    analyzed_commits = 0

    # Find all test files
    test_files_set = find_test_files(repo)

    for commit in commits:
        if analyzed_commits >= max_commits_to_process:
            break

        analyzed_commits += 1
        commit_sha = commit.sha
        commit_message = commit.commit.message
        
        commit_details = check_commit(commit_sha, repo)
        
        test_files_altered = [detail for detail in commit_details['files'] if detail['filename'] in test_files_set]
        
        if commit_details['related_to_tests']:
            commit_messages.append({
                'message': commit_message,
                'files': test_files_altered
            })

            if len(qualitative_commits) < qualitative_commits_count:
                qualitative_commits.append(commit_details)

        # Print progress
        progress = (analyzed_commits / total_commits) * 100
        print(f"\nCommit analysis progress: {progress:.2f}%", end="\r")

    print("\nGenerating final report... please wait.")
    generate_report(test_files_set, output_file, commit_messages)
    generate_qualitative_report(qualitative_commits, output_file)
    print("Final report completed.")

if __name__ == "__main__":
    main()

# Close the GitHub client
g.close()
