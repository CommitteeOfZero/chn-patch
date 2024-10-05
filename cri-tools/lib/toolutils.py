import json
import os
from typing import Any


def ensure_directory(path: str) -> None:
    if not os.path.isdir(path):
        os.mkdir(path)


def save_bytes(path: str, data: bytes) -> None:
    with open(path, "wb") as f:
        f.write(data)


def load_bytes(path: str) -> bytes:
    with open(path, "rb") as f:
        return f.read()


def save_json(path: str, value: Any) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(value, f, ensure_ascii=False, indent="\t")
        f.write("\n")


def load_json(path: str) -> Any:
    with open(path, "r", encoding="utf-8-sig") as f:
        return json.load(f)
