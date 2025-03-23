import requests
import json
import re

def obter_token():
    """Lê o token do GitHub do arquivo github_token.txt."""
    try:
        with open("github_token.txt", "r") as f:
            return f.readline().strip()
    except FileNotFoundError:
        print("Arquivo github_token.txt não encontrado. Por favor, crie o arquivo e coloque seu token do GitHub dentro.")
        exit()

def obter_informacoes_repositorio(token):
    """Obtém informações do repositório Bootstrap usando a API do GitHub."""
    headers = {"Authorization": f"token {token}"}
    url_base = "https://api.github.com/repos/twbs/bootstrap"

    # Releases
    url_releases = f"{url_base}/releases"
    response_releases = requests.get(url_releases, headers=headers)
    releases = response_releases.json()

    # Branches
    url_branches = f"{url_base}/branches"
    response_branches = requests.get(url_branches, headers=headers)
    branches = response_branches.json()

    # Milestones
    url_milestones = f"{url_base}/milestones"
    response_milestones = requests.get(url_milestones, headers=headers)
    milestones = response_milestones.json()

    # Labels
    url_labels = f"{url_base}/labels"
    response_labels = requests.get(url_labels, headers=headers)
    labels = response_labels.json()

    return releases, branches, milestones, labels

def analisar_versionamento(releases):
    """Analisa as versões semânticas das releases, incluindo as não padronizadas."""
    major = 0
    minor = 0
    patch = 0
    nao_padronizadas = []

    for release in releases:
        version = release["tag_name"]
        # Tenta corresponder ao padrão SemVer (x.y.z)
        match = re.match(r"(\d+)\.(\d+)\.(\d+)", version)

        if match:
            major_num, minor_num, patch_num = map(int, match.groups())
            if major_num >= 10:
                major += 1
            elif minor_num >= 5:
                minor += 1
            else:
                patch += 1
        else:
            nao_padronizadas.append(version)

    return major, minor, patch, nao_padronizadas

def obter_data_criacao_branch(token, branch_name):
    """Obtém a data de criação da branch através do primeiro commit."""
    headers = {"Authorization": f"token {token}"}
    url_base = "https://api.github.com/repos/twbs/bootstrap"
    url_commits = f"{url_base}/commits?sha={branch_name}&per_page=1"  # Pega apenas o primeiro commit
    response_commits = requests.get(url_commits, headers=headers)
    commits = response_commits.json()

    if commits and isinstance(commits, list) and len(commits) > 0:
        primeiro_commit = commits[0]
        data_criacao = primeiro_commit["commit"]["author"]["date"]
        return data_criacao[:10]  # Retorna apenas a data (AAAA-MM-DD)
    else:
        return "Data de criação não encontrada"

def escrever_arquivo(releases, branches, milestones, labels, token):
    """Escreve as informações no arquivo Releases e Gerenciamento.txt."""
    major, minor, patch, nao_padronizadas = analisar_versionamento(releases)

    with open("Releases e Gerenciamento.txt", "w", encoding="utf-8") as arquivo:
        arquivo.write("## Análise do Repositório Bootstrap (twbs/bootstrap)\n\n")

        arquivo.write("### Releases:\n\n")
        arquivo.write(f"Número total de releases: {len(releases)}\n\n")
        arquivo.write("Lista de releases e suas datas de lançamento:\n")
        for release in releases:
            arquivo.write(f"- {release['name']} ({release['tag_name']}): {release['published_at'][:10]}\n") # Pega apenas a data

        arquivo.write("\n### Versionamento Semântico:\n\n")
        arquivo.write(f"- MAJOR (Mudanças incompatíveis): {major}\n")
        arquivo.write(f"- MINOR (Novas funcionalidades): {minor}\n")
        arquivo.write(f"- PATCH (Correções de bugs/segurança): {patch}\n")

        if nao_padronizadas:
            arquivo.write("\n- Releases com versionamento não padronizado:\n")
            for version in nao_padronizadas:
                arquivo.write(f"  - {version}\n")

        arquivo.write("\n### Branches:\n\n")
        arquivo.write(f"Número total de branches: {len(branches)}\n\n")
        arquivo.write("Lista de branches, suas datas de criação e propósitos (requer análise individual):\n")
        for branch in branches:
            data_criacao = obter_data_criacao_branch(token, branch["name"])
            arquivo.write(f"- {branch['name']} (Data de Criação: {data_criacao})\n")
        arquivo.write("  *Nota: A descrição exata do propósito de cada branch exigiria uma análise individual do histórico de commits e da documentação do projeto.*")

        arquivo.write("\n### CONTRIBUTING.md:\n\n")
        arquivo.write("O arquivo CONTRIBUTING.md geralmente contém diretrizes para contribuir com o projeto, como:\n")
        arquivo.write("- Como reportar bugs\n")
        arquivo.write("- Como sugerir melhorias\n")
        arquivo.write("- Diretrizes de estilo de código\n")
        arquivo.write("- Processo de envio de pull requests\n")
        arquivo.write("  *Nota: Para obter o conteúdo exato, é necessário acessar o arquivo diretamente no repositório.*")

        arquivo.write("\n### Milestones:\n\n")
        arquivo.write(f"Número total de milestones: {len(milestones)}\n\n")
        arquivo.write("Lista de milestones e seus objetivos:\n")
        for milestone in milestones:
            arquivo.write(f"- {milestone['title']}: {milestone['description']}\n")

        arquivo.write("\n### Labels:\n\n")
        arquivo.write(f"Número total de labels: {len(labels)}\n\n")
        arquivo.write("Lista de labels e seus propósitos:\n")
        for label in labels:
            arquivo.write(f"- {label['name']}: {label['description']}\n")
        arquivo.write("  *Nota: As labels são usadas para categorizar issues e pull requests, facilitando a organização e o gerenciamento do projeto.*")

# Bloco principal
if __name__ == "__main__":
    token = obter_token()
    releases, branches, milestones, labels = obter_informacoes_repositorio(token)
    escrever_arquivo(releases, branches, milestones, labels, token)
    print("bootstrap_analyzer.txt' gerado com sucesso.")