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
"""
MultiQC - Aggregate results from bioinformatics analyses across many samples into a
single report

https://multiqc.info/
"""

from __future__ import annotations

import fnmatch
import os
from typing import TYPE_CHECKING, Iterable

from paleomix.common.command import AtomicCmd, InputFile, OptionsType, OutputFile
from paleomix.node import CommandNode, Node, NodeError

if TYPE_CHECKING:
    from typing_extensions import Literal

# Supported modules and their expected files
# For more, see https://multiqc.info/docs/#multiqc-modules
MODULES = {
    "fastp": "*fastp.json",
    "fastqc": "*_fastqc.zip",
}


class MultiQCNode(CommandNode):
    def __init__(
        self,
        source: Literal["fastp", "fastqc"],
        output_prefix: str,
        dependencies: Iterable[Node],
        options: OptionsType | None = None,
    ) -> None:
        pattern = MODULES.get(source)
        if pattern is None:
            raise NodeError(f"unsupported MultiQC source {source!r}")

        if options is None:
            options = {}

        command = AtomicCmd(
            [
                "multiqc",
                "--zip-data-dir",
                "--filename",
                os.path.basename(output_prefix),
                "--outdir",
                "%(TEMP_DIR)s",
                "--module",
                source,
            ],
            extra_files=(
                OutputFile(output_prefix + ".html"),
                OutputFile(output_prefix + "_data.zip"),
            ),
        )

        command.append_options(options)

        input_files_found = False
        dependencies = list(dependencies)
        for node in dependencies:
            for filename in fnmatch.filter(node.output_files, pattern):
                input_files_found = True
                command.append(InputFile(filename))

        if not input_files_found:
            raise NodeError(f"no {source!r} input files found for MultiQC")

        CommandNode.__init__(
            self,
            command=command,
            description="multiQC of %i reports" % (len(dependencies),),
            dependencies=dependencies,
        )
