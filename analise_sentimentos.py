import os
import pandas as pd
import google.generativeai as genai
from datetime import datetime
import csv
import time
import random
import logging
from google.generativeai import GenerativeModel
from dotenv import load_dotenv

# Carregar variáveis do arquivo .env
load_dotenv()

# Configuração do logger
logging.basicConfig(filename='issue_processor.log', level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

# Chave da API do Gemini (INSIRA A SUA CHAVE AQUI - APENAS PARA TESTES LOCAIS!)
GEMINI_API_KEY = "AIzaSyDETu14kGy9717uaEjLqRZe3tJyWaKo8_8"  # Substitua com a sua chave da API

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

# Palavras-chave por categoria (palavras chave artigo)
KEYWORDS = {
    "respectfulness": ["code of conduct", "polite", "rude"], #Palavras-chave usadas no artigo
    "freedom": ["freedom", "user choose", "sovereign"], #Palavras-chave usadas no artigo
    "broadmindedness": ["diversity", "diverse", "unconventional"], #Palavras-chave usadas no artigo
    "social power": ["central authority", "gatekeeper", "monopoly"], #Palavras-chave usadas no artigo
    "equity & equality": ["unfair", "fairness", "justice"], #Palavras-chave usadas no artigo
    "environment": ["climate change", "energy consumption", "wildlife"], #Palavras-chave usadas no artigo
    "desconhecido": [] #Para casos em que Gemini não consegue classificar
}

def classify_issue_gemini(title, body):
    if not model:
        logging.error("Modelo Gemini não inicializado. Impossível classificar a issue.")
        print("Modelo Gemini não inicializado. Impossível classificar a issue.")
        return "desconhecido"

    prompt = f"""Classifique a seguinte issue em uma das categorias: {', '.join(CATEGORIES)}.
    Use as seguintes palavras chaves para cada categoria:
    Respectfulness: {', '.join(KEYWORDS["respectfulness"])}
    Freedom: {', '.join(KEYWORDS["freedom"])}
    Broadmindedness: {', '.join(KEYWORDS["broadmindedness"])}
    Social Power: {', '.join(KEYWORDS["social power"])}
    Equity & Equality: {', '.join(KEYWORDS["equity & equality"])}
    Environment: {', '.join(KEYWORDS["environment"])}

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

def analyze_issues_csv_monthly(csv_file):
    """
    Lê um arquivo CSV, classifica as issues usando o Gemini mês a mês e retorna um dicionário com as contagens de cada categoria por mês.
    """
    monthly_category_counts = {}

    try:
        df = pd.read_csv(csv_file, encoding='utf-8')  # Garante a leitura correta de caracteres especiais
        logging.info(f"Arquivo CSV lido com sucesso. Número de linhas: {len(df)}")
        print(f"Arquivo CSV lido com sucesso. Número de linhas: {len(df)}")

        # Colunas em inglês
        title_column = 'Title' #Título
        description_column = 'Body' #Descrição
        created_at_column = 'Created At' #Data de Criação

        # Verifique se as colunas existem
        if created_at_column not in df.columns:
            logging.error(f"A coluna '{created_at_column}' não foi encontrada no arquivo CSV.")
            print(f"A coluna '{created_at_column}' não foi encontrada no arquivo CSV.")
            return monthly_category_counts

        if title_column not in df.columns or description_column not in df.columns:
            logging.error(f"As colunas '{title_column}' ou '{description_column}' não foram encontradas no arquivo CSV.")
            print(f"As colunas '{title_column}' ou '{description_column}' não foram encontradas no arquivo CSV.")
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
                title = row[title_column]  # Assume que a coluna que contem os titulos se chama 'Title'
                body = row[description_column]  # Assume que a coluna que contem os corpos das issues se chama 'Body'
                print(f"Título: {title}")
                print(f"Body: {body}")
                category = classify_issue_gemini(title, body)
                logging.info(f"Issue classificada como: {category}")
                print(f"Issue classificada como: {category}")
                category_counts[category] += 1  # Incrementa a contagem da categoria

            logging.info(f"Mês: {month_str}, Total de issues processadas: {total_issues}")
            logging.info(f"Mês: {month_str}, Contagem das categorias: {category_counts}")
            print(f"Mês: {month_str}, Total de issues processadas: {total_issues}")
            print(f"Mês: {month_str}, Contagem das categorias: {category_counts}")

            monthly_category_counts[month_str] = {
                "total_issues": total_issues,
                "category_counts": category_counts
            }

    except FileNotFoundError:
        logging.error(f"Arquivo CSV não encontrado: {csv_file}")
        print(f"Arquivo CSV não encontrado: {csv_file}")
    except KeyError as e:
        logging.error(f"Coluna ausente no arquivo CSV: {e}")
        print(f"Coluna ausente no arquivo CSV: {e}")
    except Exception as e:
        logging.exception(f"Erro ao processar o arquivo CSV: {e}")  # Use logging.exception para imprimir o stack trace completo
        print(f"Erro ao processar o arquivo CSV: {e}")

    return monthly_category_counts


def generate_output_txt(monthly_category_counts, output_file="saida_gemini.txt"):
    """
    Gera um arquivo de texto com a análise das categorias das issues mês a mês, incluindo estatísticas.
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
                f.write(f"- {category}: {', '.join(keywords)}\n")  # Escreve as palavras-chave de cada categoria

        logging.info(f"Arquivo de saída gerado com sucesso: {output_file}")
        print(f"Arquivo de saída gerado com sucesso: {output_file}")
    except Exception as e:
        logging.error(f"Erro ao gerar o arquivo de saída: {e}")
        print(f"Erro ao gerar o arquivo de saída: {e}")


def main():
    csv_file = "issues_fechadas.csv"  # Nome do arquivo CSV com as issues
    output_file = "saida_gemini.txt"  # Nome do arquivo TXT de saída

    # Analisa as issues do CSV mês a mês
    monthly_category_counts = analyze_issues_csv_monthly(csv_file)

    # Gera o arquivo de texto com os resultados
    if monthly_category_counts:  # Garante que a análise foi feita com sucesso
        generate_output_txt(monthly_category_counts, output_file)
    else:
        logging.warning("Nenhuma categoria foi analisada. O arquivo de saída não será gerado.")
        print("Nenhuma categoria foi analisada. O arquivo de saída não será gerado.")


if __name__ == "__main__":
    main()