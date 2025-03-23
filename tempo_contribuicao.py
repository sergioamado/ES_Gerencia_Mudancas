import csv
import google.generativeai as genai
import os
from datetime import datetime

# Substitua com sua chave de API do Gemini
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")
if not GOOGLE_API_KEY:
    print("Erro: A variável de ambiente GOOGLE_API_KEY não está definida.")
    exit()
genai.configure(api_key=GOOGLE_API_KEY)

# Caminho para o seu arquivo CSV
CSV_FILE = "closed_issues.csv"
OUTPUT_FILE = "tempo_contribuicao.txt"

# Lista dos 30 principais contribuidores (mantenha para filtrar os resultados)
TOP_CONTRIBUTORS = [
    "ghost", "Merg1255", "lookfirst", "dyve", "leeaston", "pamelafox", "andriijas",
    "buraktuyan", "necolas", "ansman", "ctalkington", "martinbean", "Anahkiasen",
    "tinyfly", "MGaetan89", "simonfranz", "fat", "sannefoltz", "ShaunR", "mdo",
    "marcalj", "jasny", "purwandi", "fionawhim", "quasipickle", "richardp-au",
    "thezoggy", "paglias", "powder96", "BigBlueHat"
]

def analisar_tempo_contribuicoes(csv_file, output_file, top_contributors):
    """
    Analisa o tempo de contribuição dos contribuidores, usando o Gemini para resumir os resultados.

    Args:
        csv_file (str): Caminho para o arquivo CSV contendo os dados das issues.
        output_file (str): Caminho para o arquivo de texto onde os resultados serão salvos.
        top_contributors (list): Lista dos nomes de usuário dos principais contribuidores a serem analisados.
    """

    contribuicoes_por_usuario = {}

    try:
        with open(csv_file, 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            for row in reader:
                user = row['user']
                if user in top_contributors:
                    created_at = datetime.fromisoformat(row['created_at'].replace('Z', '+00:00')) # Converter para datetime
                    closed_at = datetime.fromisoformat(row['closed_at'].replace('Z', '+00:00'))   # Converter para datetime

                    if user not in contribuicoes_por_usuario:
                        contribuicoes_por_usuario[user] = {
                            'datas_criacao': [],
                            'primeira_issue': None,
                            'ultima_issue': None
                        }

                    contribuicoes_por_usuario[user]['datas_criacao'].append(created_at)  # Armazenar datas como datetime

    except FileNotFoundError:
        print(f"Erro: Arquivo CSV '{csv_file}' não encontrado.")
        return
    except Exception as e:
        print(f"Erro ao ler o arquivo CSV: {e}")
        return

    # Encontrar a primeira e a última issue para cada contribuidor
    for user, data in contribuicoes_por_usuario.items():
        datas_criacao = data['datas_criacao']
        if datas_criacao:
            data['primeira_issue'] = min(datas_criacao)  # Encontrar a data mais antiga
            data['ultima_issue'] = max(datas_criacao)    # Encontrar a data mais recente

    # Listar modelos disponíveis
    print("Modelos disponíveis:")
    for m in genai.list_models():
        print(f"- {m.name}")

    # Tentar carregar o modelo, com fallback
    try:
        model = genai.GenerativeModel('gemini-pro')
        print("Modelo usado: gemini-pro")
    except Exception as e:
        print(f"Erro ao carregar gemini-pro: {e}")
        # Tentar um modelo alternativo
        available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        if available_models:
            alternative_model_name = available_models[0]
            print(f"Usando modelo alternativo: {alternative_model_name}")
            model = genai.GenerativeModel(alternative_model_name)
            print(f"Modelo usado: {alternative_model_name}")  # Log do modelo alternativo
        else:
            print("Nenhum modelo compatível encontrado. Abortando.")
            return

    with open(output_file, 'w', encoding='utf-8') as outfile:
        for contribuidor, data in contribuicoes_por_usuario.items():
            primeira_issue_str = data['primeira_issue'].strftime('%Y-%m-%d %H:%M:%S') if data['primeira_issue'] else "N/A"
            ultima_issue_str = data['ultima_issue'].strftime('%Y-%m-%d %H:%M:%S') if data['ultima_issue'] else "N/A"

            prompt = f"""Analise as seguintes informações sobre o contribuidor {contribuidor}:

            Primeira issue criada em: {primeira_issue_str}
            Última issue criada em: {ultima_issue_str}

            Com base nessas informações, forneça um resumo conciso sobre o período de contribuição desse usuário. Inclua a data de início, a data de término e a duração total das contribuições (se disponível).

            Formate a resposta da seguinte forma:
            Data de início: [data]
            Data de término: [data]
            Duração total: [duração]
            """

            try:
                response = model.generate_content(prompt)
                analise = response.text

            except Exception as e:
                analise = f"Erro ao analisar com o Gemini: {e}"

            outfile.write(f"Análise do Tempo de Contribuição do Contribuidor: {contribuidor}\n")
            outfile.write(analise + "\n\n")  # Salva a análise no arquivo

    print(f"Análise completa. Resultados salvos em '{output_file}'")

# Executa a análise
analisar_tempo_contribuicoes(CSV_FILE, OUTPUT_FILE, TOP_CONTRIBUTORS)