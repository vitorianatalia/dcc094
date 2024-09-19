import os
import re
import sys
import time
from collections import defaultdict
from github import Github

# Configurações
max_commits_to_process = 200  # Número máximo de commits a serem processados
qualitative_commits_count = 10  # Número de commits para análise qualitativa

access_token = os.getenv('ACCESS_TOKEN')
g = Github(access_token)

def get_refactor_keywords():
    """Retorna uma lista de palavras-chave relacionadas a refatorações."""
    return [
        r'\brefactor\b', r'\bextract method\b', r'\bmove method\b', 
        r'\bmove attribute\b', r'\bcleanup\b', r'\breorganize\b'
    ]

def check_commit(commit, repo_path):
    """Verifica se um commit possui refatorações de código, analisando a mensagem e o diff."""
    changed_files = commit.stats.files
    diffs = commit.diff(commit.parents[0]) if commit.parents else []
    
    refactor_related_files = []
    for diff in diffs:
        patch = diff.diff.decode('utf-8', errors='ignore') if diff.diff else ""
        if contains_refactor_code(patch):
            refactor_related_files.append({
                'filename': diff.b_path,
                'changes': changed_files.get(diff.b_path, {}).get('lines', 0),
                'patch': patch
            })

    if refactor_related_files:
        return {
            'commit_sha': commit.hexsha,
            'message': commit.message,
            'files': refactor_related_files,
            'related_to_refactor': True
        }
    
    return {
        'commit_sha': commit.hexsha,
        'message': commit.message,
        'files': [],
        'related_to_refactor': False
    }

def contains_refactor_code(patch):
    """Verifica se um patch contém código relacionado a refatorações."""
    refactor_patterns = get_refactor_keywords()
    return any(re.search(pattern, patch, re.IGNORECASE) for pattern in refactor_patterns)

def process_commits(repo, max_commits_to_process):
    """Processa os commits do repositório para identificar refatorações."""
    commits = list(repo.iter_commits())
    commit_messages = []
    qualitative_commits = []
    total_commits = len(commits)

    refactor_related_commit_count = 0  
    analyzed_commits = 0
    author_commit_count = defaultdict(int)

    for commit in commits:
        if analyzed_commits >= max_commits_to_process:
            break

        commit_details = check_commit(commit, repo.working_tree_dir)
        analyzed_commits += 1

        if commit_details:
            commit_messages.append(commit_details)
        if commit_details['related_to_refactor']:
            refactor_related_commit_count += 1

        author = commit.author.name or "Unknown"
        author_commit_count[author] += 1  

        if len(qualitative_commits) < qualitative_commits_count:
            qualitative_commits.append(commit_details)

        progress = (analyzed_commits / max_commits_to_process) * 100
        print(f"\rCommit analysis progress: {progress:.2f}%", end="")

        if analyzed_commits % 100 == 0:
            print("\nPausando por 10 segundos para evitar sobrecarga.")
            time.sleep(10)

    top_contributors = sorted(author_commit_count.items(), key=lambda x: x[1], reverse=True)[:10]

    return commit_messages, qualitative_commits, total_commits, top_contributors, refactor_related_commit_count

def generate_report(commit_messages, output_file, total_commits, top_contributors, refactor_related_commit_count):
    """Gera um relatório resumido dos commits relacionados a refatorações."""
    with open(output_file, 'w') as file:
        file.write("====================================\n")
        file.write("       Relatório de Refatorações\n")
        file.write("====================================\n")
        
        file.write(f"\nTotal de Commits no Repositório: {total_commits}\n")
        file.write(f"Total de Commits Processados: {len(commit_messages)}\n")
        file.write(f"Commits Relacionados a Refatorações: {refactor_related_commit_count}\n")
        
        file.write("\nTop 10 Contribuidores de Refatorações:\n")
        file.write("--------------------------------------------\n")
        for author, count in top_contributors:
            file.write(f" - {author}: {count} commits relacionados a refatorações\n")
        
        file.write("\nCommits de Refatoração:\n")
        file.write("-----------------------\n")
        for commit_info in commit_messages:
            file.write(f"SHA do Commit: {commit_info['commit_sha']}\n")
            file.write(f"Mensagem: {commit_info['message']}\n")
            file.write("Arquivos Modificados:\n")
            for file_detail in commit_info['files']:
                file.write(f"  - {file_detail['filename']}: {file_detail['changes']} alterações\n")
            file.write("--------------------------------------------------\n")

def generate_qualitative_report(qualitative_commits, output_file):
    """Gera um relatório qualitativo detalhado dos commits analisados."""
    with open(output_file, 'a') as file:
        file.write("\n\n====================================\n")
        file.write("     Análise Qualitativa de Commits\n")
        file.write("====================================\n")
        
        for commit_info in qualitative_commits:
            file.write(f"SHA do Commit: {commit_info['commit_sha']}\n")
            file.write(f"Mensagem do Commit: {commit_info['message']}\n")
            file.write(f"Relacionado a Refatorações: {'Sim' if commit_info['related_to_refactor'] else 'Não'}\n")
            file.write("Arquivos Modificados:\n")
            for file_detail in commit_info['files']:
                file.write(f"  - {file_detail['filename']}: {file_detail['changes']} alterações\n")
            file.write("--------------------------------------------------\n")

def main():
    repo_path = "Rockeseat/umbriel"  # Modifique para o caminho do repositório local
    print('alo')
    repo = g.get_repo(repo_path)
    
    output_file = "refactor_changes_report.txt"
    
    commit_messages, qualitative_commits, total_commits, top_contributors, refactor_related_commit_count = process_commits(repo, max_commits_to_process)

    print("Gerando relatório final... aguarde.")
    generate_report(commit_messages, output_file, total_commits, top_contributors, refactor_related_commit_count)
    generate_qualitative_report(qualitative_commits, output_file)
    print("Relatório finalizado.")

if __name__ == "_main_":
    main()