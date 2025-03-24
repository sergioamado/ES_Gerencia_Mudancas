#artigo 1

import csv
from datetime import datetime, timedelta

def analyze_contributions(csv_filename="issues_closed_resumida.csv", txt_filename="issues_closed_contribuidores.txt"):
    """
    Analisa um arquivo CSV de issues fechadas e calcula o tempo de participação e o número de issues
    por usuário, salvando os resultados em um arquivo de texto.

    Args:
        csv_filename (str, opcional): O nome do arquivo CSV de entrada.
                                        Padrão: "issues_closed_resumida.csv".
        txt_filename (str, opcional): O nome do arquivo de texto de saída.
                                        Padrão: "issues_closed_contribuidores.txt".
    """

    contributions = {}

    try:
        with open(csv_filename, "r", encoding="utf-8") as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                user = row["user"]
                created_at_str = row["created_at"]
                closed_at_str = row["closed_at"]

                # Converter as strings de data e hora para objetos datetime
                try:
                    created_at = datetime.fromisoformat(created_at_str.replace("Z", "+00:00"))
                    closed_at = datetime.fromisoformat(closed_at_str.replace("Z", "+00:00"))
                except ValueError as e:
                    print(f"Erro ao converter data/hora para a issue {row['number']}: {e}")
                    continue  # Ir para a próxima issue em caso de erro

                # Calcular o tempo de participação
                participation_time = closed_at - created_at

                # Atualizar as informações do usuário no dicionário
                if user not in contributions:
                    contributions[user] = {
                        "total_participation_time": timedelta(),
                        "num_issues": 0,
                    }

                contributions[user]["total_participation_time"] += participation_time
                contributions[user]["num_issues"] += 1

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

                # Formatando o tempo total em dias, horas, minutos e segundos
                days = total_time.days
                hours, remainder = divmod(total_time.seconds, 3600)
                minutes, seconds = divmod(remainder, 60)
                time_str = f"{days} dias, {hours} horas, {minutes} minutos, {seconds} segundos"

                txtfile.write(f"Usuário: {user}\n")
                txtfile.write(f"  Número de Issues Participadas: {num_issues}\n")
                txtfile.write(f"  Tempo Total de Participação: {time_str}\n")
                txtfile.write("\n")

        print(f"Análise salva em '{txt_filename}'")

    except Exception as e:
        print(f"Erro ao salvar o arquivo de texto: {e}")


if __name__ == "__main__":
   # analyze_contributions()  # Usa os nomes de arquivo padrão
    # Ou especifique os nomes dos arquivos:
    analyze_contributions("issues_closed_resumida.csv", "issues_closed_contribuidores.txt")