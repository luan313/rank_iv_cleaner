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
arquivo_json.parent.mkdir(parents=True, exist_ok=True)

def organizar_ivs(conjunto_ivs):
    """Função auxiliar para converter o set em lista de inteiros ordenada."""
    return sorted([int(x) for x in conjunto_ivs if x.isdigit()])

def iniciar_driver():
    """Inicializa e retorna uma única instância do navegador."""
    opcoes = webdriver.ChromeOptions()
    
    # 🕵️ MODO DE DEPURAÇÃO: Comentamos o Headless para o Chrome abrir na tela!
    # opcoes.add_argument('--headless')
    
    opcoes.add_argument('--disable-gpu')
    opcoes.add_argument('--no-sandbox')
    opcoes.add_argument('--log-level=3') 
    opcoes.page_load_strategy = 'eager' 
    
    servico = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=servico, options=opcoes)
    driver.set_page_load_timeout(60) 
    
    return driver

def extrair_dados_lote():
    if not os.path.exists(path_txt):
        print(f"⚠️ Erro: O arquivo '{path_txt}' não foi encontrado.")
        return
        
    nomes_pokemon_todos = []
    metadados_pokemon = {}

    with open(path_txt, "r", encoding="utf-8") as f:
        for linha in f:
            if not linha.strip(): continue
            
            partes = linha.strip().split(",")
            nome = partes[0]
            dex = int(partes[1]) if len(partes) > 1 and partes[1].isdigit() else 0
            family = partes[2] if len(partes) > 2 else "none"
            
            nomes_pokemon_todos.append(nome)
            metadados_pokemon[nome] = {"dex": dex, "family": family}
        
    dados_finais = {}
    if os.path.exists(arquivo_json):
        with open(arquivo_json, "r", encoding="utf-8") as f:
            try:
                dados_finais = json.load(f)
            except json.JSONDecodeError:
                dados_finais = {}

    # ✔️ CORREÇÃO: Reprocessar os valores "null" se eles existirem
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

    ligas = {"great": 1500, "ultra": 2500, "master": 10000}
    driver = iniciar_driver()
    
    tempo_inicio = time.time()
    tempo_limite = 5.5 * 60 * 60 
    processados_agora = 0 
    
    try:
        for index, nome in enumerate(nomes_pendentes, 1):
            
            tempo_decorrido = time.time() - tempo_inicio
            if tempo_decorrido > tempo_limite:
                print("\n⏳ Tempo limite atingido. Encerrando de forma segura...")
                break 
                
            print(f"\n[{index}/{len(nomes_pendentes)}] Processando: {nome}...")
            
            # Se for a primeira vez do pokemon ou se estiver reprocessando, garante a base
            if nome not in dados_finais:
                dados_finais[nome] = {}
                
            dados_finais[nome]["dex"] = metadados_pokemon[nome]["dex"]
            dados_finais[nome]["family"] = metadados_pokemon[nome]["family"]
            
            for nome_liga, cp_liga in ligas.items():
                # Pula APENAS se a liga específica já estiver rasada perfeitamente (não for None)
                if dados_finais[nome].get(nome_liga) is not None:
                    continue

                url = f"https://pvpivs.com/?mon={nome}&r=99&cp={cp_liga}"
                sucesso_na_liga = False
                
                for tentativa in range(3):
                    valores_cp = []
                    valores_iv_ataque = set()
                    valores_iv_defesa = set()
                    valores_iv_ps = set()
                    ranks_validados = 0
                    
                    try:
                        driver.get(url)
                        
                        # 🎯 REFINAMENTO DA MIRA: Procuramos especificamente tabelas grandes
                        xpath_tabela = "//table//tbody/tr"
                        
                        WebDriverWait(driver, 10).until(
                            EC.presence_of_element_located((By.XPATH, xpath_tabela))
                        )
                        
                        # 🧠 ESPERA INTELIGENTE: Fica monitorando até o JS inserir os números
                        limite_js = time.time() + 15
                        while time.time() < limite_js:
                            linhas_teste = driver.find_elements(By.XPATH, xpath_tabela)
                            if linhas_teste:
                                colunas_teste = linhas_teste[0].find_elements(By.TAG_NAME, "td")
                                if len(colunas_teste) > 5 and colunas_teste[0].text.strip().isdigit():
                                    break # Sucesso! O JavaScript terminou de carregar os ranks
                            time.sleep(1) 
                        
                        # Puxa a tabela validada
                        linhas = driver.find_elements(By.XPATH, xpath_tabela)
                        
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
                                    
                        if ranks_validados > 0:
                            dados_finais[nome][nome_liga] = {
                                "iv_ataque": organizar_ivs(valores_iv_ataque),
                                "iv_defesa": organizar_ivs(valores_iv_defesa),
                                "iv_ps": organizar_ivs(valores_iv_ps),
                                "range_cp": [min(valores_cp), max(valores_cp)] if valores_cp else []
                            }
                            sucesso_na_liga = True
                            break 
                        else:
                            raise Exception("Tabela vazia ou bloqueio de site.")
                            
                    except TimeoutException:
                        print(f"   -> Site engasgou na liga {nome_liga} ({tentativa + 1}/3). Tentando recarregar...")
                        time.sleep(2) 
                    except Exception as e:
                        print(f"   -> Lentidão/Bloqueio na liga {nome_liga} ({tentativa + 1}/3): {e}")
                        time.sleep(3) 
                
                if not sucesso_na_liga:
                    print(f"   ❌ Falha definitiva ao extrair a liga {nome_liga} para {nome}.")
                    dados_finais[nome][nome_liga] = None
            
            # Salva no disco local imediatamente
            with open(arquivo_json, "w", encoding="utf-8") as f:
                json.dump(dados_finais, f, indent=4, ensure_ascii=False)
            
            processados_agora += 1
            
            # 🛡️ SEGURANÇA LOCAL: Os comandos de Git estão desativados!
            if processados_agora % 10 == 0:
                print(f"📦 Lote de 10 concluído e salvo no seu HD (Envio ao GitHub pausado).")
                # os.system('git config --global user.name "GitHub Actions Bot"')
                # os.system('git config --global user.email "actions@github.com"')
                # os.system(f'git add "{arquivo_json.as_posix()}"')
                # os.system('git commit -m "🤖 Lote parcial salvo automaticamente"')
                # os.system('git push')
                
            time.sleep(1) 
            
    finally:
        print("\n✅ Extração finalizada ou interrompida. Fechando o navegador...")
        driver.quit()

if __name__ == "__main__":
    extrair_dados_lote()