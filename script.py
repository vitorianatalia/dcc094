import os
from github import Github
from dotenv import load_dotenv

load_dotenv()
access_token = os.getenv('ACCESS_TOKEN')

g = Github(access_token)

repo = g.get_repo("Rocketseat/umbriel")
commits = repo.get_commits()

def check_commit(commit_sha):
    commit = repo.get_commit(commit_sha)
    changed_files = commit.files

    # Print the files changed
    result = []
    for file in changed_files:
        result.append({'filename': file.filename, 'status': file.status, 'changes': file.changes, 'patch': file.patch})
    
    return result

# Print commit messages containing specific keywords
keywords = ["test", "teste", "tests"]
for commit in commits:
    if any(keyword in commit.commit.message for keyword in keywords):
        print(commit.commit.message)
        commit_sha = commit.sha
        commit_details = check_commit(commit_sha)
        for commit in commit_details:
            print(commit.get('filename'))

# Arquivos de configuração podem ter sido alterados em commits sem a palavra test    

# Change in specific config files
config_files = ["karma.conf.js", "jest.config.js", "pytest.ini", "testng.xml"]

# Initialize the contents list with the root directory
contents = repo.get_contents("")

# To store all found configuration files
found_files_set = set()

while contents:
    file_content = contents.pop(0)
    if file_content.type == "dir":
        contents.extend(repo.get_contents(file_content.path))
    else:
        file_path = file_content.path
        found_files = [config_file for config_file in config_files if config_file in file_path]
        found_files_set.update(found_files)

# Print all found configuration files
if found_files_set:
    print("Configuration files found:")
    for file in found_files_set:
        print(file)
else:
    print("No configuration files found.")

g.close()
