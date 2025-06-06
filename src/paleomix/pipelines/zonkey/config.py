#
# Copyright (c) 2023 Mikkel Schubert <MikkelSch@gmail.com>
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
#
from __future__ import annotations

import paleomix
import paleomix.common.logging
import paleomix.pipeline
from paleomix.common.argparse import (
    SUPPRESS,
    ArgumentParser,
    ArgumentParserBase,
    SubParsersAction,
)

_RUN_USAGE = """%(prog)s [..] <database.tar> <samples.txt> [destination]
       %(prog)s [..] <database.tar> <sample.bam> [destination]
       %(prog)s [..] <database.tar> <nuclear.bam> <mitochondrial.bam> <destination>
"""

_DEFAULT_CONFIG_FILES = [
    "/etc/paleomix/zonkey.ini",
    "~/.paleomix/zonkey.ini",
]


def build_parser() -> tuple[ArgumentParserBase, ArgumentParserBase]:
    parser = ArgumentParser(prog="paleomix zonkey")

    subparsers = parser.add_subparsers(dest="command", metavar="command")
    run = add_run_command(subparsers)
    add_mito_command(subparsers)
    add_copy_example_command(subparsers)

    return parser, run


def add_copy_example_command(subparsers: SubParsersAction[ArgumentParser]) -> None:
    parser = subparsers.add_parser("example", help="Create example project")

    parser.add_argument(
        "database", help="Zonkey database file (uncompressed)", metavar="database.tar"
    )

    parser.add_argument(
        "destination",
        default=".",
        nargs="?",
        help="Destination folder for example data.",
    )


def add_mito_command(subparsers: SubParsersAction[ArgumentParser]) -> None:
    parser = subparsers.add_parser(
        "mito", help="Create phylo pipeline project for mt alignments"
    )

    parser.add_argument(
        "database", help="Zonkey database file (uncompressed)", metavar="database.tar"
    )

    parser.add_argument(
        "destination",
        default=".",
        nargs="?",
        help="Destination folder for project template.",
    )


def add_run_command(subparsers: SubParsersAction[ArgumentParser]) -> ArgumentParserBase:
    parser = subparsers.add_parser(
        "run",
        aliases=("dryrun",),
        help="Run pipeline on provided makefiles",
        usage=_RUN_USAGE,
        prog="paleomix zonkey run",
        default_config_files=_DEFAULT_CONFIG_FILES,
    )

    parser.add_argument(
        "database", help="Zonkey database file (uncompressed)", metavar="database.tar"
    )

    parser.add_argument("files", help="See usage", nargs="+")

    group = parser.add_argument_group("Program options")
    group.add_argument(
        "--downsample-to",
        type=int,
        default=1000000,
        help="Number of reads to use for analyses; if 0, no downsampling is performed",
    )
    group.add_argument(
        "--admixture-replicates",
        type=int,
        default=1,
        help="Number of admixture replicates to run, before "
        "the result with the highest likelihood",
    )
    group.add_argument(
        "--treemix-k",
        type=int,
        default=0,
        help="Value passed to treemix's -k option; number of "
        "SNPs per block for estimation of the covariance "
        "matrix. If set to 0, a value will be estimated "
        "assuming an even distribution of SNPs",
    )
    group.add_argument(
        "--treemix-outgroup",
        default="",
        type=lambda value: tuple(_f for _f in sorted(value.split(",")) if _f),
        help="Comma-seperated list of samples to use as the "
        "outgroup when running TreeMix; note that these "
        "must form a monophyletic clade, or TreeMix will "
        "not execute.",
    )

    group.add_argument(
        "--admixture-only",
        help=SUPPRESS,
        default=False,
        action="store_true",
    )

    paleomix.common.logging.add_argument_group(parser)
    paleomix.pipeline.add_argument_groups(parser)

    # Removed options
    parser.add_argument("--progress-ui", help=SUPPRESS)
    parser.add_argument("--ui-colors", help=SUPPRESS)

    return parser
