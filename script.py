import os

from github import Github
from github import Auth
from dotenv import load_dotenv

load_dotenv()
access_token = os.getenv('ACCESS_TOKEN')

g = Github(access_token)

repo = g.get_repo("Rocketseat/umbriel")
# repo.get_contents("")
commits = repo.get_commits()

for commit in commits:
    if "test" in commit.commit.message:
        print(commit.commit.message)
        print("------")
        print(commit.commit.author.date)
        print("-----------------------")


g.close()