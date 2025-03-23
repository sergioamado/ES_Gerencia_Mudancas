#codigo do artigo predictng
# a saida não produziu todas as palavras que os 
#contribuidores mais usam

import os
import pandas as pd
import google.generativeai as genai
from datetime import datetime
import csv
import time
import random
import logging
import requests
from google.generativeai import GenerativeModel
from dotenv import load_dotenv
from collections import Counter

# Carregar variáveis do arquivo .env
load_dotenv()

# Configuração do logger
logging.basicConfig(filename='issue_processor.log', level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

# Chave da API do Gemini (INSIRA A SUA CHAVE AQUI - APENAS PARA TESTES LOCAIS!)
GEMINI_API_KEY = "SUA_CHAVE_API_AQUI"  # Substitua com a sua chave da API
GITHUB_TOKEN = "SEU_GITHUB_TOKEN" #Substitua com seu token do github

# Configurações do GitHub
GITHUB_REPO = "twbs/bootstrap"  # Substitua pelo repositório desejado
HEADERS = {'Authorization': f'token {GITHUB_TOKEN}'}

# Inicializar Gemini
try:
    genai.configure(api_key=GEMINI_API_KEY)  # Configura a chave da API
    print("API do Gemini configurada.")

    model = None  # Inicializa o modelo como None
    if GEMINI_API_KEY:
        try:
            model = genai.GenerativeModel('gemini-pro')
            logging.info("Modelo Gemini inicializado com sucesso.")
            print("Modelo Gemini inicializado com sucesso.")
        except Exception as e:
            logging.error(f"Erro ao inicializar o modelo Gemini: {e}")
            print(f"Erro ao inicializar o modelo Gemini: {e}")
    else:
        logging.error("Chave da API não configurada.")
        print("Chave da API não configurada.")

except Exception as e:
    logging.error(f"Erro ao configurar a API do Gemini: {e}")
    print(f"Erro ao configurar a API do Gemini: {e}")


# Constantes
CATEGORIES = ["respectfulness", "freedom", "broadmindedness", "social power", "equity & equality", "environment", "desconhecido"]
INITIAL_DELAY = 1  # segundos
MAX_RETRIES = 3
JITTER_DELAY = 0.5
TOP_CONTRIBUTORS_COUNT = 30

# Palavras-chave por categoria
KEYWORDS = {
    "respectfulness": [
        "code of conduct", "polite", "rude",  # Palavras do artigo
        "respectful communication", "constructive feedback", "collaboration", "avoiding offensive language",
        "respectful tone", "inclusive language", "empathy", "patience", "mutual respect", "professionalism",
        "kindness", "courtesy", "positive interaction", "respectful disagreement", "active listening",
        "avoiding toxicity", "respectful code reviews", "respecting time", "respecting contributions",
        "respecting diversity"
    ],
    "freedom": [
        "freedom", "user choose", "sovereign",  # Palavras do artigo
        "freedom to contribute", "freedom to fork", "freedom to modify code", "freedom of choice",
        "open source", "open collaboration", "autonomy", "independence", "self-governance",
        "freedom of expression", "freedom to experiment", "freedom to innovate", "freedom to distribute",
        "freedom to use", "freedom to decide", "freedom to customize", "freedom to participate",
        "freedom to criticize", "freedom to collaborate", "freedom to choose tools"
    ],
    "broadmindedness": [
        "diversity", "diverse", "unconventional",  # Palavras do artigo
        "openness to new ideas", "acceptance of different approaches", "inclusivity", "global collaboration",
        "multiculturalism", "flexibility", "adaptability", "creativity", "innovation", "non-conformity",
        "open-mindedness", "embracing change", "diverse perspectives", "cross-cultural collaboration",
        "tolerance", "respect for differences", "unconventional solutions", "alternative approaches",
        "out-of-the-box thinking", "embracing diversity"
    ],
    "social power": [
        "central authority", "gatekeeper", "monopoly",  # Palavras do artigo
        "maintainer authority", "control over decisions", "influence on project direction", "hierarchy",
        "leadership", "governance", "decision-making power", "power dynamics", "contributor hierarchy",
        "power to approve", "power to reject", "power to define standards", "power to set priorities",
        "power to moderate", "power to manage", "power to influence", "power to govern", "power to shape",
        "power to control", "power to lead"
    ],
    "equity & equality": [
        "unfair", "fairness", "justice",  # Palavras do artigo
        "equal opportunities", "fair treatment", "equal voice", "fair distribution of tasks", "inclusivity",
        "equal access", "fair recognition", "equal representation", "fair contribution", "equal rights",
        "equal participation", "fair rewards", "equal credit", "fair policies", "equal support",
        "fair evaluation", "equal mentorship", "fair collaboration", "equal decision-making", "fair compensation"
    ],
    "environment": [
        "climate change", "energy consumption", "wildlife",  # Palavras do artigo
        "sustainability", "eco-friendly", "resource efficiency", "carbon footprint", "green computing",
        "energy-efficient code", "renewable energy", "reducing waste", "minimizing impact",
        "environmental awareness", "sustainable practices", "eco-conscious development",
        "low-energy algorithms", "green infrastructure", "reducing emissions", "sustainable hardware",
        "energy optimization", "environmental responsibility", "eco-friendly tools", "green policies"
    ],
    "desconhecido": [] #Para casos em que Gemini não consegue classificar
}

def classify_issue_gemini(title, body):
    if not model:
        logging.error("Modelo Gemini não inicializado. Impossível classificar a issue.")
        print("Modelo Gemini não inicializado. Impossível classificar a issue.")
        return "desconhecido"

    prompt = f"""Classifique a seguinte issue em uma das categorias: {', '.join(CATEGORIES)}.
    Use as seguintes palavras chaves para cada categoria:
    Respectfulness: {', '.join(KEYWORDS["respectfulness"][:3])} #Apenas as 3 primeiras palavras para cada categoria
    Freedom: {', '.join(KEYWORDS["freedom"][:3])}
    Broadmindedness: {', '.join(KEYWORDS["broadmindedness"][:3])}
    Social Power: {', '.join(KEYWORDS["social power"][:3])}
    Equity & Equality: {', '.join(KEYWORDS["equity & equality"][:3])}
    Environment: {', '.join(KEYWORDS["environment"][:3])}

    Retorne a categoria como um texto. Se as categorias sugeridas não se aplicarem, retorne a que voce interpretar com o texto "desconhecido".

    Título: {title}
    Descrição: {body}

    Categoria:"""

    retries = 0
    delay = INITIAL_DELAY

    while retries <= MAX_RETRIES:
        try:
            response = model.generate_content(prompt)
            category = response.text.strip().lower()
            print(f"Resposta do Gemini: {category}")

             # Verifique se a categoria retornada pelo Gemini é válida
            if category in CATEGORIES:
                 logging.info(f"Classificou a issue com título '{title}' para a categoria '{category}' usando Gemini.")
                 print(f"Classificou a issue com título '{title}' para a categoria '{category}' usando Gemini.")
                 return category
            else:
                logging.warning(f"Categoria '{category}' retornada pelo Gemini é inválida para a issue '{title}'.")
                print(f"Categoria '{category}' retornada pelo Gemini é inválida para a issue '{title}'.")
                return "desconhecido"  # Categoria padrão caso o Gemini retorne algo inválido

        except Exception as e:
            logging.exception(f"Erro ao obter resposta do Gemini: {e}")
            print(f"Erro ao obter resposta do Gemini: {e}")

            if "429" in str(e):  # Verifica se o erro é de Rate Limit
                logging.warning(f"Erro 429: Tentativa {retries + 1} - Esperando {delay:.2f} segundos...")
                print(f"Erro 429: Tentativa {retries + 1} - Esperando {delay:.2f} segundos...")
                time.sleep(delay + random.uniform(0, JITTER_DELAY)) # Chamando a biblioteca corretamente
                delay *= 2
                retries += 1
            else:
                logging.error(f"Erro na classificação: {e}")
                print(f"Erro na classificação: {e}")
                return "desconhecido"

    logging.warning(f"Desistindo após {MAX_RETRIES} tentativas de classificar a issue '{title}' usando Gemini.")
    print(f"Desistindo após {MAX_RETRIES} tentativas de classificar a issue '{title}' usando Gemini.")
    return "desconhecido"

def fetch_comments(issue_number):
    """Fetch all comments for a specific issue."""
    url = f"https://api.github.com/repos/{GITHUB_REPO}/issues/{issue_number}/comments"
    try:
        response = requests.get(url, headers=HEADERS)
        response.raise_for_status()  # Lança uma exceção para status de erro
        return response.json()
    except requests.exceptions.RequestException as e:
        logging.error(f"Error fetching comments for issue {issue_number}: {e}")
        print(f"Erro ao buscar comentarios da issue {issue_number}: {e}")
        return []

def analyze_issues_csv_monthly(csv_file):
    """
    Lê um arquivo CSV, classifica as issues usando o Gemini mês a mês e retorna um dicionário com as contagens de cada categoria por mês.
    Adiciona também a análise dos top contribuidores e suas palavras mais frequentes.
    """
    monthly_category_counts = {}
    all_comments = []  # Lista para armazenar todos os comentários para análise de contribuidores
    all_authors = [] #Lista para armazenar todos os autores

    try:
        df = pd.read_csv(csv_file, encoding='utf-8')  # Garante a leitura correta de caracteres especiais
        logging.info(f"Arquivo CSV lido com sucesso. Número de linhas: {len(df)}")
        print(f"Arquivo CSV lido com sucesso. Número de linhas: {len(df)}")

        # Colunas do CSV
        number_column = 'number'
        title_column = 'title'
        body_column = 'body'
        user_column = 'user'
        created_at_column = 'created_at'


        # Verifique se as colunas existem
        if not all(col in df.columns for col in [created_at_column, title_column, body_column, number_column, user_column]):
            logging.error("Uma ou mais colunas necessárias não foram encontradas no arquivo CSV.")
            print("Uma ou mais colunas necessárias não foram encontradas no arquivo CSV.")
            return monthly_category_counts

        # Imprime as primeiras linhas do DataFrame para verificar as colunas
        print("Primeiras linhas do DataFrame:")
        print(df.head())

        # Converta a coluna 'Created At' para datetime, lidando com diferentes formatos
        # Usando infer_datetime_format=True para tentar detectar o formato automaticamente
        try:
            df[created_at_column] = pd.to_datetime(df[created_at_column], infer_datetime_format=True, errors='raise')
            logging.info(f"Coluna '{created_at_column}' convertida para datetime com sucesso (inferido).")
            print(f"Coluna '{created_at_column}' convertida para datetime com sucesso (inferido).")
        except ValueError as e:
            logging.error(f"Não foi possível converter a coluna '{created_at_column}' para datetime (inferência falhou): {e}")
            print(f"Não foi possível converter a coluna '{created_at_column}' para datetime (inferência falhou): {e}")
            return monthly_category_counts


        # Agrupe as issues por mês
        grouped = df.groupby(pd.Grouper(key=created_at_column, freq='M'))

        for month, group in grouped:
            month_str = month.strftime('%Y-%m')  # Formato YYYY-MM para o nome do mês
            logging.info(f"Analisando mês: {month_str}")
            logging.info(f"Analisando mês: {month_str}, Número de issues neste mês: {len(group)}")
            print(f"Analisando mês: {month_str}, Número de issues neste mês: {len(group)}")
            category_counts = {category: 0 for category in CATEGORIES}
            total_issues = len(group)

            for index, row in group.iterrows():
                issue_number = row[number_column]
                title = row[title_column]  # Assume que a coluna que contem os titulos se chama 'title'
                body = row[body_column]  # Assume que a coluna que contem os corpos das issues se chama 'body'
                author = row[user_column] #Assume que a coluna que contem os autores se chama 'user'

                print(f"Título: {title}")
                print(f"Body: {body}")
                category = classify_issue_gemini(title, body)
                logging.info(f"Issue classificada como: {category}")
                print(f"Issue classificada como: {category}")
                category_counts[category] += 1  # Incrementa a contagem da categoria

                #Busca os comentarios da API
                comments = fetch_comments(issue_number)
                for comment in comments:
                    all_comments.append(comment.get('body', '')) #Adiciona o comentario a lista
                    all_authors.append(comment.get('user').get('login', 'N/A')) #Adiciona o autor do comentario a lista
                all_authors.append(author) #adiciona o autor da issue a lista

            logging.info(f"Mês: {month_str}, Total de issues processadas: {total_issues}")
            logging.info(f"Mês: {month_str}, Contagem das categorias: {category_counts}")
            print(f"Mês: {month_str}, Total de issues processadas: {total_issues}")
            print(f"Mês: {month_str}, Contagem das categorias: {category_counts}")

            monthly_category_counts[month_str] = {
                "total_issues": total_issues,
                "category_counts": category_counts
            }

        #Análise dos contribuidores mais ativos
        top_contributors = Counter(all_authors).most_common(TOP_CONTRIBUTORS_COUNT)
        logging.info(f"Top {TOP_CONTRIBUTORS_COUNT} contribuidores: {top_contributors}")
        print(f"Top {TOP_CONTRIBUTORS_COUNT} contribuidores: {top_contributors}")

        #Análise das palavras mais frequentes nos comentários
        comment_words = ' '.join(all_comments).split()
        most_common_words = Counter(comment_words).most_common(10) #Top 10 palavras
        logging.info(f"Palavras mais frequentes nos comentários: {most_common_words}")
        print(f"Palavras mais frequentes nos comentários: {most_common_words}")

    except FileNotFoundError:
        logging.error(f"Arquivo CSV não encontrado: {csv_file}")
        print(f"Arquivo CSV não encontrado: {csv_file}")
    except KeyError as e:
        logging.error(f"Coluna ausente no arquivo CSV: {e}")
        print(f"Coluna ausente no arquivo CSV: {e}")
    except Exception as e:
        logging.exception(f"Erro ao processar o arquivo CSV: {e}")  # Use logging.exception para imprimir o stack trace completo
        print(f"Erro ao processar o arquivo CSV: {e}")

    return monthly_category_counts, top_contributors, most_common_words


def generate_output_txt(monthly_category_counts, top_contributors, most_common_words, output_file="saida_gemini.txt"):
    """
    Gera um arquivo de texto com a análise das categorias das issues mês a mês, incluindo estatísticas,
    top contribuidores e palavras mais frequentes.
    """
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write("Análise de Categorias de Issues (Mensal):\n\n")

            for month, data in monthly_category_counts.items():
                total_issues = data["total_issues"]
                category_counts = data["category_counts"]

                f.write(f"Mês: {month}\n")
                f.write(f"Total de Issues Analisadas: {total_issues}\n\n")
                f.write("Resultados:\n")

                for category, count in category_counts.items():
                    percentage = (count / total_issues) * 100 if total_issues > 0 else 0
                    f.write(f"- {category}: {count} issues ({percentage:.2f}%)\n")  # Escreve a categoria e porcentagem

                f.write("\n")

            f.write("\nPalavras-chave Utilizadas por Categoria:\n")
            for category, keywords in KEYWORDS.items():
                f.write(f"- {category}: {', '.join(keywords[:10])}\n")  # Escreve as 10 primeiras palavras-chave de cada categoria

            f.write(f"\nTop {TOP_CONTRIBUTORS_COUNT} Contribuidores:\n")
            for contributor, count in top_contributors:
                f.write(f"- {contributor}: {count} contribuições\n")

            f.write("\nPalavras Mais Frequentes nos Comentários:\n")
            for word, count in most_common_words:
                f.write(f"- {word}: {count} ocorrências\n")

        logging.info(f"Arquivo de saída gerado com sucesso: {output_file}")
        print(f"Arquivo de saída gerado com sucesso: {output_file}")
    except Exception as e:
        logging.error(f"Erro ao gerar o arquivo de saída: {e}")
        print(f"Erro ao gerar o arquivo de saída: {e}")


def main():
    csv_file = "closed_issues.csv"  # Nome do arquivo CSV com as issues
    output_file = "saida_gemini.txt"  # Nome do arquivo TXT de saída

    # Analisa as issues do CSV mês a mês
    monthly_category_counts, top_contributors, most_common_words = analyze_issues_csv_monthly(csv_file)

    # Gera o arquivo de texto com os resultados
    if monthly_category_counts:  # Garante que a análise foi feita com sucesso
        generate_output_txt(monthly_category_counts, top_contributors, most_common_words, output_file)
    else:
        logging.warning("Nenhuma categoria foi analisada. O arquivo de saída não será gerado.")
        print("Nenhuma categoria foi analisada. O arquivo de saída não será gerado.")


if __name__ == "__main__":
    main()