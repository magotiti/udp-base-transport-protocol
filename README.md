# udp-base-transport-protocol

Implementacao base em Python do SRTP, um protocolo de transporte confiavel sobre UDP.

## Estrutura

- `srtp.py`: linha de comando.
- `srtp_packet.py`: cabecalho, flags, CRC32 e numeros de sequencia.
- `srtp_transfer.py`: handshake, encerramento e transferencia nos modos Stop-and-Wait, Go-Back-N e Selective Repeat.

## Uso

Receiver:

```bash
python3 srtp.py recv 9000 recebido.bin --mode saw --window 4
```

Sender:

```bash
python3 srtp.py send 127.0.0.1 9000 arquivo.bin --mode saw --window 4
```

Modos disponiveis:

```bash
--mode saw
--mode gbn
--mode sr
```

O sender usa a porta `P+1` localmente para receber ACK/NACK, conforme o enunciado.
