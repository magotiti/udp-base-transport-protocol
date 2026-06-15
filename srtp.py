from __future__ import annotations

import argparse
from pathlib import Path

from srtp_transfer import receive_file, send_file


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="SRTP file transfer over UDP")
    subcommands = parser.add_subparsers(dest="command", required=True)

    send = subcommands.add_parser("send", help="send a file")
    send.add_argument("host", help="receiver host")
    send.add_argument("port", type=int, help="receiver UDP port")
    send.add_argument("file", help="file to send")
    send.add_argument("--bind", default="0.0.0.0", help="local bind address")
    send.add_argument("--mode", choices=("saw", "gbn", "sr"), default="saw")
    send.add_argument("--window", type=int, default=4)

    recv = subcommands.add_parser("recv", help="receive a file")
    recv.add_argument("port", type=int, help="UDP port to listen on")
    recv.add_argument("output", help="output path")
    recv.add_argument("--bind", default="0.0.0.0", help="local bind address")
    recv.add_argument("--mode", choices=("saw", "gbn", "sr"), default="saw")
    recv.add_argument("--window", type=int, default=4)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "send":
        send_file(args.host, args.port, Path(args.file), args.mode, args.window, args.bind)
    else:
        receive_file(args.port, Path(args.output), args.mode, args.window, args.bind)


if __name__ == "__main__":
    main()
