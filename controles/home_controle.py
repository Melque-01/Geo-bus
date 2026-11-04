"""Controller da página inicial."""

from controles.respostas import render


def index(dados):
    """GET / — renderiza o mapa."""
    return render("index.html", titulo="Geo Buss — rotas e tempos")
