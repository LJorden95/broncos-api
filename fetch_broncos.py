import requests
import json
import os
from datetime import datetime, timezone, timedelta

# Dicionários de tradução para PT-BR
DIAS_SEMANA = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"]
MESES = ["", "Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"]

def buscar_jogos_broncos():
    pasta_atual = os.path.dirname(__file__)
    agora = datetime.now(timezone.utc)
    br_tz = timezone(timedelta(hours=-3))
    cache_records = {}

    def baixar_imagem_com_cache(url, nome_arquivo):
        caminho = os.path.join(pasta_atual, nome_arquivo)
        if not os.path.exists(caminho) and url:
            try:
                img_data = requests.get(url, timeout=5).content
                with open(caminho, "wb") as f:
                    f.write(img_data)
            except Exception as e:
                print(f"Erro ao baixar {nome_arquivo}: {e}")
        return nome_arquivo

    def obter_record_time_api(team_id):
        if team_id in cache_records:
            return cache_records[team_id]
        try:
            url_team = f"https://site.api.espn.com/apis/site/v2/sports/football/nfl/teams/{team_id}"
            resp = requests.get(url_team, timeout=5).json()
            record_items = resp.get("team", {}).get("record", {}).get("items", [])
            if record_items:
                rec = record_items[0].get("summary", "0-0")
                cache_records[team_id] = rec
                return rec
        except Exception:
            pass
        cache_records[team_id] = "0-0"
        return "0-0"

    # 1. Record Geral do Broncos (ID 7)
    record_atual_broncos = obter_record_time_api("7")
    try:
        url_team = "https://site.api.espn.com/apis/site/v2/sports/football/nfl/teams/7"
        resp_team = requests.get(url_team, timeout=5).json()
        logo_broncos_url = resp_team["team"]["logos"][0]["href"]
        baixar_imagem_com_cache(logo_broncos_url, "broncos.png")
    except Exception as e:
        print(f"Erro ao obter logo principal: {e}")

    # 2. Busca Calendário
    season_types = [1, 2]
    todos_eventos = []
    
    for stype in season_types:
        url = f"https://site.api.espn.com/apis/site/v2/sports/football/nfl/teams/7/schedule?seasontype={stype}"
        try:
            resp = requests.get(url, timeout=10)
            if resp.status_code == 200:
                events = resp.json().get("events", [])
                todos_eventos.extend(events)
        except Exception as e:
            print(f"Erro seasontype={stype}: {e}")

    jogos_processados = []
    vitorias_broncos = 0
    derrotas_broncos = 0
    empates_broncos = 0

    for event in todos_eventos:
        date_str = event.get("date")
        if not date_str:
            continue
            
        try:
            game_date = datetime.strptime(date_str, "%Y-%m-%dT%H:%MZ").replace(tzinfo=timezone.utc)
        except Exception:
            continue

        competition = event["competitions"][0]
        nome = event.get("name", "N/A").replace('"', '')
        competitors = competition.get("competitors", [])

        adversario = "N/A"
        logo_url = ""
        team_id = "0"
        rec_adv_partida = "0-0"

        for comp in competitors:
            t_id = str(comp.get("team", {}).get("id"))
            records_list = comp.get("records", [])
            if records_list:
                rec_adv_partida = records_list[0].get("summary", "0-0")

            if t_id != "7":
                team_data = comp.get("team", {})
                adversario = team_data.get("displayName", "N/A").replace('"', '')
                team_id = t_id
                logos = team_data.get("logos", [])
                if logos:
                    logo_url = logos[0].get("href", "")

        if rec_adv_partida == "0-0" and team_id != "0":
            record_adv = obter_record_time_api(team_id)
        else:
            record_adv = rec_adv_partida

        local = competition.get("venue", {}).get("fullName", "N/A").replace('"', '')

        broadcasts = competition.get("broadcasts", [])
        tv_list = []
        for b in broadcasts:
            tv_list.extend(b.get("names", []))
        transmissao = ", ".join(tv_list) if tv_list else "Sem transmissao"
        transmissao = transmissao.replace('"', '').replace('\\', '')

        # --- CONVERSÃO DA DATA E HORA TRADUZIDA EM PT-BR ---
        game_date_br = game_date.astimezone(br_tz)
        
        dia_semana_str = DIAS_SEMANA[game_date_br.weekday()]
        mes_str = MESES[game_date_br.month]
        dia_num = game_date_br.strftime("%d")
        hora_str = game_date_br.strftime("%Hh%M")

        # Exemplo final: "Sex, 14 Ago"
        data_formatada = f"{dia_semana_str}, {dia_num} {mes_str}"
        # Exemplo final: "20h00"
        hora_formatada = hora_str

        status_type = event.get("status", {}).get("type", {}).get("state", "")

        if status_type == "post" or game_date <= agora:
            scores = []
            broncos_score = 0
            adv_score = 0
            
            for comp in competitors:
                t_id = str(comp.get("team", {}).get("id"))
                t_name = comp.get("team", {}).get("abbreviation", "")
                raw_score = comp.get("score", "0")
                val = int(raw_score.get("value", 0)) if isinstance(raw_score, dict) else int(raw_score)
                
                if t_id == "7":
                    broncos_score = val
                else:
                    adv_score = val
                    
                scores.append(f"{t_name} {val}")

            if broncos_score > adv_score:
                vitorias_broncos += 1
            elif broncos_score < adv_score:
                derrotas_broncos += 1
            else:
                empates_broncos += 1

            rec_broncos_str = f"{vitorias_broncos}-{derrotas_broncos}" + (f"-{empates_broncos}" if empates_broncos > 0 else "")
            info_status = f"Placar: {' | '.join(scores)} (DEN {rec_broncos_str})"
        else:
            info_status = f"Transmissao: {transmissao}"

        nome_escudo = f"team_{team_id}.png"
        baixar_imagem_com_cache(logo_url, nome_escudo)

        jogos_processados.append({
            "nome": nome,
            "data": data_formatada,
            "hora": hora_formatada,
            "adversario": adversario,
            "record_adv": f"({record_adv})",
            "local": local,
            "status_info": info_status,
            "escudo_file": nome_escudo,
            "game_date": game_date
        })

    jogos_processados.sort(key=lambda x: x["game_date"])

    resultado = {
        "broncos_record_geral": record_atual_broncos
    }
    for idx, jogo in enumerate(jogos_processados, start=1):
        resultado[f"j{idx}_nome"] = jogo["nome"]
        resultado[f"data{idx}"] = jogo["data"]
        resultado[f"hora{idx}"] = jogo["hora"]
        resultado[f"adv{idx}"] = f"{jogo['adversario']} {jogo['record_adv']}"
        resultado[f"loc{idx}"] = jogo["local"]
        resultado[f"trans{idx}"] = jogo["status_info"]
        resultado[f"escudo{idx}"] = jogo["escudo_file"]

    caminho_json = os.path.join(pasta_atual, "dados.json")
    with open(caminho_json, "w", encoding="utf-8") as f:
        json.dump(resultado, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    buscar_jogos_broncos()
