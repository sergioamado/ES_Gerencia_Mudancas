import pandas as pd
import subprocess

def analisar_commits(repo_path):
    """Analisa o histórico de commits para identificar padrões de contribuição."""
    try:
        log_command = [
            'git', 'log', '--pretty=format:%an;%ad', '--date=short', '--no-merges'
        ]
        result = subprocess.run(log_command, cwd=repo_path, capture_output=True, text=True, check=True)
        log_output = result.stdout

        commits_data = []
        for line in log_output.splitlines():
            author, date = line.split(';')
            commits_data.append([author, date])

        df = pd.DataFrame(commits_data, columns=['Autor', 'Data'])
        return df

    except subprocess.CalledProcessError as e:
        print(f"Erro ao executar comando git: {e}")
        return None
    except Exception as e:
        print(f"Erro ao analisar commits: {e}")
        return None

def calcular_rotatividade(df):
    """Calcula a rotatividade de desenvolvedores ao longo do tempo."""
    # Agrupa por autor e conta o número de commits por autor
    commits_por_autor = df['Autor'].value_counts()
    print(f"Commit por autor:\n{commits_por_autor}")
# Exemplo de uso
repo_path = './bootstrap'
df_commits = analisar_commits(repo_path)

if df_commits is not None:
    print("Analisando rotatividade...")
    calcular_rotatividade(df_commits)