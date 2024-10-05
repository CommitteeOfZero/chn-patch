from typing import BinaryIO
import struct


def write_bytes(fp: BinaryIO, value: bytes) -> None:
    fp.write(value)


def write_le_u(fp: BinaryIO, length: int, value: int) -> None:
    write_bytes(fp, value.to_bytes(length, "little", signed=False))


def write_be_u(fp: BinaryIO, length: int, value: int) -> None:
    write_bytes(fp, value.to_bytes(length, "big", signed=False))


def write_be_s(fp: BinaryIO, length: int, value: int) -> None:
    write_bytes(fp, value.to_bytes(length, "big", signed=True))


def write_be_f4(fp: BinaryIO, value: int) -> None:
    write_bytes(fp, struct.pack(">f", value))


def write_be_f8(fp: BinaryIO, value: int) -> None:
    write_bytes(fp, struct.pack(">d", value))


def read_any_bytes(fp: BinaryIO, length: int) -> bytes:
    value = fp.read(length)
    if len(value) != length:
        raise EOFError
    return value


def read_bytes(fp: BinaryIO, expected: bytes) -> None:
    actual = read_any_bytes(fp, len(expected))
    if actual != expected:
        raise ValueError(f"expected {expected!r}, got {actual!r}")


def read_any_le_u(fp: BinaryIO, length: int) -> int:
    return int.from_bytes(read_any_bytes(fp, length), "little", signed=False)


def read_any_be_u(fp: BinaryIO, length: int) -> int:
    return int.from_bytes(read_any_bytes(fp, length), "big", signed=False)


def read_be_u(fp: BinaryIO, length: int, expected: int) -> None:
    actual = read_any_be_u(fp, length)
    if actual != expected:
        raise ValueError(f"expected {expected}, got {actual}")


def read_any_be_s(fp: BinaryIO, length: int) -> int:
    return int.from_bytes(read_any_bytes(fp, length), "big", signed=True)


def read_be_s(fp: BinaryIO, length: int, expected: int) -> None:
    actual = read_any_be_s(fp, length)
    if actual != expected:
        raise ValueError(f"expected {expected}, got {actual}")


def read_any_be_f4(fp: BinaryIO) -> None:
    return struct.unpack(">f", read_any_bytes(fp, 4))[0]


def read_any_be_f8(fp: BinaryIO) -> None:
    return struct.unpack(">d", read_any_bytes(fp, 8))[0]
