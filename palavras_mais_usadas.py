#tentar rodar no deepseeker
#ver se consegue achar as palavras para classificar

import csv
import google.generativeai as genai
import os
from collections import Counter

# Substitua com sua chave de API do Gemini
GOOGLE_API_KEY = "SUA CHAVE GEMINI"  # os.environ.get("GOOGLE_API_KEY")
genai.configure(api_key=GOOGLE_API_KEY)

# Caminho para o seu arquivo CSV
CSV_FILE = "closed_issues.csv"
OUTPUT_FILE = "palavras_mais_usadas.txt"

# Lista dos 30 principais contribuidores
TOP_CONTRIBUTORS = [
    "ghost", "Merg1255", "lookfirst", "dyve", "leeaston", "pamelafox", "andriijas",
    "buraktuyan", "necolas", "ansman", "ctalkington", "martinbean", "Anahkiasen",
    "tinyfly", "MGaetan89", "simonfranz", "fat", "sannefoltz", "ShaunR", "mdo",
    "marcalj", "jasny", "purwandi", "fionawhim", "quasipickle", "richardp-au",
    "thezoggy", "paglias", "powder96", "BigBlueHat"
]

def analisar_contribuicoes(csv_file, output_file, top_contributors):
    """
    Analisa as contribuições dos principais contribuidores em um arquivo CSV,
    usando o Gemini para identificar as palavras mais utilizadas.

    Args:
        csv_file (str): Caminho para o arquivo CSV contendo os dados das issues.
        output_file (str): Caminho para o arquivo de texto onde os resultados serão salvos.
        top_contributors (list): Lista dos nomes de usuário dos principais contribuidores a serem analisados.
    """

    contribuicoes_por_usuario = {}
    for contribuidor in top_contributors:
        contribuicoes_por_usuario[contribuidor] = ""  # Inicializa com uma string vazia

    try:
        with open(csv_file, 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            for row in reader:
                if row['user'] in top_contributors:
                    # Adiciona o corpo da issue à string do contribuidor
                    contribuicoes_por_usuario[row['user']] += row['body'] + " "

    except FileNotFoundError:
        print(f"Erro: Arquivo CSV '{csv_file}' não encontrado.")
        return
    except Exception as e:
        print(f"Erro ao ler o arquivo CSV: {e}")
        return

    # Lista os modelos disponíveis
    for m in genai.list_models():
        print(m.name)

    # Tenta usar gemini-pro, senão usa outro modelo disponível
    try:
        model = genai.GenerativeModel('gemini-pro')
    except Exception as e:
        print(f"Erro ao carregar gemini-pro: {e}")
        # Procura um modelo alternativo
        available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        if available_models:
            alternative_model_name = available_models[0]  # Pega o primeiro modelo disponível
            print(f"Usando modelo alternativo: {alternative_model_name}")
            model = genai.GenerativeModel(alternative_model_name)
        else:
            print("Nenhum modelo compatível encontrado. Abortando.")
            return

    with open(output_file, 'w', encoding='utf-8') as outfile:
        for contribuidor, texto in contribuicoes_por_usuario.items():
            # Limita o texto enviado ao Gemini para evitar erros de tamanho
            texto_limitado = texto[:15000] # Limita aos primeiros 15000 caracteres

            prompt = f"""Analyze the following text (contributions from user {contribuidor} in issues) and identify the most used words (ignore common words like "the", "a", "an", "in", "to", "of", "for", "that", "is", "are", "was", "were", "with", "on", "at", "by", "from", "as", "it", "this", "that", "these", "those", "he", "she", "him", "her", "his", "hers", "its", "we", "us", "our", "ours", "you", "your", "yours", "they", "them", "their", "theirs", "i", "me", "my", "mine", "and", "but", "or", "so", "because", "if", "then", "else", "when", "where", "how", "what", "which", "who", "whom", "whose", "all", "any", "both", "each", "few", "many", "most", "none", "one", "some", "several", "much", "more", "less", "least", "every", "either", "neither", "other", "another", "such", "than", "very", "too", "also", "even", "only", "just", "really", "quite", "almost", "nearly", "already", "yet", "still", "however", "therefore", "thus", "then", "now", "here", "there", "about", "above", "across", "after", "against", "along", "among", "around", "before", "behind", "below", "beneath", "beside", "between", "beyond", "during", "except", "inside", "into", "near", "onto", "outside", "over", "through", "under", "until", "up", "down", "without", "within", "out", "off", "can", "could", "may", "might", "must", "shall", "should", "will", "would", "am", "is", "are", "was", "were", "be", "been", "being", "have", "has", "had", "having", "do", "does", "did", "doing", "done", "get", "gets", "got", "getting", "gotten", "make", "makes", "made", "making", "take", "takes", "took", "taking", "taken", "put", "puts", "putting", "put", "see", "sees", "saw", "seeing", "seen", "look", "looks", "looked", "looking", "go", "goes", "went", "going", "gone"):

            {texto_limitado}

            Present the 10 most frequent words and their respective counts.
            Format the answer as follows:
            word1: count1
            word2: count2
            ...
            """

            try:
                response = model.generate_content(prompt)
                analise = response.text

            except Exception as e:
                analise = f"Error analyzing with Gemini: {e}"


            outfile.write(f"Analysis of Contributor: {contribuidor}\n")
            outfile.write(analise + "\n\n")  # Salva a análise no arquivo

    print(f"Analysis complete. Results saved in '{output_file}'")

# Executa a análise
analisar_contribuicoes(CSV_FILE, OUTPUT_FILE, TOP_CONTRIBUTORS)