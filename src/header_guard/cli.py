"""Command line interface for the header guard utility."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Sequence, Tuple

import click

from .core import DEFAULT_SPACES_BETWEEN_ENDIF_AND_COMMENT, process_paths


@dataclass(frozen=True)
class Arguments:
    """Command line arguments supported by the header guard tool."""

    paths: Tuple[Path, ...]
    spaces_between_endif_and_comment: int


@click.command()
@click.argument("paths", nargs=-1, type=click.Path(path_type=Path))
@click.option(
    "--spaces-between-endif-and-comment",
    "spaces_between_endif_and_comment",
    type=click.IntRange(min=0),
    default=DEFAULT_SPACES_BETWEEN_ENDIF_AND_COMMENT,
    show_default=True,
    help="Number of spaces between '#endif' and the trailing comment.",
)
def cli(
    paths: Tuple[Path, ...], spaces_between_endif_and_comment: int
) -> None:
    """Entry point for the command line interface."""

    if not paths:
        raise click.UsageError("Provide at least one header path to format.")

    try:
        process_paths(paths, spaces_between_endif_and_comment)
    except FileNotFoundError as error:
        raise click.ClickException(str(error)) from error


CLI = cli


def parse_args(argv: Sequence[str]) -> Arguments:
    """Parse *argv* into :class:`Arguments` without invoking Click's CLI."""

    if not argv:
        raise ValueError("Usage: header-guard <path> [<path> ...]")

    arguments = list(argv[1:])
    try:
        with CLI.make_context("header-guard", arguments) as context:
            paths = tuple(context.params["paths"])
            spaces_between_endif_and_comment = context.params[
                "spaces_between_endif_and_comment"
            ]
    except click.ClickException as error:
        raise ValueError(str(error)) from error

    if not paths:
        raise ValueError("Usage: header-guard <path> [<path> ...]")

    return Arguments(paths, spaces_between_endif_and_comment)


def main(argv: Optional[Sequence[str]] = None) -> None:
    """Entry point used by both the CLI and the library API."""

    if argv is None:
        CLI.main()
        return

    arguments = parse_args(argv)
    process_paths(arguments.paths, arguments.spaces_between_endif_and_comment)
