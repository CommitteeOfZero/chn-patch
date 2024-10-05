from argparse import ArgumentParser

from lib.tools.create_archive import run


def _main():
    parser = ArgumentParser()
    parser.add_argument("--directory", required=True)
    parser.add_argument("--archive", required=True)
    args = parser.parse_args()
    run(**vars(args))


_main()
