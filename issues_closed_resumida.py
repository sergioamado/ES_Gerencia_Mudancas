#artigo 1

import requests
import csv
import os
from datetime import datetime, timedelta

def get_github_token(token_file="github_token.txt"):
    """Lê o token do GitHub de um arquivo."""
    try:
        with open(token_file, "r") as f:
            token = f.read().strip()
            if not token:
                print(f"Aviso: O arquivo '{token_file}' está vazio.")
                return None
            return token
    except FileNotFoundError:
        print(f"Erro: Arquivo '{token_file}' não encontrado.")
        return None
    except Exception as e:
        print(f"Erro ao ler o token do arquivo: {e}")
        return None

def get_closed_issues(repo_owner, repo_name, github_token):
    """
    Obtém informações resumidas sobre as issues fechadas de um repositório no GitHub,
    incluindo as labels. Garante a extração dos campos desejados.
    """
    url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/issues"
    headers = {"Authorization": f"token {github_token}"}
    params = {"state": "closed", "per_page": 100}

    issues_data = []
    page = 1

    try:
        while True:
            params["page"] = page
            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()
            issues = response.json()

            if not issues:
                break

            for issue in issues:
                # Garante que os campos existam e atribui um valor padrão se não existirem
                number = issue.get("number", None)
                title = issue.get("title", None)
                user = issue.get("user", {}).get("login", None)  # Acessa o login do usuário com segurança
                created_at = issue.get("created_at", None)
                closed_at = issue.get("closed_at", None)

                # Extrai os nomes das labels
                labels = [label["name"] for label in issue.get("labels", [])]

                issues_data.append({
                    "number": number,
                    "title": title,
                    "user": user,
                    "created_at": created_at,
                    "closed_at": closed_at,
                    "labels": labels,
                })

            page += 1

        return issues_data

    except requests.exceptions.RequestException as e:
        print(f"Erro na requisição à API do GitHub: {e}")
        return None
    except Exception as e:
        print(f"Erro inesperado ao obter issues: {e}")
        return None

def save_issues_to_csv(issues_data, filename="issues_closed_resumida.csv"):
    """
    Salva os dados das issues, incluindo as labels, em um arquivo CSV.
    """
    if not issues_data:
        print("Nenhum dado de issue para salvar.")
        return

    try:
        with open(filename, "w", newline="", encoding="utf-8") as csvfile:
            fieldnames = ["number", "title", "user", "created_at", "closed_at", "labels"]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

            writer.writeheader()
            for issue in issues_data:
                # Converte a lista de labels para uma string para salvar no CSV
                issue["labels"] = ";".join(issue["labels"]) if issue["labels"] else ""  # Lida com o caso em que não há labels
                writer.writerow(issue)

        print(f"Dados das issues salvos em '{filename}'")

    except Exception as e:
        print(f"Erro ao salvar o arquivo CSV: {e}")

def analyze_contributions(csv_filename="issues_closed_resumida.csv", txt_filename="issues_closed_contribuidores.txt"):
    """
    Analisa um arquivo CSV de issues fechadas (com labels) e calcula o tempo de participação,
    o número de issues por usuário e as labels utilizadas, salvando os resultados em um
    arquivo de texto.
    """

    contributions = {}

    try:
        with open(csv_filename, "r", encoding="utf-8") as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                user = row["user"]
                created_at_str = row["created_at"]
                closed_at_str = row["closed_at"]
                labels_str = row["labels"]  # Pega as labels como string

                # Converte as strings de data e hora para objetos datetime
                try:
                    created_at = datetime.fromisoformat(created_at_str.replace("Z", "+00:00"))
                    closed_at = datetime.fromisoformat(closed_at_str.replace("Z", "+00:00"))
                except ValueError as e:
                    print(f"Erro ao converter data/hora para a issue {row['number']}: {e}")
                    continue

                # Calcula o tempo de participação
                participation_time = closed_at - created_at

                # Converte a string de labels de volta para uma lista
                labels = labels_str.split(";")  # Usa o mesmo separador que na função save_issues_to_csv

                # Atualiza as informações do usuário no dicionário
                if user not in contributions:
                    contributions[user] = {
                        "total_participation_time": timedelta(),
                        "num_issues": 0,
                        "labels": {},  # Dicionário para contar as labels
                    }

                contributions[user]["total_participation_time"] += participation_time
                contributions[user]["num_issues"] += 1

                # Conta as labels
                for label in labels:
                    if label:  # Evita contar strings vazias (se houver separadores extras)
                        if label not in contributions[user]["labels"]:
                            contributions[user]["labels"][label] = 0
                        contributions[user]["labels"][label] += 1

    except FileNotFoundError:
        print(f"Erro: Arquivo '{csv_filename}' não encontrado.")
        return
    except Exception as e:
        print(f"Erro ao ler o arquivo CSV: {e}")
        return

    # Salvar os resultados em um arquivo de texto
    try:
        with open(txt_filename, "w", encoding="utf-8") as txtfile:
            txtfile.write("Análise de Contribuições por Usuário:\n\n")
            for user, data in contributions.items():
                total_time = data["total_participation_time"]
                num_issues = data["num_issues"]
                labels = data["labels"]

                # Formatando o tempo total em dias, horas, minutos e segundos
                days = total_time.days
                hours, remainder = divmod(total_time.seconds, 3600)
                minutes, seconds = divmod(remainder, 60)
                time_str = f"{days} dias, {hours} horas, {minutes} minutos, {seconds} segundos"

                txtfile.write(f"Usuário: {user}\n")
                txtfile.write(f"  Número de Issues Participadas: {num_issues}\n")
                txtfile.write(f"  Tempo Total de Participação: {time_str}\n")

                txtfile.write("  Labels Utilizadas:\n")
                for label, count in labels.items():
                    txtfile.write(f"    - {label}: {count}\n")

                txtfile.write("\n")

        print(f"Análise salva em '{txt_filename}'")

    except Exception as e:
        print(f"Erro ao salvar o arquivo de texto: {e}")


if __name__ == "__main__":
    # Substitua pelos valores corretos
    repo_owner = "twbs"  # Ex: "google"
    repo_name = "bootstrap"  # Ex: "guava"

    github_token = get_github_token()
    if not github_token:
        print("Token do GitHub não encontrado. Abortando.")
        exit(1)

    issues = get_closed_issues(repo_owner, repo_name, github_token)

    if issues:
        save_issues_to_csv(issues)
        analyze_contributions()  # Analisa o CSV gerado
    else:
        print("Não foi possível obter os dados das issues.")