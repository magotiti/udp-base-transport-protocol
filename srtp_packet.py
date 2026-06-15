from __future__ import annotations

import struct
import zlib
from dataclasses import dataclass


MAX_SEQ = 1 << 14
MAX_PAYLOAD = 255
MAX_WINDOW = 255
TIMEOUT = 0.100

HEADER_FORMAT = "!HHBI"
HEADER_SIZE = struct.calcsize(HEADER_FORMAT)

FLAG_SYN = 0x8000
FLAG_FIN = 0x4000
FLAG_ACK = 0x0002
FLAG_NACK = 0x0001


def seq_add(seq: int, delta: int = 1) -> int:
    return (seq + delta) % MAX_SEQ


def seq_distance(start: int, end: int) -> int:
    return (end - start) % MAX_SEQ


def in_window(seq: int, base: int, size: int) -> bool:
    return seq_distance(base, seq) < size


@dataclass(frozen=True)
class Packet:
    seq: int = 0
    ack: int = 0
    syn: bool = False
    fin: bool = False
    ack_flag: bool = False
    nack: bool = False
    length: int = 0
    payload: bytes = b""

    def encode(self) -> bytes:
        first = self.seq & 0x3FFF
        second = (self.ack & 0x3FFF) << 2

        if self.syn:
            first |= FLAG_SYN
        if self.fin:
            first |= FLAG_FIN
        if self.ack_flag:
            second |= FLAG_ACK
        if self.nack:
            second |= FLAG_NACK

        header = struct.pack(HEADER_FORMAT, first, second, self.length & 0xFF, 0)
        crc = zlib.crc32(header + self.payload) & 0xFFFFFFFF
        return struct.pack(HEADER_FORMAT, first, second, self.length & 0xFF, crc) + self.payload

    @classmethod
    def decode(cls, data: bytes) -> "Packet | None":
        if len(data) < HEADER_SIZE:
            return None

        first, second, length, received_crc = struct.unpack(HEADER_FORMAT, data[:HEADER_SIZE])
        payload = data[HEADER_SIZE:]
        zero_crc_header = struct.pack(HEADER_FORMAT, first, second, length, 0)
        computed_crc = zlib.crc32(zero_crc_header + payload) & 0xFFFFFFFF

        if computed_crc != received_crc:
            return None

        return cls(
            seq=first & 0x3FFF,
            ack=(second >> 2) & 0x3FFF,
            syn=bool(first & FLAG_SYN),
            fin=bool(first & FLAG_FIN),
            ack_flag=bool(second & FLAG_ACK),
            nack=bool(second & FLAG_NACK),
            length=length,
            payload=payload,
        )
