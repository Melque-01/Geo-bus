"""Model da entidade `rotas` (histórico de rotas calculadas)."""

import json

from db.database import consultar, consultar_um, inserir

CAMPOS_RESUMO = """
    id,
    distancia_m,
    duracao_osrm_s,
    tempos,
    ST_AsGeoJSON(origem)::json  AS origem,
    ST_AsGeoJSON(destino)::json AS destino,
    criado_em
"""


def salvar(origem, destino, geometria, distancia_m, duracao_osrm_s, tempos):
    """Grava uma rota calculada e devolve o id."""
    return inserir(
        """
        INSERT INTO rotas
            (origem, destino, geometria, distancia_m, duracao_osrm_s, tempos)
        VALUES
            (ST_SetSRID(ST_MakePoint(%s, %s), 4326),
             ST_SetSRID(ST_MakePoint(%s, %s), 4326),
             ST_GeomFromGeoJSON(%s),
             %s, %s, %s::jsonb)
        RETURNING id
        """,
        (
            origem["lon"],
            origem["lat"],
            destino["lon"],
            destino["lat"],
            json.dumps(geometria),
            distancia_m,
            duracao_osrm_s,
            json.dumps(tempos),
        ),
    )


def listar(limite=20):
    """Últimas rotas calculadas, sem geometria."""
    return consultar(
        f"SELECT {CAMPOS_RESUMO} FROM rotas ORDER BY criado_em DESC LIMIT %s",
        (int(limite),),
    )


def buscar(rota_id):
    """Uma rota completa, incluindo a geometria em GeoJSON."""
    return consultar_um(
        f"""
        SELECT {CAMPOS_RESUMO},
               ST_AsGeoJSON(geometria)::json AS geometria
        FROM rotas
        WHERE id = %s
        """,
        (int(rota_id),),
    )
