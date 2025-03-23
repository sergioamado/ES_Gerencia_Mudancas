import requests
from bs4 import BeautifulSoup
import csv

def carregar_token():
    """Carrega o token do GitHub a partir do arquivo github_token.txt."""
    try:
        with open('github_token.txt', 'r') as file:
            return file.read().strip()
    except FileNotFoundError:
        print("Erro: Arquivo github_token.txt não encontrado.")
        return None

def extrair_info_releases(url_releases, arquivo_csv):
    """Extrai informações sobre as releases do Bootstrap e as salva em um arquivo CSV."""
    token = carregar_token()
    if not token:
        return

    headers = {
        'Authorization': f'token {token}'
    }

    try:
        response = requests.get(url_releases, headers=headers)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        releases = soup.find_all('div', class_='release-entry')  # Ajuste conforme a estrutura real

        with open(arquivo_csv, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(['Versão', 'Data', 'Descrição'])  # Cabeçalho do CSV

            for release in releases:
                versao = release.find('span', class_='css-truncate-target').text.strip() if release.find('span', class_='css-truncate-target') else 'N/A'
                data = release.find('relative-time').text.strip() if release.find('relative-time') else 'N/A'
                descricao = release.find('div', class_='markdown-body').text.strip() if release.find('div', class_='markdown-body') else 'N/A'

                writer.writerow([versao, data, descricao])

        print(f"Informações das releases salvas em {arquivo_csv}")

    except requests.exceptions.RequestException as e:
        print(f"Erro ao acessar {url_releases}: {e}")
    except Exception as e:
        print(f"Erro ao extrair informações das releases: {e}")

# Exemplo de uso
url_releases = 'https://github.com/twbs/bootstrap/releases'  # Substitua pelo URL real
arquivo_csv = 'bootstrap_releases.csv'
extrair_info_releases(url_releases, arquivo_csv)