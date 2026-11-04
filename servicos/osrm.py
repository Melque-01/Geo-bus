"""Cliente do osrm-backend.

Usado apenas para geometria e distância. O tempo por perfil é calculado em
`servicos.tempo` — o OSRM aqui roda com um único perfil ("driving").
"""

import json
import urllib.error
import urllib.parse
import urllib.request

from config import OSRM_TIMEOUT, OSRM_URL


class ErroRota(Exception):
    """Falha ao obter rota do OSRM (serviço fora, sem caminho, coordenada inválida)."""


def calcular_rota(origem, destino):
    """Retorna distancia_m, duracao_s (OSRM) e geometria GeoJSON.

    origem/destino: {"lat": float, "lon": float}
    """
    coordenadas = (
        f"{origem['lon']},{origem['lat']};"
        f"{destino['lon']},{destino['lat']}"
    )
    consulta = urllib.parse.urlencode(
        {"overview": "full", "geometries": "geojson", "steps": "false"}
    )
    url = f"{OSRM_URL}/route/v1/driving/{coordenadas}?{consulta}"

    try:
        with urllib.request.urlopen(url, timeout=OSRM_TIMEOUT) as resposta:
            dados = json.loads(resposta.read().decode("utf-8"))
    except urllib.error.HTTPError as erro:
        raise ErroRota(f"OSRM respondeu HTTP {erro.code}") from erro
    except (urllib.error.URLError, TimeoutError, OSError) as erro:
        raise ErroRota(f"OSRM indisponível em {OSRM_URL}: {erro}") from erro
    except json.JSONDecodeError as erro:
        raise ErroRota("OSRM devolveu resposta inválida") from erro

    if dados.get("code") != "Ok" or not dados.get("routes"):
        raise ErroRota(f"sem rota entre os pontos ({dados.get('code')})")

    rota = dados["routes"][0]
    return {
        "distancia_m": float(rota["distance"]),
        "duracao_s": float(rota.get("duration") or 0),
        "geometria": rota["geometry"],
    }
