import os
from pathlib import Path

# Descobre o caminho da pasta atual (utils_populate) e sobe um nível para achar a pasta get_names/data
dir_path = Path(__file__).parent
pasta_data = dir_path.parent / "get_names" / "data"

# Define os caminhos exatos dos arquivos
caminho_original = pasta_data / "lista_pokemons_pvpivs.txt"
caminho_metade_1 = pasta_data / "lista_metade_1.txt"
caminho_metade_2 = pasta_data / "lista_metade_2.txt"

# Verifica se o arquivo original existe antes de tentar abrir
if not caminho_original.exists():
    print(f"⚠️ Erro: Não foi possível encontrar o arquivo em {caminho_original}")
    exit()

# Lê todas as linhas do arquivo original
with open(caminho_original, "r", encoding="utf-8") as f:
    linhas = f.readlines()

# Calcula a metade exata
metade = len(linhas) // 2

# Separa as listas
lista_1 = linhas[:metade]
lista_2 = linhas[metade:]

# Cria o arquivo para o PC 1 na pasta correta
with open(caminho_metade_1, "w", encoding="utf-8") as f1:
    f1.writelines(lista_1)

# Cria o arquivo para o PC 2 na pasta correta
with open(caminho_metade_2, "w", encoding="utf-8") as f2:
    f2.writelines(lista_2)

print(f"✅ Sucesso! O arquivo original tinha {len(linhas)} Pokémon.")
print(f"💻 PC 1: 'lista_metade_1.txt' gerado com {len(lista_1)} Pokémon na pasta get_names/data.")
print(f"💻 PC 2: 'lista_metade_2.txt' gerado com {len(lista_2)} Pokémon na pasta get_names/data.")