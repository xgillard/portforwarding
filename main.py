"""Script qui permet d'ouvrir un tunnel vers une autre machine."""

import argparse
import select
import socket
import socketserver


def cli() -> argparse.ArgumentParser:
    """Recupere arguments en ligne de commande."""
    parser = argparse.ArgumentParser(
        prog = "portforwarding",
        description= "portforwarding pour avoir accès au réseau AGR depuis ma box linux",
    )
    parser.add_argument("-l", "--local",  help="le port local")
    parser.add_argument("-a", "--addr",   help="l'adresse de la machine distante")
    parser.add_argument("-r", "--remote", help="le port de la machine distante")
    return parser


class ForwardServer(socketserver.ThreadingTCPServer):
    """Un server tcp simple qui gère les requetes entrantes via des threads."""

    daemon_threads = True
    allow_reuse_address = True


class TunnelHandler(socketserver.BaseRequestHandler):
    """Un handler qui redirige le traffic d'une requete (tcp) vers un channel ssh."""

    chain_host: str
    chain_port: int

    def handle(self) -> None:
        """Effectue la redirection."""
        try:
            chan = socket.create_connection((self.chain_host, self.chain_port))

            if chan is None:
                raise ValueError("channel creation rejected")  # noqa: EM101, TRY003

            while True:
                r, w, x = select.select([self.request, chan], [], [])
                if self.request in r:
                    data = self.request.recv(1024)
                    if len(data) == 0:
                        break
                    chan.send(data)
                if chan in r:
                    data = chan.recv(1024)
                    if len(data) == 0:
                        break
                    self.request.send(data)
        finally:
            chan.close()
            self.request.close()


def forward_tunnel(
    local_port: int,
    remote_host: str,
    remote_port: int,
) -> None:
    """Ouvre un tunnel ssh (forward).

    Ouvre le port local  `local_port` et redirige tout le traffic
    entrant sur ce port vers `remote_host:remote_port` en routant
    tout le traffic sur un canal ssh.
    """

    class SubHandler(TunnelHandler):
        chain_host = remote_host
        chain_port = remote_port

    ForwardServer(("0.0.0.0", local_port), SubHandler).serve_forever()  # noqa: S104



def main() -> None:
    """Point d'entrée principal du programme."""
    args = cli().parse_args()
    print(f"{args.addr=}, {args.local=}, {args.remote=}")
    forward_tunnel(
        remote_host=args.addr,
        local_port=int(args.local),
        remote_port=int(args.remote),
    )


if __name__ == "__main__":
    main()
