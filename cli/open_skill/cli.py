import argparse

from . import __version__


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="open-skill", description="Open Skill Standard CLI")
    p.add_argument("--version", action="version", version=f"open-skill {__version__}")
    return p


def main(argv=None) -> int:
    build_parser().parse_args(argv)
    return 0
