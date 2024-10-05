from dataclasses import dataclass
from enum import IntEnum
from io import BytesIO
from typing import Any, BinaryIO

from lib.codecutils import (
    write_bytes,
    write_be_u,
    write_be_s,
    write_be_f4,
    write_be_f8,
    read_any_bytes,
    read_bytes,
    read_any_be_u,
    read_any_be_s,
    read_any_be_f4,
    read_any_be_f8,
)


class CharsEncoding(IntEnum):
    CP932 = 0
    UTF8 = 1


class Kind(IntEnum):
    U1 = 0
    S1 = 1
    U2 = 2
    S2 = 3
    U4 = 4
    S4 = 5
    U8 = 6
    S8 = 7
    F4 = 8
    F8 = 9
    Chars = 10
    Bytes = 11


class _Storage(IntEnum):
    DEFAULT = 1
    CONSTANT = 3
    NORMAL = 5


@dataclass(frozen=True)
class Column:
    name: str
    kind: Kind


@dataclass(frozen=True)
class Spec:
    name: str
    columns: tuple[Column, ...]
    string_encoding: CharsEncoding


@dataclass(frozen=True)
class Table:
    spec: Spec
    rows: tuple[dict[str, Any], ...]


_default_values = {
    Kind.U1: 0,
    Kind.S1: 0,
    Kind.U2: 0,
    Kind.S2: 0,
    Kind.U4: 0,
    Kind.S4: 0,
    Kind.U8: 0,
    Kind.S8: 0,
    Kind.F4: 0.0,
    Kind.F8: 0.0,
    Kind.Chars: "",
    Kind.Bytes: b"",
}


class _CharsBuilder:
    def __init__(self):
        self.data = bytearray(b"<NULL>\x00")

    def add(self, value: str) -> int:
        if not value:
            return 0
        offset = len(self.data)
        self.data += value.encode("utf-8") + b"\x00"
        return offset

    def build(self, fp: BinaryIO) -> None:
        fp.write(self.data)


class _BytesBuilder:
    def __init__(self):
        self.data = bytearray()

    def add(self, value: bytes) -> int:
        if not value:
            return 0
        offset = len(self.data)
        self.data += value
        return offset

    def build(self, fp: BinaryIO) -> None:
        fp.write(self.data)


class _Writer:
    def __init__(self, fp: BinaryIO, table: Table):
        self._fp = fp
        self._table = table
        self._chars = _CharsBuilder()
        self._bytes = _BytesBuilder()

    def write(self) -> None:
        name_offset = self._chars.add(self._table.spec.name)

        write_be_u(self._fp, 2, self._table.spec.string_encoding)
        rows_offset_position = self._fp.tell()
        write_be_u(self._fp, 2, 0)
        strings_offset_position = self._fp.tell()
        write_be_u(self._fp, 4, 0)
        blobs_offset_position = self._fp.tell()
        write_be_u(self._fp, 4, 0)
        write_be_u(self._fp, 4, name_offset)
        write_be_u(self._fp, 2, len(self._table.spec.columns))
        row_size_position = self._fp.tell()
        write_be_u(self._fp, 2, 0)
        write_be_u(self._fp, 4, len(self._table.rows))

        self._write_columns()

        rows_offset = self._fp.tell()
        self._write_rows()

        strings_offset = self._fp.tell()
        self._chars.build(self._fp)

        write_bytes(self._fp, bytes(-self._fp.tell() % 8))
        blobs_offset = self._fp.tell()
        self._bytes.build(self._fp)
        write_bytes(self._fp, bytes(-self._fp.tell() % 8))

        tmp = self._fp.tell()
        self._fp.seek(rows_offset_position)
        write_be_u(self._fp, 2, rows_offset)
        self._fp.seek(strings_offset_position)
        write_be_u(self._fp, 4, strings_offset)
        self._fp.seek(blobs_offset_position)
        write_be_u(self._fp, 4, blobs_offset)
        self._fp.seek(row_size_position)
        write_be_u(self._fp, 2, self._row_size)
        self._fp.seek(tmp)

    def _write_columns(self) -> None:
        constants = []
        for column in self._table.spec.columns:
            constant = None
            for row in self._table.rows:
                value = row[column.name]
                if constant is None:
                    constant = value
                elif [constant] != [value]:
                    constant = None
                    break
            constants.append(constant is not None)

            kind = column.kind
            if constant is None:
                storage = _Storage.NORMAL
            elif [constant] != [_default_values[kind]]:
                storage = _Storage.CONSTANT
            else:
                storage = _Storage.DEFAULT

            info = (storage << 4) | kind
            name_offset = self._chars.add(column.name)

            write_be_u(self._fp, 1, info)
            write_be_u(self._fp, 4, name_offset)
            if storage == _Storage.CONSTANT:
                self._write_value(kind, constant)
        self._constants = constants

    def _write_rows(self) -> None:
        row_size = 0
        for i in range(len(self._table.rows)):
            row_start = self._fp.tell()
            self._write_row(i)
            row_size = self._fp.tell() - row_start
        self._row_size = row_size

    def _write_row(self, index: int) -> None:
        row = self._table.rows[index]
        for column, constant in zip(self._table.spec.columns, self._constants):
            value = row[column.name]
            if not constant:
                self._write_value(column.kind, value)

    def _write_value(self, kind: Kind, value: Any) -> None:
        match kind:
            case Kind.U1:
                write_be_u(self._fp, 1, value)
            case Kind.S1:
                write_be_s(self._fp, 1, value)
            case Kind.U2:
                write_be_u(self._fp, 2, value)
            case Kind.S2:
                write_be_s(self._fp, 2, value)
            case Kind.U4:
                write_be_u(self._fp, 4, value)
            case Kind.S4:
                write_be_s(self._fp, 4, value)
            case Kind.U8:
                write_be_u(self._fp, 8, value)
            case Kind.S8:
                write_be_s(self._fp, 8, value)
            case Kind.F4:
                write_be_f4(self._fp, value)
            case Kind.F8:
                write_be_f8(self._fp, value)
            case Kind.Chars:
                write_be_u(self._fp, 4, self._chars.add(value))
            case Kind.Bytes:
                write_be_u(self._fp, 4, self._bytes.add(value))
                write_be_u(self._fp, 4, len(value))
            case _:
                raise Exception(kind)


class _Reader:
    def __init__(self, fp: BinaryIO):
        self._fp = fp

    def read(self) -> Table:
        self._chars_encoding = CharsEncoding(read_any_be_u(self._fp, 2))
        self._rows_offset = read_any_be_u(self._fp, 2)
        self._strings_offset = read_any_be_u(self._fp, 4)
        self._blobs_offset = read_any_be_u(self._fp, 4)
        self._name_offset = read_any_be_u(self._fp, 4)
        self._column_count = read_any_be_u(self._fp, 2)
        self._row_size = read_any_be_u(self._fp, 2)
        self._row_count = read_any_be_u(self._fp, 4)

        match self._chars_encoding:
            case CharsEncoding.CP932:
                self._chars_encoding_name = "cp932"
            case CharsEncoding.UTF8:
                self._chars_encoding_name = "utf-8"
            case _:
                raise Exception(self._chars_encoding)

        self._read_columns()
        name = self._read_string(self._name_offset)
        rows = []
        for _ in range(self._row_count):
            rows.append(self._read_row())
        return Table(
            spec=Spec(name, self._columns, self._chars_encoding),
            rows=tuple(rows),
        )

    def _read_columns(self) -> None:
        columns: list[Column] = []
        constants: list[Any | None] = []
        for _ in range(self._column_count):
            column, constant = self._read_column()
            columns.append(column)
            constants.append(constant)
        self._columns = tuple(columns)
        self._constants = tuple(constants)

    def _read_column(self) -> tuple[Column, Any | None]:
        info = read_any_be_u(self._fp, 1)
        kind = Kind(info & 0xF)
        storage = _Storage(info >> 4)

        name_offset = read_any_be_u(self._fp, 4)
        name = self._read_string(name_offset)

        if storage == _Storage.DEFAULT:
            constant = _default_values[kind]
        elif storage == _Storage.CONSTANT:
            constant = self._read_value(kind)
        elif storage == _Storage.NORMAL:
            constant = None
        else:
            raise Exception(storage)

        return Column(name, kind), constant

    def _read_row(self) -> dict[str, Any]:
        row = {}
        for column, constant in zip(self._columns, self._constants):
            kind = column.kind
            value = constant
            if value is None:
                value = self._read_value(kind)
            row[column.name] = value
        return row

    def _read_value(self, kind: Kind) -> Any:
        match kind:
            case Kind.U1:
                return read_any_be_u(self._fp, 1)
            case Kind.S1:
                return read_any_be_s(self._fp, 1)
            case Kind.U2:
                return read_any_be_u(self._fp, 2)
            case Kind.S2:
                return read_any_be_s(self._fp, 2)
            case Kind.U4:
                return read_any_be_u(self._fp, 4)
            case Kind.S4:
                return read_any_be_s(self._fp, 4)
            case Kind.U8:
                return read_any_be_u(self._fp, 8)
            case Kind.S8:
                return read_any_be_s(self._fp, 8)
            case Kind.F4:
                return read_any_be_f4(self._fp)
            case Kind.F8:
                return read_any_be_f8(self._fp)
            case Kind.Chars:
                return self._read_string(
                    read_any_be_u(self._fp, 4),
                )
            case Kind.Bytes:
                return self._read_blob(
                    read_any_be_u(self._fp, 4),
                    read_any_be_u(self._fp, 4),
                )
            case _:
                raise Exception(kind)

    def _read_string(self, offset: int) -> str:
        if offset == 0:
            return ""
        buffer = bytearray()
        tmp = self._fp.tell()
        self._fp.seek(self._strings_offset + offset)
        while True:
            b = read_any_be_u(self._fp, 1)
            if b == 0x00:
                break
            buffer.append(b)
        self._fp.seek(tmp)
        return buffer.decode(self._chars_encoding_name)

    def _read_blob(self, offset: int, length: int) -> bytes:
        tmp = self._fp.tell()
        self._fp.seek(self._blobs_offset + offset)
        value = read_any_bytes(self._fp, length)
        self._fp.seek(tmp)
        return value


def _write_wrapper(fp: BinaryIO, data: bytes) -> None:
    write_bytes(fp, b"@UTF")
    write_be_u(fp, 4, len(data))
    write_bytes(fp, data)


def _read_wrapper(fp: BinaryIO) -> bytes:
    read_bytes(fp, b"@UTF")
    length = read_any_be_u(fp, 4)
    return read_any_bytes(fp, length)


def write(fp: BinaryIO, table: Table) -> None:
    buffer = BytesIO()
    _Writer(buffer, table).write()
    _write_wrapper(fp, buffer.getvalue())


def read(fp: BinaryIO) -> Table:
    buffer = BytesIO(_read_wrapper(fp))
    return _Reader(buffer).read()


def encode(table: Table) -> bytes:
    buffer = BytesIO()
    write(buffer, table)
    return buffer.getvalue()


def decode(data: bytes) -> Table:
    return read(BytesIO(data))
