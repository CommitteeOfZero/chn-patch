import os

from lib.cri.cpk import Config, Writer
from lib.toolutils import load_json


def run(directory: str, archive: str) -> None:
    meta = load_json(os.path.join(directory, "_meta.json"))
    with open(archive, "wb") as archive_fp:
        writer = Writer(
            archive_fp,
            Config(
                alignment=meta["alignment"],
                encrypt_tables=meta["encrypt-tables"],
                randomize_padding=meta["randomize-padding"],
            ),
        )
        for entry in meta["entries"]:
            with open(os.path.join(directory, entry["path"]), "rb") as file_fp:
                writer.write_file(entry["id"], entry["name"], file_fp)
                print("Wrote file", entry["id"],":", entry["name"], "into c0data.cpk")
        writer.close()
