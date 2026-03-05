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

dir_path = Path(__file__).parent
path_txt = dir_path.parent / "get_names" / "data" / "lista_pokemons_pvpivs.txt"

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
    
    servico = Service(ChromeDriverManager().install())
    return webdriver.Chrome(service=servico, options=opcoes)

def extrair_dados_lote():
    arquivo_json = "dados_pvp_ivs.json"
    
    # Verifica se o arquivo de nomes existe
    if not os.path.exists(path_txt):
        print(f"⚠️ Erro: O arquivo '{path_txt}' não foi encontrado. Execute o get_names.py primeiro.")
        return
        
    # Lê todos os nomes, ignorando linhas vazias
    with open(path_txt, "r", encoding="utf-8") as f:
        nomes_pokemon = [linha.strip() for linha in f if linha.strip()]
        
    print(f"📋 Encontrados {len(nomes_pokemon)} Pokémon para processar.")
    
    # Carrega o JSON existente se houver, para não sobrescrever caso você pare e volte
    dados_finais = {}
    if os.path.exists(arquivo_json):
        with open(arquivo_json, "r", encoding="utf-8") as f:
            try:
                dados_finais = json.load(f)
            except json.JSONDecodeError:
                dados_finais = {}

    # Define as ligas e seus parâmetros de CP no site (10000 representa a Master League Level 50)
    ligas = {
        "great": 1500,
        "ultra": 2500,
        "master": 10000 
    }
    
    driver = iniciar_driver()
    
    # --- AJUSTE 1: Configuração do limite de tempo ---
    tempo_inicio = time.time()
    tempo_limite = 5.5 * 60 * 60 # 5 horas e meia em segundos
    processados_agora = 0 # Contador para sabermos quando fizer o git push
    
    try:
        for index, nome in enumerate(nomes_pokemon, 1):
            
            # --- AJUSTE 1 (Continuação): Checa se estourou o limite de tempo ---
            tempo_decorrido = time.time() - tempo_inicio
            if tempo_decorrido > tempo_limite:
                print("\n⏳ Tempo limite de segurança (5h30m) atingido. Encerrando para evitar corte brusco do GitHub...")
                break # Sai do laço e vai direto pro 'finally'
            
            # Pula o Pokémon se ele já estiver completo no JSON
            if nome in dados_finais and len(dados_finais[nome]) == 3:
                print(f"[{index}/{len(nomes_pokemon)}] {nome} já processado. Pulando...")
                continue
                
            print(f"\n[{index}/{len(nomes_pokemon)}] Processando: {nome}...")
            dados_finais[nome] = {}
            
            for nome_liga, cp_liga in ligas.items():
                url = f"https://pvpivs.com/?mon={nome}&r=99&cp={cp_liga}"
                driver.get(url)
                
                valores_cp = []
                valores_iv_ataque = set()
                valores_iv_defesa = set()
                valores_iv_ps = set()
                ranks_validados = 0
                
                try:
                    # Espera mais curta (5s) para não travar muito tempo caso a tabela falhe
                    WebDriverWait(driver, 5).until(
                        EC.presence_of_element_located((By.XPATH, "//table//tbody/tr"))
                    )
                    time.sleep(1.5) # Tempo rápido de estabilização do DOM
                    
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
                                
                    # Populando o dicionário da liga atual
                    if ranks_validados > 0:
                        dados_finais[nome][nome_liga] = {
                            "iv_ataque": organizar_ivs(valores_iv_ataque),
                            "iv_defesa": organizar_ivs(valores_iv_defesa),
                            "iv_ps": organizar_ivs(valores_iv_ps),
                            "range_cp": [min(valores_cp), max(valores_cp)] if valores_cp else []
                        }
                    else:
                        dados_finais[nome][nome_liga] = None # Caso o Pokémon não seja elegível pra liga
                        
                except TimeoutException:
                    print(f"   -> Timeout ao carregar liga {nome_liga} para {nome}.")
                    dados_finais[nome][nome_liga] = None
                except Exception as e:
                    print(f"   -> Erro inesperado na liga {nome_liga}: {e}")
                    dados_finais[nome][nome_liga] = None
            
            # Salva o progresso LOCALMENTE no JSON a cada Pokémon finalizado
            with open(arquivo_json, "w", encoding="utf-8") as f:
                json.dump(dados_finais, f, indent=4, ensure_ascii=False)
            
            processados_agora += 1
            
            # --- AJUSTE 2: Faz o Commit e Push no GitHub a cada 10 Pokémon novos ---
            if processados_agora % 10 == 0:
                print(f"📦 Salvando lote de 10 Pokémon no repositório GitHub...")
                os.system('git config --global user.name "GitHub Actions Bot"')
                os.system('git config --global user.email "actions@github.com"')
                os.system(f'git add {arquivo_json}')
                os.system('git commit -m "🤖 Lote parcial salvo automaticamente"')
                os.system('git push')
                
            # Pequena pausa para não sobrecarregar o servidor do pvpivs
            time.sleep(1) 
            
    finally:
        print("\n✅ Extração finalizada ou interrompida. Fechando o navegador...")
        driver.quit()

# Inicia a execução
extrair_dados_lote()