import requests
import os
from pathlib import Path

# Configuração dos caminhos virtuais
dir_path = Path(__file__).parent
path_txt = dir_path.parent / "get_names" / "data" / "lista_pokemons_pvpivs.txt"

def enriquecer_lista():
    if not path_txt.exists():
        print(f"⚠️ Erro: O arquivo '{path_txt}' não foi encontrado. Verifique o caminho.")
        return

    print("Baixando Gamemaster do PvPoke...")
    url_gamemaster = "https://raw.githubusercontent.com/pvpoke/pvpoke/refs/heads/master/src/data/gamemaster/pokemon.json"
    
    try:
        response = requests.get(url_gamemaster)
        response.raise_for_status()
        gamemaster = response.json()
    except Exception as e:
        print(f"❌ Erro ao baixar gamemaster: {e}")
        return

    # 1. Cria um dicionário de busca rápida baseado no Gamemaster
    dicionario_pvpoke = {}
    for poke in gamemaster:
        sp_id = poke.get("speciesId", "").lower()
        dex = poke.get("dex", 0)
        family_id = poke.get("family", {}).get("id", "none") 
        
        dicionario_pvpoke[sp_id] = {"dex": dex, "family": family_id}

    # 2. Lê a nossa lista atual do TXT
    with open(path_txt, "r", encoding="utf-8") as f:
        linhas = [linha.strip() for linha in f if linha.strip()]

    linhas_atualizadas = []
    nao_encontrados = 0

    print("Cruzando dados dos Pokémon...")
    
    # --- DICIONÁRIOS DE CORREÇÃO ---
    # Limpamos os speculatives daqui!
    mapa_nomes = {
        "basculin_hisuian": "basculin",
        "brute_bonnet": "brutebonnet",
        "burmy": "burmy_plant",
        "cherrim": "cherrim_sunny",
        "eiscue_ice_face": "eiscue_ice",
        "eiscue_noice_face": "eiscue_noice",
        "enamorus": "enamorus_incarnate",
        "flutter_mane": "fluttermane",
        "gimmighoul_chest": "gimmighoul",
        "gimmighoul_roaming": "gimmighoul",
        "sliggoo_hisuian" : "sliggoo",
        "goodra_hisuian": "goodra",
        "great_tusk": "greattusk",
        "ice_rider_calyrex": "calyrex",
        "shadow_rider_calyrex": "calyrex",
        "iron_bundle": "ironbundle",
        "iron_hands": "ironhands",
        "iron_jugulis": "ironjugulis",
        "iron_moth": "ironmoth",
        "iron_thorns": "ironthorns",
        "iron_treads": "irontreads",
        "iron_valiant": "ironvaliant",
        "keldeo": "keldeo_ordinary",
        "absol_mega_z": "absol_mega",
        "garchomp_mega_z": "garchomp_mega",
        "lucario_mega_z": "lucario_mega",
        "meganium_mega": "meganium",
        "roaring_moon": "roaringmoon",
        "morpeko": "morpeko_full_belly",
        "oinkologne_male": "oinkologne",
        "oricorio": "oricorio_pom_pom",
        "primal_groudon": "groudon_primal",
        "primal_kyogre": "kyogre_primal",
        "sandy_shocks": "sandyshocks",
        "scream_tail": "screamtail",
        "slither_wing": "slitherwing",
        "tatsugiri": "tatsugiri_curly",
        "tauros_paldean": "tauros",
        "terapagos_normal": "terapagos",
        "terapagos_stellar": "terapagos",
        "terapagos_terastal": "terapagos",
        "ultra_necrozma": "necrozma_ultra",
        "urshifu": "urshifu_rapid_strike",
        "zacian_hero_of_many_battles": "zacian_hero",
        "zamazenta_hero_of_many_battles": "zamazenta_hero",
        "zygarde_fifty_percent": "zygarde",
        "zygarde_ten_percent": "zygarde_10"

    }
    
    mapa_manual = {}

    # 3. Processa cada nome
    for linha in linhas:
        nome = linha.split(",")[0] 
        chave_busca = nome.lower()
        
        # --- REGRAS DINÂMICAS DE FORMATAÇÃO ---
        
        # Regra 1: Transforma "_alola" em "_alolan" 
        if "_alola" in chave_busca and "_alolan" not in chave_busca:
            chave_busca = chave_busca.replace("_alola", "_alolan")
            
        # Regra 2: Joga o 'mega_' para depois do nome base
        if chave_busca.startswith("mega_"):
            partes = chave_busca.split("_")
            if len(partes) == 2: 
                chave_busca = f"{partes[1]}_mega"
            elif len(partes) > 2: 
                chave_busca = f"{partes[1]}_mega_{'_'.join(partes[2:])}"

        # Regra 3: Remove "_speculative" APENAS para a busca no Gamemaster
        if "_speculative" in chave_busca:
            chave_busca = chave_busca.replace("_speculative", "")

        # --------------------------------------
        
        # Se existir uma tradução manual para o nome restante, aplica a tradução
        if chave_busca in mapa_nomes:
            chave_busca = mapa_nomes[chave_busca]
            
        # Tenta procurar no Gamemaster do PvPoke
        if chave_busca in dicionario_pvpoke:
            dex = dicionario_pvpoke[chave_busca]["dex"]
            family = dicionario_pvpoke[chave_busca]["family"]
            
        # Procura no banco manual (se houver)
        elif nome.lower() in mapa_manual:
            dex = mapa_manual[nome.lower()]["dex"]
            family = mapa_manual[nome.lower()]["family"]
            
        # Se não existir em lugar nenhum, dá o aviso
        else:
            dex = 0
            family = "none"
            nao_encontrados += 1
            print(f"  -> Aviso: Dados não encontrados no PvPoke para: {nome}")
            
        # Adiciona na lista atualizada. O 'nome' original intacto vai pro TXT!
        linhas_atualizadas.append(f"{nome},{dex},{family}")

    # 4. Sobrescreve o TXT com a nova formatação
    with open(path_txt, "w", encoding="utf-8") as f:
        for linha in linhas_atualizadas:
            f.write(linha + "\n")

    print(f"\n✅ TXT atualizado com sucesso! {len(linhas_atualizadas)} Pokémon processados.")
    if nao_encontrados > 0:
        print(f"⚠️ {nao_encontrados} Pokémon não tiveram match exato e ficaram com dex 0.")

if __name__ == "__main__":
    enriquecer_lista()