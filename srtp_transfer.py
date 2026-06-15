from __future__ import annotations

import socket
import time
from pathlib import Path

from srtp_packet import MAX_PAYLOAD, MAX_SEQ, MAX_WINDOW, TIMEOUT, Packet, in_window, seq_add, seq_distance


def clamp_window(window: int) -> int:
    return max(1, min(window, MAX_WINDOW))


def make_chunks(path: Path) -> list[bytes]:
    data = path.read_bytes()
    chunks = [data[i : i + MAX_PAYLOAD] for i in range(0, len(data), MAX_PAYLOAD)]

    if not chunks or len(chunks[-1]) == MAX_PAYLOAD:
        chunks.append(b"")

    return chunks


def make_data_packets(chunks: list[bytes]) -> list[Packet]:
    total = len(chunks)
    packets = []

    for index, chunk in enumerate(chunks):
        is_last = index == total - 1
        length = len(chunk) if is_last else MAX_PAYLOAD
        packets.append(Packet(seq=index % MAX_SEQ, length=length, payload=chunk))

    return packets


def send_packet(sock: socket.socket, packet: Packet, peer: tuple[str, int]) -> None:
    sock.sendto(packet.encode(), peer)


def receive_valid(sock: socket.socket) -> tuple[Packet, tuple[str, int]]:
    while True:
        data, peer = sock.recvfrom(4096)
        packet = Packet.decode(data)
        if packet is not None:
            return packet, peer


def send_and_wait(sock: socket.socket, packet: Packet, peer: tuple[str, int]) -> Packet:
    while True:
        send_packet(sock, packet, peer)
        try:
            response, _ = receive_valid(sock)
            return response
        except socket.timeout:
            continue


def sender_handshake(sock: socket.socket, peer: tuple[str, int], proposed_window: int) -> int:
    syn = Packet(syn=True, length=proposed_window)

    while True:
        response = send_and_wait(sock, syn, peer)
        if response.syn and response.ack_flag:
            effective_window = min(proposed_window, response.length)
            send_packet(sock, Packet(ack=response.seq, ack_flag=True), peer)
            return clamp_window(effective_window)


def receiver_handshake(sock: socket.socket, proposed_window: int) -> tuple[tuple[str, int], int]:
    while True:
        packet, sender = receive_valid(sock)
        if not packet.syn:
            continue

        effective_window = min(proposed_window, packet.length)
        syn_ack = Packet(seq=0, ack=packet.seq, syn=True, ack_flag=True, length=effective_window)
        send_packet(sock, syn_ack, sender)

        sock.settimeout(TIMEOUT * 10)
        try:
            confirm, confirm_sender = receive_valid(sock)
        except socket.timeout:
            continue
        finally:
            sock.settimeout(None)

        if confirm_sender == sender and confirm.ack_flag:
            return sender, clamp_window(effective_window)


def send_fin(sock: socket.socket, peer: tuple[str, int]) -> None:
    fin = Packet(fin=True)
    while True:
        response = send_and_wait(sock, fin, peer)
        if response.fin and response.ack_flag:
            return


def send_file_saw(sock: socket.socket, peer: tuple[str, int], packets: list[Packet]) -> None:
    for packet in packets:
        while True:
            response = send_and_wait(sock, packet, peer)
            if response.ack_flag and response.ack == packet.seq:
                break


def send_file_gbn(sock: socket.socket, peer: tuple[str, int], packets: list[Packet], window: int) -> None:
    base = 0
    next_seq = 0
    sent_at: dict[int, float] = {}

    while base < len(packets):
        while next_seq < len(packets) and next_seq - base < window:
            send_packet(sock, packets[next_seq], peer)
            sent_at[next_seq] = time.monotonic()
            next_seq += 1

        try:
            response, _ = receive_valid(sock)
        except socket.timeout:
            response = None

        if response is not None and response.nack:
            next_seq = base
            continue

        if response is not None and response.ack_flag:
            distance = seq_distance(base % MAX_SEQ, response.ack)
            acknowledged_index = base + distance
            if base <= acknowledged_index < next_seq:
                base = acknowledged_index + 1

        if base < next_seq and time.monotonic() - sent_at.get(base, 0) >= TIMEOUT:
            for index in range(base, next_seq):
                send_packet(sock, packets[index], peer)
                sent_at[index] = time.monotonic()


def send_file_sr(sock: socket.socket, peer: tuple[str, int], packets: list[Packet], window: int) -> None:
    base = 0
    next_seq = 0
    acked: set[int] = set()
    sent_at: dict[int, float] = {}

    while base < len(packets):
        while next_seq < len(packets) and next_seq - base < window:
            send_packet(sock, packets[next_seq], peer)
            sent_at[next_seq] = time.monotonic()
            next_seq += 1

        try:
            response, _ = receive_valid(sock)
        except socket.timeout:
            response = None

        if response is not None and response.ack_flag:
            distance = seq_distance(base % MAX_SEQ, response.ack)
            index = base + distance
            if base <= index < len(packets):
                acked.add(index)

        if response is not None and response.nack:
            distance = seq_distance(base % MAX_SEQ, response.ack)
            index = base + distance
            if base <= index < next_seq and index not in acked:
                send_packet(sock, packets[index], peer)
                sent_at[index] = time.monotonic()

        now = time.monotonic()
        for index in range(base, next_seq):
            if index not in acked and now - sent_at.get(index, 0) >= TIMEOUT:
                send_packet(sock, packets[index], peer)
                sent_at[index] = now

        while base in acked:
            base += 1


def receive_saw(sock: socket.socket, output: Path, peer: tuple[str, int]) -> None:
    expected = 0
    last_ack: int | None = None

    with output.open("wb") as file:
        while True:
            packet, sender = receive_valid(sock)
            if sender != peer:
                continue
            if packet.fin:
                send_packet(sock, Packet(fin=True, ack_flag=True, ack=packet.seq), peer)
                return
            if packet.seq != expected:
                if last_ack is not None:
                    send_packet(sock, Packet(ack=last_ack, ack_flag=True), peer)
                continue

            file.write(packet.payload)
            send_packet(sock, Packet(ack=packet.seq, ack_flag=True), peer)
            last_ack = packet.seq
            expected = seq_add(expected)


def receive_gbn(sock: socket.socket, output: Path, peer: tuple[str, int]) -> None:
    expected = 0

    with output.open("wb") as file:
        while True:
            packet, sender = receive_valid(sock)
            if sender != peer:
                continue
            if packet.fin:
                send_packet(sock, Packet(fin=True, ack_flag=True, ack=packet.seq), peer)
                return
            if packet.seq == expected:
                file.write(packet.payload)
                send_packet(sock, Packet(ack=packet.seq, ack_flag=True), peer)
                expected = seq_add(expected)
            else:
                send_packet(sock, Packet(ack=expected, nack=True), peer)


def receive_sr(sock: socket.socket, output: Path, peer: tuple[str, int], window: int) -> None:
    base = 0
    buffer: dict[int, Packet] = {}

    with output.open("wb") as file:
        while True:
            packet, sender = receive_valid(sock)
            if sender != peer:
                continue
            if packet.fin:
                send_packet(sock, Packet(fin=True, ack_flag=True, ack=packet.seq), peer)
                return
            if not in_window(packet.seq, base, window):
                send_packet(sock, Packet(ack=packet.seq, ack_flag=True), peer)
                continue

            buffer[packet.seq] = packet
            send_packet(sock, Packet(ack=packet.seq, ack_flag=True), peer)

            while base in buffer:
                current = buffer.pop(base)
                file.write(current.payload)
                base = seq_add(base)

            if base not in buffer:
                send_packet(sock, Packet(ack=base, nack=True), peer)


def send_file(host: str, port: int, file_path: Path, mode: str, window: int, bind: str) -> None:
    packets = make_data_packets(make_chunks(file_path))

    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.bind((bind, port + 1))
        sock.settimeout(TIMEOUT)
        peer = (host, port)

        effective_window = sender_handshake(sock, peer, clamp_window(window))
        transfer_window = 1 if mode == "saw" else effective_window

        if mode == "saw":
            send_file_saw(sock, peer, packets)
        elif mode == "gbn":
            send_file_gbn(sock, peer, packets, transfer_window)
        else:
            send_file_sr(sock, peer, packets, transfer_window)

        send_fin(sock, peer)


def receive_file(port: int, output: Path, mode: str, window: int, bind: str) -> None:
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.bind((bind, port))
        peer, effective_window = receiver_handshake(sock, clamp_window(window))
        transfer_window = 1 if mode == "saw" else effective_window

        if mode == "saw":
            receive_saw(sock, output, peer)
        elif mode == "gbn":
            receive_gbn(sock, output, peer)
        else:
            receive_sr(sock, output, peer, transfer_window)
