import requests
import csv
import os
import time

# Configurações
OWNER = "twbs"  # Dono do repositório (Twitter Bootstrap)
REPO = "bootstrap"  # Nome do repositório
CSV_FILENAME = "closed_issues.csv"  # Nome do arquivo CSV de saída
NUM_ISSUES = 5000  # Número de issues a serem baixadas
ISSUES_PER_PAGE = 100  # Número máximo permitido pela API do GitHub
DELAY_SECONDS = 1  # Tempo de espera entre as requisições (para evitar rate limiting)


def get_github_token():
    """Lê o token do GitHub do arquivo github_token.txt."""
    try:
        with open("github_token.txt", "r") as f:
            return f.read().strip()
    except FileNotFoundError:
        print("Erro: Arquivo 'github_token.txt' não encontrado.")
        return None


def get_closed_issues(owner, repo, github_token, num_issues, issues_per_page=100):
    """
    Baixa as issues fechadas do repositório especificado.

    Args:
        owner: Dono do repositório (ex: "twbs").
        repo: Nome do repositório (ex: "bootstrap").
        github_token: Token de autenticação do GitHub.
        num_issues: Número total de issues a serem baixadas.
        issues_per_page: Número de issues por página (máximo 100).

    Returns:
        Uma lista de dicionários, onde cada dicionário representa uma issue.
        Retorna None em caso de erro.
    """

    issues = []
    page = 1
    while len(issues) < num_issues:
        url = f"https://api.github.com/repos/{owner}/{repo}/issues"
        params = {
            "state": "closed",
            "per_page": issues_per_page,
            "page": page,
            "sort": "created",  # Ordena por data de criação (mais antigas primeiro)
            "direction": "asc"  # Ordem ascendente (mais antigas primeiro)
        }
        headers = {"Authorization": f"token {github_token}"}

        try:
            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()  # Lança uma exceção para códigos de erro HTTP
            data = response.json()

            if not data:
                print("Nenhuma issue encontrada nesta página. Saindo.")
                break

            for issue_data in data:
                issues.append({
                    "number": issue_data["number"],
                    "title": issue_data["title"],
                    "user": issue_data["user"]["login"],
                    "created_at": issue_data["created_at"],
                    "closed_at": issue_data["closed_at"],
                    "url": issue_data["html_url"],
                    "body": issue_data["body"]
                })

            print(f"Baixadas {len(issues)} issues...")
            page += 1
            time.sleep(DELAY_SECONDS)  # Espera para evitar rate limiting

        except requests.exceptions.RequestException as e:
            print(f"Erro ao fazer a requisição: {e}")
            return None  # Retorna None em caso de erro.
        except ValueError as e:
            print(f"Erro ao decodificar JSON: {e}")
            return None  # Retorna None em caso de erro.

    return issues[:num_issues]  # Retorna apenas o número solicitado de issues.


def save_issues_to_csv(issues, filename):
    """Salva as issues em um arquivo CSV."""
    if not issues:
        print("Nenhuma issue para salvar.")
        return

    try:
        with open(filename, "w", newline="", encoding="utf-8") as csvfile:
            fieldnames = ["number", "title", "user", "created_at", "closed_at", "url", "body"]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

            writer.writeheader()
            for issue in issues:
                writer.writerow(issue)

        print(f"Issues salvas em {filename}")

    except Exception as e:
        print(f"Erro ao salvar o arquivo CSV: {e}")


def main():
    """Função principal."""
    github_token = get_github_token()
    if not github_token:
        return  # Sai se o token não foi encontrado

    print("Iniciando a coleta de issues fechadas...")
    issues = get_closed_issues(OWNER, REPO, github_token, NUM_ISSUES, ISSUES_PER_PAGE)

    if issues:
        save_issues_to_csv(issues, CSV_FILENAME)
    else:
        print("Falha ao obter as issues.")


if __name__ == "__main__":
    main()