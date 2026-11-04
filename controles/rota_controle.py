"""Controller de rotas: valida entrada, chama OSRM, calcula tempos e salva."""

import json

from config import AREA, PERFIS
from controles.respostas import json_resposta
from modelo import rota as rota_modelo
from servicos import osrm, tempo


def _ponto(dados, nome):
    """Aceita {"origem": {"lat": .., "lon": ..}} ou {"origem": "lat,lon"}."""
    bruto = dados.get(nome)

    if isinstance(bruto, dict):
        try:
            return {"lat": float(bruto.get("lat")), "lon": float(bruto.get("lon"))}
        except (TypeError, ValueError):
            return None

    if isinstance(bruto, str) and bruto.strip():
        partes = bruto.replace(";", ",").split(",")
        if len(partes) == 2:
            try:
                return {"lat": float(partes[0]), "lon": float(partes[1])}
            except ValueError:
                return None

    # formato alternativo: origem_lat / origem_lon
    lat = dados.get(f"{nome}_lat")
    lon = dados.get(f"{nome}_lon")
    if lat is not None and lon is not None:
        try:
            return {"lat": float(lat), "lon": float(lon)}
        except (TypeError, ValueError):
            return None

    return None


def _valido(ponto):
    return ponto is not None and -90 <= ponto["lat"] <= 90 and -180 <= ponto["lon"] <= 180


def _dentro_da_area(ponto):
    """O recorte do OSRM cobre só Parauapebas; fora dele a rota sairia errada."""
    return (
        AREA["sul"] <= ponto["lat"] <= AREA["norte"]
        and AREA["oeste"] <= ponto["lon"] <= AREA["leste"]
    )


def api_perfis(dados):
    """GET /api/perfis — perfis disponíveis e velocidades usadas."""
    return json_resposta(PERFIS)


def api_rota(dados):
    """POST /api/rota — calcula a rota e devolve tempo para cada perfil."""
    origem = _ponto(dados, "origem")
    destino = _ponto(dados, "destino")

    if not _valido(origem):
        return json_resposta({"erro": "origem inválida (use lat,lon)"}, 400)
    if not _valido(destino):
        return json_resposta({"erro": "destino inválido (use lat,lon)"}, 400)

    for nome, ponto in (("origem", origem), ("destino", destino)):
        if not _dentro_da_area(ponto):
            return json_resposta(
                {
                    "erro": f"{nome} fora da área de Parauapebas",
                    "area": AREA,
                },
                400,
            )

    try:
        rota = osrm.calcular_rota(origem, destino)
    except osrm.ErroRota as erro:
        return json_resposta({"erro": str(erro)}, 502)

    tempos = tempo.calcular_tempos(rota["distancia_m"])

    resposta = {
        "ok": True,
        "origem": origem,
        "destino": destino,
        "distancia_m": round(rota["distancia_m"], 1),
        "distancia_km": round(rota["distancia_m"] / 1000, 2),
        "duracao_osrm_s": round(rota["duracao_s"], 1),
        "tempos": tempos,
        "geometria": rota["geometria"],
        "salvo": False,
        "id": None,
    }

    try:
        resposta["id"] = rota_modelo.salvar(
            origem,
            destino,
            rota["geometria"],
            rota["distancia_m"],
            rota["duracao_s"],
            tempos,
        )
        resposta["salvo"] = resposta["id"] is not None
    except Exception as erro:  # noqa: BLE001 - rota válida mesmo sem banco
        resposta["aviso"] = f"rota não salva no banco: {erro}"

    return json_resposta(resposta)


def api_historico(dados):
    """GET /api/historico?limite=20 — últimas rotas calculadas."""
    try:
        limite = int(dados.get("limite", 20))
    except (TypeError, ValueError):
        limite = 20

    limite = max(1, min(limite, 200))

    try:
        rotas = rota_modelo.listar(limite)
    except Exception as erro:  # noqa: BLE001
        return json_resposta({"erro": f"falha ao consultar o banco: {erro}"}, 503)

    for item in rotas:
        item["criado_em"] = item["criado_em"].isoformat()

    return json_resposta({"rotas": rotas})


def api_rota_detalhe(dados):
    """GET /api/rota?id=1 — uma rota salva, com geometria."""
    try:
        rota_id = int(dados.get("id", 0))
    except (TypeError, ValueError):
        return json_resposta({"erro": "id inválido"}, 400)

    try:
        item = rota_modelo.buscar(rota_id)
    except Exception as erro:  # noqa: BLE001
        return json_resposta({"erro": f"falha ao consultar o banco: {erro}"}, 503)

    if not item:
        return json_resposta({"erro": "rota não encontrada"}, 404)

    item["criado_em"] = item["criado_em"].isoformat()
    return json_resposta(item)


def api_status(dados):
    """GET /api/status — diagnóstico rápido (banco e OSRM)."""
    from db import database

    banco_ok = database.disponivel()
    osrm_ok = False
    try:
        osrm.calcular_rota({"lat": -6.0678, "lon": -49.9022}, {"lat": -6.0700, "lon": -49.9000})
        osrm_ok = True
    except osrm.ErroRota:
        osrm_ok = False

    return json_resposta({"banco": banco_ok, "osrm": osrm_ok})
