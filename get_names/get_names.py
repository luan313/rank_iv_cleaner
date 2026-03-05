import requests
import re

def extrair_apenas_pokelist():
    url = "https://pvpivs.com/includes/pokeListObj.js"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    
    print(f"Baixando dados de: {url}...")
    resposta = requests.get(url, headers=headers)
    
    if resposta.status_code == 200:
        conteudo_js = resposta.text
        
        # Passo 1: Isolar apenas a parte do arquivo que nos interessa
        if "pokeListObj={" not in conteudo_js:
            print("❌ Não foi possível encontrar a declaração 'pokeListObj={' no arquivo.")
            return
            
        # Divide o texto em duas partes e pega tudo que vem DEPOIS de "pokeListObj={"
        bloco_pokelist = conteudo_js.split("pokeListObj={")[1]
        
        # Passo 2: O Regex perfeito para o formato Bulbasaur:"..."
        # Busca palavras que começam com Letra Maiúscula, seguidas imediatamente por dois-pontos e aspas duplas
        padrao = r'([A-Z][A-Za-z0-9_]+):"'
        
        # Roda a busca APENAS no bloco isolado
        nomes = re.findall(padrao, bloco_pokelist)
        
        # Removendo duplicatas (caso existam) e ordenando
        nomes_unicos = sorted(list(set(nomes)))
        
        if not nomes_unicos:
            print("❌ Não foi possível extrair os nomes do pokeListObj.")
            return

        print(f"✅ Sucesso! Foram extraídos {len(nomes_unicos)} Pokémon diretamente do pokeListObj.")
        
        with open(r"data\lista_pokemons_pvpivs.txt", "w", encoding="utf-8") as arquivo:
            for nome in nomes_unicos:
                arquivo.write(nome + "\n")
                
        print("A lista limpa foi salva em 'lista_pokemons_pvpivs.txt'.")
        
    else:
        print(f"Falha ao acessar o site. Código HTTP: {resposta.status_code}")

# Executa o script
extrair_apenas_pokelist()