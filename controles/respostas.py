"""Helpers de resposta: HTML, JSON e redirecionamento.

Toda resposta segue o formato (status, cabeçalhos, corpo_em_bytes).
"""

import html
import json
import os

PASTA_TEMPLATES = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "templates"
)


def escapar(texto):
    """Escapa HTML para evitar injeção em templates."""
    return html.escape(str(texto))


def render(nome_template, **variaveis):
    """Carrega um template e substitui os marcadores {{chave}}."""
    caminho = os.path.join(PASTA_TEMPLATES, nome_template)
    with open(caminho, encoding="utf-8") as arquivo:
        pagina = arquivo.read()

    for chave, valor in variaveis.items():
        pagina = pagina.replace("{{" + chave + "}}", escapar(valor))

    return 200, {"content-type": "text/html; charset=utf-8"}, pagina.encode("utf-8")


def redirecionar(url, status=303):
    return status, {"location": url}, b""


def json_resposta(objeto, status=200):
    corpo = json.dumps(objeto, ensure_ascii=False).encode("utf-8")
    return status, {"content-type": "application/json; charset=utf-8"}, corpo
