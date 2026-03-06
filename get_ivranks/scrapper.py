from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from webdriver_manager.chrome import ChromeDriverManager
import time
import json
import os
from pathlib import Path

# Configuração de caminhos virtuais
dir_path = Path(__file__).parent
path_txt = dir_path.parent / "get_names" / "data" / "lista_pokemons_pvpivs.txt"

# Caminho para o JSON na pasta data
arquivo_json = dir_path.parent / "data" / "dados_pvp_ivs.json"
# Cria a pasta 'data' automaticamente se ela não existir
arquivo_json.parent.mkdir(parents=True, exist_ok=True)

def organizar_ivs(conjunto_ivs):
    """Função auxiliar para converter o set em lista de inteiros ordenada."""
    return sorted([int(x) for x in conjunto_ivs if x.isdigit()])

def iniciar_driver():
    """Inicializa e retorna uma única instância do navegador."""
    opcoes = webdriver.ChromeOptions()
    opcoes.add_argument('--headless')
    opcoes.add_argument('--disable-gpu')
    opcoes.add_argument('--no-sandbox')
    opcoes.add_argument('--log-level=3') # Suprime logs desnecessários do Chrome no terminal
    
    # ESTRATÉGIA ANTI-TRAVAMENTO: Ignora carregamento de imagens e scripts lentos de anúncios
    opcoes.page_load_strategy = 'eager' 
    
    servico = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=servico, options=opcoes)
    
    # Se a página travar por mais de 30 segundos, força o Timeout para o script tentar de novo
    driver.set_page_load_timeout(30) 
    
    return driver

def extrair_dados_lote():
    # Verifica se o arquivo de nomes existe
    if not os.path.exists(path_txt):
        print(f"⚠️ Erro: O arquivo '{path_txt}' não foi encontrado.")
        return
        
    nomes_pokemon_todos = []
    metadados_pokemon = {} # Vai guardar o Dex e Family temporariamente

    # Lê todos os nomes do TXT, ignorando linhas vazias
    with open(path_txt, "r", encoding="utf-8") as f:
        for linha in f:
            if not linha.strip(): continue
            
            partes = linha.strip().split(",")
            nome = partes[0]
            # Validação caso a pessoa rode o scraper sem ter rodado o script do gamemaster
            dex = int(partes[1]) if len(partes) > 1 and partes[1].isdigit() else 0
            family = partes[2] if len(partes) > 2 else "none"
            
            nomes_pokemon_todos.append(nome)
            metadados_pokemon[nome] = {"dex": dex, "family": family}
        
    # Carrega o JSON existente se houver
    dados_finais = {}
    if os.path.exists(arquivo_json):
        with open(arquivo_json, "r", encoding="utf-8") as f:
            try:
                dados_finais = json.load(f)
            except json.JSONDecodeError:
                dados_finais = {}

    # ATENÇÃO À MUDANÇA AQUI:
    # Como agora o dicionário tem 5 chaves (dex, family, great, ultra, master), 
    # não podemos mais checar se o 'len == 3'. Vamos checar se as 3 ligas existem lá dentro.
    nomes_pendentes = [
        nome for nome in nomes_pokemon_todos 
        if not (
            nome in dados_finais and 
            dados_finais[nome].get("great") is not None and 
            dados_finais[nome].get("ultra") is not None and 
            dados_finais[nome].get("master") is not None
        )
    ]
    
    print(f"📋 Total de Pokémon no TXT: {len(nomes_pokemon_todos)}")
    print(f"🚀 Faltam processar: {len(nomes_pendentes)} Pokémon.")

    if len(nomes_pendentes) == 0:
        print("🎉 Todos os Pokémon já foram processados! O arquivo JSON está completo.")
        return

    # Define as ligas e seus parâmetros de CP no site
    ligas = {
        "great": 1500,
        "ultra": 2500,
        "master": 10000 
    }
    
    driver = iniciar_driver()
    
    # --- AJUSTE DE TEMPO (5h30m) ---
    tempo_inicio = time.time()
    tempo_limite = 5.5 * 60 * 60 # 5 horas e meia em segundos
    processados_agora = 0 # Contador para sabermos quando fazer o git push
    
    try:
        # AGORA ELE SÓ PERCORRE OS PENDENTES
        for index, nome in enumerate(nomes_pendentes, 1):
            
            # Checa se estourou o limite de tempo
            tempo_decorrido = time.time() - tempo_inicio
            if tempo_decorrido > tempo_limite:
                print("\n⏳ Tempo limite de segurança (5h30m) atingido. Encerrando para evitar corte brusco do GitHub...")
                break # Sai do laço e vai direto pro 'finally'
                
            print(f"\n[{index}/{len(nomes_pendentes)}] Processando: {nome}...")
            
            # Inicializa as chaves do Pokémon (sobrescreve se antes estava incompleto)
            dados_finais[nome] = {
                "dex": metadados_pokemon[nome]["dex"],
                "family": metadados_pokemon[nome]["family"]
            }
            
            for nome_liga, cp_liga in ligas.items():
                url = f"https://pvpivs.com/?mon={nome}&r=99&cp={cp_liga}"
                sucesso_na_liga = False
                
                # SISTEMA DE TENTATIVAS: Tenta até 3 vezes carregar a mesma liga caso a internet/site falhe
                for tentativa in range(3):
                    valores_cp = []
                    valores_iv_ataque = set()
                    valores_iv_defesa = set()
                    valores_iv_ps = set()
                    ranks_validados = 0
                    
                    try:
                        driver.get(url)
                        
                        # Espera a tabela aparecer no HTML (mesmo que ainda esteja vazia)
                        WebDriverWait(driver, 5).until(
                            EC.presence_of_element_located((By.XPATH, "//table//tbody/tr"))
                        )
                        
                        # 🛠️ AJUSTE 1: Aumentado para 4.5 segundos! 
                        # Dá tempo para o CPU fraco do GitHub terminar os cálculos do JavaScript
                        time.sleep(4.5) 
                        
                        linhas = driver.find_elements(By.XPATH, "//table//tbody/tr")
                        
                        for linha in linhas:
                            colunas = linha.find_elements(By.TAG_NAME, "td")
                            
                            if len(colunas) > 5:
                                rank_texto = colunas[0].text.strip()
                                if not rank_texto.isdigit():
                                    continue 
                                
                                ranks_validados += 1
                                
                                cp_texto = colunas[2].text.strip()
                                if cp_texto.isdigit():
                                    valores_cp.append(int(cp_texto))
                                    
                                valores_iv_ataque.add(colunas[3].text.strip())
                                valores_iv_defesa.add(colunas[4].text.strip())
                                valores_iv_ps.add(colunas[5].text.strip())
                                
                                if ranks_validados == 99:
                                    break
                                    
                        # Se leu os ranks perfeitamente, salva e SAI do laço de tentativas
                        if ranks_validados > 0:
                            dados_finais[nome][nome_liga] = {
                                "iv_ataque": organizar_ivs(valores_iv_ataque),
                                "iv_defesa": organizar_ivs(valores_iv_defesa),
                                "iv_ps": organizar_ivs(valores_iv_ps),
                                "range_cp": [min(valores_cp), max(valores_cp)] if valores_cp else []
                            }
                            sucesso_na_liga = True
                            break # Quebra o 'for tentativa' pois deu certo
                        else:
                            # 🛠️ AJUSTE 2: Forçamos um erro se a tabela for lida vazia!
                            # Isso faz com que ele caia no 'except' abaixo e tente de novo.
                            raise Exception("A tabela carregou, mas o JavaScript ainda não preencheu os números.")
                            
                    except TimeoutException:
                        print(f"   -> Site engasgou na liga {nome_liga} ({tentativa + 1}/3). Tentando recarregar...")
                        time.sleep(2) 
                    except Exception as e:
                        # 🛠️ Agora o nosso erro forçado cai aqui e o script TENTA DE NOVO!
                        print(f"   -> CPU lento na liga {nome_liga} ({tentativa + 1}/3): {e}")
                        time.sleep(3) # Dá um respiro antes de dar o refresh
                
                # Se falhar nas 3 tentativas, marca como None para não travar o script inteiro
                if not sucesso_na_liga:
                    print(f"   ❌ Falha definitiva ao extrair a liga {nome_liga} para {nome}.")
                    dados_finais[nome][nome_liga] = None
            
            # Salva o progresso LOCALMENTE no JSON a cada Pokémon finalizado
            with open(arquivo_json, "w", encoding="utf-8") as f:
                json.dump(dados_finais, f, indent=4, ensure_ascii=False)
            
            processados_agora += 1
            
            # Faz o Commit e Push no GitHub a cada 10 Pokémon extraídos com sucesso
            if processados_agora % 10 == 0:
                print(f"📦 Salvando lote parcial de 10 Pokémon no repositório GitHub...")
                os.system('git config --global user.name "GitHub Actions Bot"')
                os.system('git config --global user.email "actions@github.com"')
                os.system(f'git add "{arquivo_json.as_posix()}"')
                os.system('git commit -m "🤖 Lote parcial salvo automaticamente (10 Pokemons)"')
                os.system('git push')
                
            # Pequena pausa para não sobrecarregar o servidor do pvpivs
            time.sleep(1) 
            
    finally:
        print("\n✅ Extração finalizada ou interrompida de forma segura. Fechando o navegador...")
        
        # Força um último push antes de desligar a máquina (caso tenha sobrado algo fora do múltiplo de 10)
        if processados_agora > 0 and processados_agora % 10 != 0:
            print("📦 Fazendo push final do que restou na fila...")
            os.system('git config --global user.name "GitHub Actions Bot"')
            os.system('git config --global user.email "actions@github.com"')
            os.system(f'git add "{arquivo_json.as_posix()}"')
            os.system('git commit -m "🤖 Push final da rodada de extração"')
            os.system('git push')
            
        driver.quit()

# Inicia a execução
if __name__ == "__main__":
    extrair_dados_lote()