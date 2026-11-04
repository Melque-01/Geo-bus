"""Cliente SSH da VM de desenvolvimento (uso local, não faz parte da aplicação).

Exemplo:
    python tools/vm.py run "ip -br a"
    python tools/vm.py sudo "apt-get update -y"
    python tools/vm.py put "C:/caminho/arquivo" "/tmp/arquivo"
    python tools/vm.py get "/tmp/arquivo" "C:/caminho/arquivo"
"""

import os
import shlex
import sys

import paramiko

try:  # console do Windows (cp1252) não aceita símbolos do systemd
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except AttributeError:
    pass

HOST = os.getenv("VM_HOST", "")
USER = os.getenv("VM_USER", "")
SENHA = os.getenv("VM_PASSWORD", "")

if not (HOST and USER and SENHA):
    raise SystemExit(
        "defina VM_HOST, VM_USER e VM_PASSWORD no ambiente.\n"
        'ex.: $env:VM_HOST="192.168.1.149"; $env:VM_USER="melque"; $env:VM_PASSWORD="..."'
    )


def cliente():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(HOST, username=USER, password=SENHA, timeout=15, banner_timeout=30)
    return ssh


def executar(comando, sudo=False, tempo=600):
    if sudo:
        comando = f"sudo -S -p '' {comando}"
    ssh = cliente()
    try:
        stdin, stdout, stderr = ssh.exec_command(comando, timeout=tempo, get_pty=False)
        if sudo:
            stdin.write(SENHA + "\n")
            stdin.flush()
        saida = stdout.read().decode("utf-8", errors="replace")
        erro = stderr.read().decode("utf-8", errors="replace")
        codigo = stdout.channel.recv_exit_status()
        return codigo, saida, erro
    finally:
        ssh.close()


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        return 1

    acao = sys.argv[1]
    argumento = sys.argv[2]

    if acao == "run":
        codigo, saida, erro = executar(argumento)
    elif acao == "sudo":
        # aplica sudo no comando inteiro (inclusive pipes, ;, &&)
        codigo, saida, erro = executar(f"bash -lc {shlex.quote(argumento)}", sudo=True)
    elif acao == "put":
        ssh = cliente()
        try:
            with ssh.open_sftp() as sftp:
                sftp.put(argumento, sys.argv[3])
            codigo, saida, erro = 0, f"enviado: {argumento} -> {sys.argv[3]}", ""
        finally:
            ssh.close()
    elif acao == "get":
        ssh = cliente()
        try:
            with ssh.open_sftp() as sftp:
                sftp.get(argumento, sys.argv[3])
            codigo, saida, erro = 0, f"baixado: {argumento} -> {sys.argv[3]}", ""
        finally:
            ssh.close()
    else:
        print(f"ação desconhecida: {acao}")
        return 2

    print(saida.rstrip())
    if erro.strip():
        print("--- stderr ---")
        print(erro.rstrip())
    print(f"--- exit {codigo} ---")
    return codigo


if __name__ == "__main__":
    sys.exit(main())
