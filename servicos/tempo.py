"""Cálculo de tempo de viagem por perfil.

velocidade (km/h) -> tempo (min):  distancia_km / velocidade_kmh * 60
"""

from config import PERFIS


def calcular_tempos(distancia_m):
    """Devolve um dicionário com o tempo estimado de cada perfil."""
    distancia_km = float(distancia_m) / 1000.0
    tempos = {}

    for chave, perfil in PERFIS.items():
        velocidade = float(perfil["velocidade_kmh"]) or 1.0
        minutos = (distancia_km / velocidade) * 60.0
        tempos[chave] = {
            "perfil": chave,
            "rotulo": perfil["rotulo"],
            "velocidade_kmh": velocidade,
            "tempo_min": round(minutos, 1),
        }

    return tempos
