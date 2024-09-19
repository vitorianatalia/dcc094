import re
from git import Repo
from collections import defaultdict

# Configuration
max_commits_to_process = 200

def get_refactoring_keywords():
    """Returns a list of keywords related to refactoring."""
    return [
        r'\bextract method\b', r'\binline method\b', r'\brename method\b', r'\bmove method\b', 
        r'\bmove attribute\b', r'\bpull up method\b', r'\bpull up attribute\b', r'\bpush down method\b', 
        r'\bpush down attribute\b', r'\bextract superclass\b', r'\bextract interface\b', r'\bmove class\b', 
        r'\brename class\b', r'\bextract and move method\b', r'\brename package\b', r'\bmove and rename class\b', 
        r'\bextract class\b', r'\bextract subclass\b', r'\bextract variable\b', r'\binline variable\b', 
        r'\bparameterize variable\b', r'\brename variable\b', r'\brename parameter\b', r'\brename attribute\b', 
        r'\bmove and rename attribute\b', r'\breplace variable with attribute\b', r'\breplace attribute\b', 
        r'\bmerge variable\b', r'\bmerge parameter\b', r'\bmerge attribute\b', r'\bsplit variable\b', 
        r'\bsplit parameter\b', r'\bsplit attribute\b', r'\bchange variable type\b', r'\bchange parameter type\b', 
        r'\bchange return type\b', r'\bchange attribute type\b', r'\bextract attribute\b', r'\bmove and rename method\b', 
        r'\bmove and inline method\b', r'\badd method annotation\b', r'\bremove method annotation\b', 
        r'\bmodify method annotation\b', r'\badd attribute annotation\b', r'\bremove attribute annotation\b', 
        r'\bmodify attribute annotation\b', r'\badd class annotation\b', r'\bremove class annotation\b', 
        r'\bmodify class annotation\b', r'\badd parameter annotation\b', r'\bremove parameter annotation\b', 
        r'\bmodify parameter annotation\b', r'\badd variable annotation\b', r'\bremove variable annotation\b', 
        r'\bmodify variable annotation\b', r'\badd parameter\b', r'\bremove parameter\b', r'\breorder parameter\b', 
        r'\badd thrown exception type\b', r'\bremove thrown exception type\b', r'\bchange thrown exception type\b', 
        r'\bchange method access modifier\b', r'\bchange attribute access modifier\b', r'\bencapsulate attribute\b', 
        r'\bparameterize attribute\b', r'\breplace attribute with variable\b', r'\badd method modifier\b', 
        r'\bremove method modifier\b', r'\badd attribute modifier\b', r'\bremove attribute modifier\b', 
        r'\badd variable modifier\b', r'\badd parameter modifier\b', r'\bremove variable modifier\b', 
        r'\bremove parameter modifier\b', r'\bchange class access modifier\b', r'\badd class modifier\b', 
        r'\bremove class modifier\b', r'\bmove package\b', r'\bsplit package\b', r'\bmerge package\b', 
        r'\blocalize parameter\b', r'\bchange type declaration kind\b', r'\bcollapse hierarchy\b', 
        r'\breplace loop with pipeline\b', r'\breplace anonymous with lambda\b', r'\bmerge class\b', 
        r'\binline attribute\b', r'\breplace pipeline with loop\b', r'\bsplit class\b', r'\bsplit conditional\b', 
        r'\binvert condition\b', r'\bmerge conditional\b', r'\bmerge catch\b', r'\bmerge method\b', 
        r'\bsplit method\b', r'\bmove code\b', r'\breplace anonymous with class\b', r'\bparameterize test\b', 
        r'\bassert throws\b', r'\breplace generic with diamond\b', r'\btry with resources\b', 
        r'\breplace conditional with ternary\b',r'\brefactor', r'\brefactoring', r'polishing', r'polish'
    ]

def contains_refactoring_keywords(message):
    """Check if a commit message contains refactoring-related keywords."""
    refactoring_patterns = get_refactoring_keywords()
    return any(re.search(pattern, message, re.IGNORECASE) for pattern in refactoring_patterns)

def process_commits_for_refactoring(repo, max_commits_to_process):
    """Process a number of commits and identify refactorings."""
    commit_refactorings = []
    commits = list(repo.iter_commits())
    total_commits = len(commits)

    analyzed_commits = 0
    author_refactoring_count = defaultdict(int)

    for commit in commits[:max_commits_to_process]:
        commit_message = commit.message.lower()
        if contains_refactoring_keywords(commit_message):
            refactoring_details = {
                'commit_sha': commit.hexsha,
                'message': commit.message,
                'author': commit.author.name,
                'date': commit.authored_datetime,
                'files': [file for file in commit.stats.files.keys()],
                'refactoring_detected': True
            }
            commit_refactorings.append(refactoring_details)
            author_refactoring_count[commit.author.name] += 1

        analyzed_commits += 1
        progress = (analyzed_commits / max_commits_to_process) * 100
        print(f"\rCommit analysis progress: {progress:.2f}%", end="")

    print()  # Ensure progress line is cleared

    top_refactoring_authors = sorted(author_refactoring_count.items(), key=lambda x: x[1], reverse=True)[:10]

    return commit_refactorings, total_commits, top_refactoring_authors

def generate_refactoring_report(commit_refactorings, total_commits, top_refactoring_authors, output_file):
    """Generate a summary report of refactorings."""
    with open(output_file, 'w', encoding='utf-8') as file:
        file.write("====================================\n")
        file.write("    Refactoring Commits Report\n")
        file.write("====================================\n")

        file.write(f"\nTotal Commits in Repository: {total_commits}\n")
        file.write(f"Total Refactoring Commits Detected: {len(commit_refactorings)}\n")

        file.write("\nTop 10 Contributors for Refactoring Commits:\n")
        file.write("--------------------------------------------\n")
        for author, count in top_refactoring_authors:
            file.write(f" - {author}: {count} refactoring commits\n")

        file.write("\nRefactoring Commits:\n")
        file.write("---------------------\n")
        for commit in commit_refactorings:
            file.write(f"Commit SHA: {commit['commit_sha']}\n")
            file.write(f"Message: {commit['message']}\n")
            file.write(f"Author: {commit['author']}\n")
            file.write(f"Date: {commit['date']}\n")
            file.write(f"Files Affected:\n")
            for file_detail in commit['files']:
                file.write(f"  - {file_detail}\n")
            file.write("--------------------------------------------------\n")

def main():
    repo_path = input("Enter the path to the local Git repository: ")
    output_file = "local_refactoring_report.txt"

    repo = Repo(repo_path)

    print("Processing commits for refactorings... this might take some time.")
    commit_refactorings, total_commits, top_refactoring_authors = process_commits_for_refactoring(repo, max_commits_to_process)

    print("Generating refactoring report... please wait.")
    generate_refactoring_report(commit_refactorings, total_commits, top_refactoring_authors, output_file)
    print("Refactoring report completed.")

if __name__ == "__main__":
    main()
