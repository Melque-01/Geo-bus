"""Configurações do projeto.

Lê o arquivo `.env` (se existir) e expõe os valores usados pelo resto do
código. Nada aqui acessa a rede ou o banco.
"""

import os
from pathlib import Path

RAIZ = Path(__file__).resolve().parent


def _carregar_env(caminho=RAIZ / ".env"):
    """Lê pares CHAVE=VALOR do .env sem dependência externa."""
    if not caminho.exists():
        return
    for linha in caminho.read_text(encoding="utf-8").splitlines():
        linha = linha.strip()
        if not linha or linha.startswith("#") or "=" not in linha:
            continue
        chave, valor = linha.split("=", 1)
        os.environ.setdefault(chave.strip(), valor.strip().strip('"').strip("'"))


_carregar_env()

# --- Servidor -------------------------------------------------------------
HOST = os.getenv("HOST", "127.0.0.1")
PORTA = int(os.getenv("PORTA", "8000"))

# --- PostgreSQL / PostGIS -------------------------------------------------
BANCO = {
    "host": os.getenv("DB_HOST", "127.0.0.1"),
    "port": int(os.getenv("DB_PORT", "5432")),
    "dbname": os.getenv("DB_NAME", "geo_buss"),
    "user": os.getenv("DB_USER", "geo_buss"),
    "password": os.getenv("DB_PASSWORD", "geo_buss"),
    "connect_timeout": int(os.getenv("DB_TIMEOUT", "5")),
}

# --- OSRM -----------------------------------------------------------------
# Base da API do osrm-backend (perfil "driving").
OSRM_URL = os.getenv("OSRM_URL", "http://127.0.0.1:5000").rstrip("/")
OSRM_TIMEOUT = float(os.getenv("OSRM_TIMEOUT", "15"))

# --- Área de atendimento ---------------------------------------------------
# Recorte coberto pelo OSRM. Pontos fora daqui seriam "encaixados" na borda e
# gerariam rotas falsas, então são recusados. Formato: oeste,sul,leste,norte.
_BBOX_PADRAO = "-50.05,-6.20,-49.75,-5.95"


def _ler_area(bruto):
    try:
        oeste, sul, leste, norte = (float(parte) for parte in bruto.split(","))
    except (AttributeError, ValueError):
        oeste, sul, leste, norte = (float(parte) for parte in _BBOX_PADRAO.split(","))
    return {"oeste": oeste, "sul": sul, "leste": leste, "norte": norte}


AREA = _ler_area(os.getenv("AREA_BBOX", _BBOX_PADRAO))

# --- Perfis e velocidades médias (km/h) -----------------------------------
# O OSRM entrega apenas a geometria/distância; o tempo é calculado aqui.
# Ajuste conforme o trânsito real de Parauapebas.
PERFIS = {
    "carro": {
        "rotulo": "Carro",
        "velocidade_kmh": float(os.getenv("VEL_CARRO", "30")),
    },
    "moto": {
        "rotulo": "Moto",
        "velocidade_kmh": float(os.getenv("VEL_MOTO", "35")),
    },
    "bicicleta": {
        "rotulo": "Bicicleta",
        "velocidade_kmh": float(os.getenv("VEL_BICICLETA", "15")),
    },
    "pe": {
        "rotulo": "A pé",
        "velocidade_kmh": float(os.getenv("VEL_PE", "4.8")),
    },
}
