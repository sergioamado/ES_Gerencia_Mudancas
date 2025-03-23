#baixa as issues para um arquivo csv
# -*- coding: utf-8 -*-
# issues_fechadas.csv

import requests
import csv
import logging
import time
import os

# Configurações
GITHUB_REPO = "twbs/bootstrap"  # Substitua pelo repositório desejado
MAX_ISSUES = 4000  # Número máximo de issues a serem buscadas
HEADERS = {}

def carregar_token():
    """Carrega o token do GitHub a partir do arquivo github_token.txt."""
    try:
        with open('github_token.txt', 'r') as file:
            return file.read().strip()
    except FileNotFoundError:
        logging.error("Error: github_token.txt file not found.")
        return None
    except Exception as e:
        logging.error(f"Erro inesperado ao carregar o token: {e}")
        return None

def verificar_limite(response):
    """Verifica o limite de requisições da API e aguarda se necessário."""
    remaining = int(response.headers.get('X-RateLimit-Remaining', 1))
    reset_time = int(response.headers.get('X-RateLimit-Reset', int(time.time()))) # Use int(time.time()) as default
    if remaining == 0:
        wait_time = reset_time - int(time.time())
        if wait_time > 0:
            logging.warning(f"Rate limit reached. Waiting for {wait_time} seconds...")
            time.sleep(wait_time + 1)  # Aguarda até o limite ser resetado

def fetch_issues():
    """Fetch all issues from a GitHub repository using the GitHub API."""
    all_issues = []
    page = 1
    per_page = 100  # Number of issues per page

    while len(all_issues) < MAX_ISSUES:
        url = f"https://api.github.com/repos/{GITHUB_REPO}/issues?state=closed&per_page={per_page}&page={page}"
        try:
            response = requests.get(url, headers=HEADERS)
            response.raise_for_status()  # Lança uma exceção para status de erro
        except requests.exceptions.RequestException as e:
            logging.error(f"Error fetching issues (page {page}): {e}")
            break

        verificar_limite(response)  # Verifica o limite de requisições

        if response.status_code == 200:
            issues = response.json()
            if not issues:  # Stop if the page is empty
                break
            all_issues.extend(issues)
            logging.info(f"Issues fetched from page {page}")
            page += 1
        else:
            logging.error(f"Error fetching issues (page {page}): {response.status_code}")
            break

    return all_issues[:MAX_ISSUES]  # Return up to MAX_ISSUES issues

def fetch_comments(issue_number):
    """Fetch all comments for a specific issue."""
    url = f"https://api.github.com/repos/{GITHUB_REPO}/issues/{issue_number}/comments"
    try:
        response = requests.get(url, headers=HEADERS)
        response.raise_for_status()  # Lança uma exceção para status de erro
    except requests.exceptions.RequestException as e:
        logging.error(f"Error fetching comments for issue {issue_number}: {e}")
        return []

    verificar_limite(response)  # Verifica o limite de requisições

    if response.status_code == 200:
        return response.json()
    else:
        logging.error(f"Error fetching comments for issue {issue_number}: {response.status_code}")
        return []

def save_issues_to_csv(issues, csv_file):
    """Save issues to a CSV file."""
    try:
        with open(csv_file, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(['Title', 'Body', 'All Comments', 'Created At', 'Closed At', 'Authors'])  # Header in English

            for issue in issues:
                # Filter out issues created by bots
                issue_author = issue.get('user', {}).get('login', 'N/A')
                if '[bot]' in issue_author or '-bot' in issue_author:
                    continue

                issue_number = issue.get('number', 'N/A')
                title = issue.get('title', 'N/A')
                body = issue.get('body', 'N/A')
                created_at = issue.get('created_at', 'N/A')
                closed_at = issue.get('closed_at', 'N/A')

                # Fetch comments for the issue
                comments = fetch_comments(issue_number)
                all_comments = []
                comment_authors = set()

                for comment in comments:
                    all_comments.append(comment.get('body', ''))
                    comment_authors.add(comment.get('user', {}).get('login', 'N/A'))

                # Add the issue author to the list of authors
                comment_authors.add(issue_author)

                writer.writerow([
                    title,
                    body,
                    " | ".join(all_comments),  # Comments separated by " | "
                    created_at,
                    closed_at,
                    ", ".join(comment_authors)  # Authors separated by commas
                ])

        logging.info(f"Issues saved to file {csv_file}")
    except Exception as e:
        logging.error(f"Erro ao salvar as issues no arquivo CSV: {e}")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s') # Added format

    # Load the GitHub token
    token = carregar_token()
    if not token:
        exit(1)

    # Configure the authentication header
    HEADERS = {
        'Authorization': f'token {token}'
    }

    # Fetch issues and save to CSV
    issues = fetch_issues()
    if issues: # Only save if issues were successfully fetched
        save_issues_to_csv(issues, 'issues_fechadas.csv')
    else:
        logging.warning("No issues fetched, CSV not saved.")