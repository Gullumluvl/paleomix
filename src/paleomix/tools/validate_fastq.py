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

import json
import sys

from paleomix.common.argparse import ArgumentParser, Namespace
from paleomix.common.formats.fastq import FASTQ, FASTQOffsets, FASTQualities


def parse_args(argv: list[str]) -> Namespace:
    parser = ArgumentParser("paleomix :validate_fastq")
    parser.add_argument("files", nargs="+")
    parser.add_argument("--collapsed", action="store_true")
    parser.add_argument("--no-empty", action="store_true")
    parser.add_argument("--offset", type=int, choices=(33, 64), default=33)

    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    expected_offsets = FASTQOffsets(args.offset)

    seq_retained_nts = 0
    seq_retained_reads = 0

    for filename in args.files:
        qualities = FASTQualities()
        for record in FASTQ.from_file(filename):
            qualities.update(record)

            seq_retained_reads += 1
            seq_retained_nts += len(record.sequence)

        offsets: FASTQOffsets = qualities.offsets()
        if offsets == FASTQOffsets.BOTH:
            print(
                "FASTQ file(s) contains quality scores with both quality offsets (33 "
                "and 64); file may be unexpected format or corrupt. Please ensure that "
                "this file contains valid FASTQ reads from a single source.",
                file=sys.stderr,
            )

            return 1
        elif offsets == FASTQOffsets.MISSING:
            if args.no_empty:
                print("FASTQ file is empty.", file=sys.stderr)

                return 1
        elif offsets not in (FASTQOffsets.AMBIGUOUS, expected_offsets):
            print(
                "FASTQ file contains quality scores with wrong quality score offset "
                f"({offsets}); expected reads with quality score offset "
                f"{expected_offsets}. Ensure that the 'QualityOffset' specified in the "
                "makefile corresponds to the input.",
                file=sys.stderr,
            )

            return 1

    print(
        json.dumps(
            {
                "filenames": args.files,
                "seq_retained_reads": seq_retained_reads,
                "seq_retained_nts": seq_retained_nts,
                "seq_collapsed": seq_retained_reads if args.collapsed else 0,
            },
            indent=2,
            sort_keys=True,
        )
    )

    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
