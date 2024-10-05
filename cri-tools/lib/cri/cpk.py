from dataclasses import dataclass
import os
from shutil import copyfileobj
from typing import BinaryIO

from lib.codecutils import (
    write_bytes,
    write_le_u,
)
from lib.cri.table import (
    Column,
    Kind,
    Spec,
    CharsEncoding,
    Table,
    encode as encode_table,
)


@dataclass(frozen=True)
class Config:
    alignment: int
    encrypt_tables: bool
    randomize_padding: bool


_header_spec = Spec(
    name="CpkHeader",
    columns=(
        Column("UpdateDateTime", Kind.U8),
        Column("FileSize", Kind.U8),
        Column("ContentOffset", Kind.U8),
        Column("ContentSize", Kind.U8),
        Column("TocOffset", Kind.U8),
        Column("TocSize", Kind.U8),
        Column("TocCrc", Kind.U4),
        Column("HtocOffset", Kind.U8),
        Column("HtocSize", Kind.U8),
        Column("EtocOffset", Kind.U8),
        Column("EtocSize", Kind.U8),
        Column("ItocOffset", Kind.U8),
        Column("ItocSize", Kind.U8),
        Column("ItocCrc", Kind.U4),
        Column("GtocOffset", Kind.U8),
        Column("GtocSize", Kind.U8),
        Column("GtocCrc", Kind.U4),
        Column("HgtocOffset", Kind.U8),
        Column("HgtocSize", Kind.U8),
        Column("EnabledPackedSize", Kind.U8),
        Column("EnabledDataSize", Kind.U8),
        Column("TotalDataSize", Kind.U8),
        Column("Tocs", Kind.U4),
        Column("Files", Kind.U4),
        Column("Groups", Kind.U4),
        Column("Attrs", Kind.U4),
        Column("TotalFiles", Kind.U4),
        Column("Directories", Kind.U4),
        Column("Updates", Kind.U4),
        Column("Version", Kind.U2),
        Column("Revision", Kind.U2),
        Column("Align", Kind.U2),
        Column("Sorted", Kind.U2),
        Column("EnableFileName", Kind.U2),
        Column("EID", Kind.U2),
        Column("CpkMode", Kind.U4),
        Column("Tvers", Kind.Chars),
        Column("Comment", Kind.Chars),
        Column("Codec", Kind.U4),
        Column("DpkItoc", Kind.U4),
        Column("EnableTocCrc", Kind.U2),
        Column("EnableFileCrc", Kind.U2),
        Column("CrcMode", Kind.U4),
        Column("CrcTable", Kind.Bytes),
    ),
    string_encoding=CharsEncoding.CP932,
)

_toc_info_spec = Spec(
    name="CpkTocInfo",
    columns=(
        Column("DirName", Kind.Chars),
        Column("FileName", Kind.Chars),
        Column("FileSize", Kind.U4),
        Column("ExtractSize", Kind.U4),
        Column("FileOffset", Kind.U8),
        Column("ID", Kind.U4),
        Column("UserString", Kind.Chars),
    ),
    string_encoding=CharsEncoding.CP932,
)

_extend_id_spec = Spec(
    name="CpkExtendId",
    columns=(
        Column("ID", Kind.S4),
        Column("TocIndex", Kind.S4),
    ),
    string_encoding=CharsEncoding.CP932,
)

_body_offset = 2048

_format_version = 7
_format_revision = 14


def _crypt(data: bytes) -> bytes:
    buffer = bytearray(data)
    key = 0x5F
    for i in range(len(data)):
        buffer[i] ^= key
        key = (key * 0x15) & 0xFF
    return bytes(buffer)


@dataclass(frozen=True)
class _InternalTocEntry:
    id_: int
    name: str
    offset: int
    size: int


@dataclass(frozen=True)
class _InternalItocEntry:
    id_: int
    index: int


class Writer:
    def __init__(self, fp: BinaryIO, config: Config):
        self._fp = fp
        self._config = config

        self._ids = set()
        self._names = set()

        self._internal_toc = []
        self._fp.seek(_body_offset)
        self._align()
        self._content_offset = self._fp.tell()

    def write_file(self, id_: int, name: str, fp: BinaryIO) -> None:
        if id_ in self._ids:
            raise ValueError(f"duplicate id: {id_!r}")
        self._ids.add(id_)

        if name in self._names:
            raise ValueError(f"duplicate name: {name!r}")
        self._names.add(name)

        self._align()
        offset = self._fp.tell()
        copyfileobj(fp, self._fp)
        size = self._fp.tell() - offset

        self._internal_toc.append(
            _InternalTocEntry(
                id_=id_,
                name=name,
                offset=offset,
                size=size,
            )
        )

    def close(self) -> None:
        total_size = 0
        self._internal_toc.sort(key=lambda x: x.name)
        internal_itoc = []
        toc = []
        for entry in self._internal_toc:
            total_size += entry.size
            internal_itoc.append(
                _InternalItocEntry(
                    id_=entry.id_,
                    index=len(toc),
                )
            )
            toc.append(
                {
                    "DirName": "",
                    "FileName": entry.name,
                    "FileSize": entry.size,
                    "ExtractSize": entry.size,
                    "FileOffset": entry.offset - _body_offset,
                    "ID": entry.id_,
                    "UserString": "",
                }
            )

        internal_itoc.sort(key=lambda x: x.id_)
        itoc = []
        for entry in internal_itoc:
            itoc.append(
                {
                    "ID": entry.id_,
                    "TocIndex": entry.index,
                }
            )

        content_offset = self._content_offset
        content_size = self._fp.tell() - content_offset

        self._align()
        toc_offset = self._fp.tell()
        self._write_chunk_table(b"TOC ", Table(_toc_info_spec, tuple(toc)))
        toc_size = self._fp.tell() - toc_offset

        self._align()
        itoc_offset = self._fp.tell()
        self._write_chunk_table(b"ITOC", Table(_extend_id_spec, tuple(itoc)))
        itoc_size = self._fp.tell() - itoc_offset

        self._fp.seek(0)
        self._write_chunk_table(
            b"CPK ",
            Table(
                _header_spec,
                (
                    {
                        "UpdateDateTime": 0,
                        "FileSize": 0,
                        "ContentOffset": content_offset,
                        "ContentSize": content_size,
                        "TocOffset": toc_offset,
                        "TocSize": toc_size,
                        "TocCrc": 0,
                        "HtocOffset": 0,
                        "HtocSize": 0,
                        "EtocOffset": 0,
                        "EtocSize": 0,
                        "ItocOffset": itoc_offset,
                        "ItocSize": itoc_size,
                        "ItocCrc": 0,
                        "GtocOffset": 0,
                        "GtocSize": 0,
                        "GtocCrc": 0,
                        "HgtocOffset": 0,
                        "HgtocSize": 0,
                        "EnabledPackedSize": total_size,
                        "EnabledDataSize": total_size,
                        "TotalDataSize": 0,
                        "Tocs": 0,
                        "Files": len(self._internal_toc),
                        "Groups": 0,
                        "Attrs": 0,
                        "TotalFiles": 0,
                        "Directories": 0,
                        "Updates": 0,
                        "Version": _format_version,
                        "Revision": _format_revision,
                        "Align": self._config.alignment,
                        "Sorted": 1,
                        "EnableFileName": 1,
                        "EID": 1,
                        "CpkMode": 2,
                        "Tvers": "",
                        "Comment": "",
                        "Codec": 0,
                        "DpkItoc": 0,
                        "EnableTocCrc": 0,
                        "EnableFileCrc": 0,
                        "CrcMode": 0,
                        "CrcTable": b"",
                    },
                ),
            ),
        )
        if self._fp.tell() > _body_offset:
            raise Exception("info is too large")
        self._pad(_body_offset - self._fp.tell())

    def _write_chunk_table(self, name: bytes, table: Table) -> None:
        data = encode_table(table)
        self._write_chunk(name, data, self._config.encrypt_tables)

    def _write_chunk(self, name: bytes, data: bytes, encrypted: bool) -> None:
        if len(name) != 4:
            raise ValueError(f"invalid chunk name: {name!r}")
        write_bytes(self._fp, name)
        if encrypted:
            write_le_u(self._fp, 4, 0x00)
        else:
            write_le_u(self._fp, 4, 0xFF)
        write_le_u(self._fp, 8, len(data))
        if encrypted:
            data = _crypt(data)
        write_bytes(self._fp, data)

    def _align(self) -> None:
        self._pad(-self._fp.tell() % self._config.alignment)

    def _pad(self, size: int) -> None:
        if self._config.randomize_padding:
            padding = os.urandom(size)
        else:
            padding = bytes(size)
        write_bytes(self._fp, padding)
