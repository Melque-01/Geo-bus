"""Servidor HTTP da aplicação (MVC sem framework).

Responsabilidades deste arquivo:
- subir o servidor e escutar requisições;
- servir arquivos de `static/`;
- transformar a requisição em um dicionário `dados`;
- achar a função correspondente em `rotas/rotas.py` e devolver a resposta.

Execução:
    python app.py
"""

import json
import mimetypes
import os
import posixpath
import traceback
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import config
from controles import respostas
from rotas.rotas import ROTAS

RAIZ = os.path.dirname(os.path.abspath(__file__))
PASTA_STATIC = os.path.join(RAIZ, "static")


class Manipulador(BaseHTTPRequestHandler):
    """Converte HTTP em chamadas para os controllers registrados em ROTAS."""

    server_version = "GeoBuss/1.0"

    def do_GET(self):
        self._despachar("GET")

    def do_POST(self):
        self._despachar("POST")

    def do_PUT(self):
        self._despachar("PUT")

    def do_DELETE(self):
        self._despachar("DELETE")

    def _despachar(self, metodo):
        url = urllib.parse.urlparse(self.path)
        caminho = "/" + url.path.strip("/")

        if caminho.startswith("/static/"):
            return self._servir_static(caminho)

        dados = {chave: valores[0] for chave, valores in urllib.parse.parse_qs(url.query).items()}
        if metodo in ("POST", "PUT", "DELETE"):
            dados.update(self._ler_corpo())

        funcao = ROTAS.get((metodo, caminho))
        if funcao is None:
            return self._enviar(*respostas.json_resposta({"erro": "rota não encontrada"}, 404))

        try:
            status, cabecalhos, corpo = funcao(dados)
        except Exception as erro:  # noqa: BLE001 - falha inesperada vira 500
            traceback.print_exc()
            return self._enviar(
                *respostas.json_resposta({"erro": f"erro interno: {erro}"}, 500)
            )

        self._enviar(status, cabecalhos, corpo)

    def _ler_corpo(self):
        """Lê o corpo da requisição e devolve um dicionário."""
        tamanho = int(self.headers.get("content-length") or 0)
        if tamanho <= 0:
            return {}

        bruto = self.rfile.read(tamanho).decode("utf-8", errors="replace")
        tipo = (self.headers.get("content-type") or "").lower()

        if "application/json" in tipo:
            try:
                conteudo = json.loads(bruto)
            except json.JSONDecodeError:
                return {}
            return conteudo if isinstance(conteudo, dict) else {}

        return {chave: valores[0] for chave, valores in urllib.parse.parse_qs(bruto).items()}

    def _servir_static(self, caminho):
        """Entrega arquivos de `static/` bloqueando path traversal."""
        relativo = posixpath.normpath(urllib.parse.unquote(caminho[len("/static/"):]))
        if relativo.startswith(".."):
            return self._enviar(*respostas.json_resposta({"erro": "acesso negado"}, 403))

        arquivo = os.path.join(PASTA_STATIC, relativo)
        if not os.path.isfile(arquivo):
            return self._enviar(*respostas.json_resposta({"erro": "arquivo não encontrado"}, 404))

        tipo = mimetypes.guess_type(arquivo)[0] or "application/octet-stream"
        if tipo.startswith("text/") or tipo in ("application/javascript", "application/json"):
            tipo += "; charset=utf-8"

        with open(arquivo, "rb") as f:
            corpo = f.read()

        self._enviar(200, {"content-type": tipo}, corpo)

    def _enviar(self, status, cabecalhos, corpo):
        self.send_response(status)
        for nome, valor in cabecalhos.items():
            self.send_header(nome, valor)
        self.send_header("content-length", str(len(corpo)))
        self.end_headers()
        if corpo:
            self.wfile.write(corpo)

    def log_message(self, formato, *args):
        print(f"[{self.log_date_time_string()}] {formato % args}")


def main():
    try:
        from db.database import criar_tabelas

        criar_tabelas()
        print("Banco: schema aplicado.")
    except Exception as erro:  # noqa: BLE001 - app sobe mesmo sem banco
        print(f"AVISO: sem banco de dados ({erro}). Rotas serão calculadas, mas não salvas.")

    servidor = ThreadingHTTPServer((config.HOST, config.PORTA), Manipulador)
    print(f"Servidor em http://{config.HOST}:{config.PORTA} (Ctrl+C para parar)")
    print(f"OSRM: {config.OSRM_URL}")
    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        print("\nEncerrando.")
    finally:
        servidor.server_close()


if __name__ == "__main__":
    main()
