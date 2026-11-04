"""Tabela de rotas da aplicação.

Formato: (MÉTODO, CAMINHO) -> função do controller.

Toda função recebe um dicionário `dados` (query string + corpo) e devolve
a tupla (status, cabeçalhos, corpo_em_bytes).
"""

from controles import home_controle, rota_controle

ROTAS = {
    ("GET", "/"): home_controle.index,
    ("GET", "/api/perfis"): rota_controle.api_perfis,
    ("POST", "/api/rota"): rota_controle.api_rota,
    ("GET", "/api/rota"): rota_controle.api_rota_detalhe,
    ("GET", "/api/historico"): rota_controle.api_historico,
    ("GET", "/api/status"): rota_controle.api_status,
}
