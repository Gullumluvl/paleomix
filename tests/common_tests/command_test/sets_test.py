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

from pathlib import Path
from typing import Any, Union
from unittest.mock import Mock, call

import pytest
from typing_extensions import TypeAlias

import paleomix.common.command
from paleomix.common.command import (
    AtomicCmd,
    AuxiliaryFile,
    CmdError,
    Executable,
    InputFile,
    OutputFile,
    ParallelCmds,
    SequentialCmds,
    TempOutputFile,
)
from paleomix.common.versions import Requirement

_SET_CLASSES = (ParallelCmds, SequentialCmds)
SetTypes: TypeAlias = Union[type[ParallelCmds], type[SequentialCmds]]

###############################################################################
###############################################################################
# Properties with same expected behavior for both Parallel/SequentialCmds


@pytest.mark.parametrize("cls", _SET_CLASSES)
def test_atomicsets__properties(cls: SetTypes) -> None:
    requirement_1 = Requirement(call=["bwa"], regexp=r"(\d+)")
    requirement_2 = Requirement(call=["bowtie2"], regexp=r"(\d+)")

    cmd_mock_1 = AtomicCmd(
        ("true",),
        extra_files=[
            Executable("false"),
            InputFile("/foo/bar/in_1.file"),
            InputFile("/foo/bar/in_2.file"),
            OutputFile("/bar/foo/out"),
            TempOutputFile("out.log"),
            AuxiliaryFile("/aux/fA"),
            AuxiliaryFile("/aux/fB"),
        ],
        requirements=[requirement_1],
    )
    cmd_mock_2 = AtomicCmd(
        ("false",),
        extra_files=[
            Executable("echo"),
            Executable("java"),
            InputFile("/foo/bar/in.file"),
            OutputFile("out.txt"),
        ],
        requirements=[requirement_2],
    )

    obj = cls([cmd_mock_1, cmd_mock_2])
    assert obj.executables == cmd_mock_1.executables | cmd_mock_2.executables
    assert obj.requirements == cmd_mock_1.requirements | cmd_mock_2.requirements
    assert obj.input_files == cmd_mock_1.input_files | cmd_mock_2.input_files
    assert obj.output_files == cmd_mock_1.output_files | cmd_mock_2.output_files
    assert (
        obj.auxiliary_files == cmd_mock_1.auxiliary_files | cmd_mock_2.auxiliary_files
    )
    assert obj.expected_temp_files == frozenset(["out", "out.txt"])
    assert (
        obj.optional_temp_files
        == cmd_mock_1.optional_temp_files | cmd_mock_2.optional_temp_files
    )


_NO_CLOBBERING_KWARGS = (
    {"extra_files": [OutputFile("/bar/out.txt")]},
    {"extra_files": [TempOutputFile("out.txt")]},
    {"stdout": "/bar/out.txt"},
    {"stdout": TempOutputFile("out.txt")},
    {"stderr": "/bar/out.txt"},
    {"stderr": TempOutputFile("out.txt")},
)


# Ensure that commands in a set doesn't clobber eachothers OUT files
@pytest.mark.parametrize("cls", _SET_CLASSES)
@pytest.mark.parametrize("kwargs", _NO_CLOBBERING_KWARGS)
def test_atomicsets__no_clobbering(cls: SetTypes, kwargs: dict[str, Any]) -> None:
    cmd_1 = AtomicCmd(["true", OutputFile("/foo/out.txt")])
    cmd_2 = AtomicCmd("true", **kwargs)
    with pytest.raises(CmdError):
        cls([cmd_1, cmd_2])


###############################################################################
###############################################################################
# Functions with same expected behavior for both Parallel/SequentialCmds


@pytest.mark.parametrize("cls", _SET_CLASSES)
def test_atomicsets__commit(cls: SetTypes) -> None:
    mock: Any = Mock()
    cmd_1 = AtomicCmd(["ls"])
    cmd_1.commit = mock.commit_1
    cmd_2 = AtomicCmd(["ls"])
    cmd_2.commit = mock.commit_2
    cmd_3 = AtomicCmd(["ls"])
    cmd_3.commit = mock.commit_3

    cls((cmd_1, cmd_2, cmd_3)).commit()

    assert mock.mock_calls == [
        call.commit_1(),
        call.commit_2(),
        call.commit_3(),
    ]


@pytest.mark.parametrize("cls", _SET_CLASSES)
def test_atomicsets__commit__remove_files_on_failure(
    tmp_path: Path, cls: SetTypes
) -> None:
    (tmp_path / "tmp").mkdir()
    out_path = tmp_path / "out"

    cmd_1 = AtomicCmd(["touch", OutputFile(str(out_path / "file1"))])
    cmd_2 = AtomicCmd(["touch", OutputFile(str(out_path / "file2"))])
    cmd_2.commit = Mock()
    cmd_2.commit.side_effect = OSError("mocked failure")

    cmdset = cls((cmd_1, cmd_2))
    cmdset.run(str(tmp_path / "tmp"))
    assert cmdset.join() == [0, 0]

    with pytest.raises(OSError, match="mocked failure"):
        cmdset.commit()

    tmp_files = [it.name for it in (tmp_path / "tmp").iterdir()]
    assert "file1" not in tmp_files
    assert "file2" in tmp_files

    assert list((tmp_path / "out").iterdir()) == []


@pytest.mark.parametrize("cls", _SET_CLASSES)
def test_atomicsets__terminate(cls: SetTypes) -> None:
    mock: Any = Mock()
    cmd_1 = AtomicCmd(["ls"])
    cmd_1.terminate = mock.terminate_1
    cmd_2 = AtomicCmd(["ls"])
    cmd_2.terminate = mock.terminate_2
    cmd_3 = AtomicCmd(["ls"])
    cmd_3.terminate = mock.terminate_3

    cmds = cls((cmd_3, cmd_2, cmd_1))
    cmds.terminate()

    assert mock.mock_calls == [
        call.terminate_3(),
        call.terminate_2(),
        call.terminate_1(),
    ]


@pytest.mark.parametrize("cls", _SET_CLASSES)
def test_atomicsets__str__(cls: SetTypes) -> None:
    cmds = cls([AtomicCmd("ls")])
    assert paleomix.common.command.pformat(cmds) == str(cmds)


@pytest.mark.parametrize("cls", _SET_CLASSES)
def test_atomicsets__duplicate_cmds(cls: SetTypes) -> None:
    cmd_1 = AtomicCmd("true")
    cmd_2 = AtomicCmd("false")
    with pytest.raises(ValueError, match="Same command included multiple times"):
        cls([cmd_1, cmd_2, cmd_1])


###############################################################################
###############################################################################
# Parallel commands


def test_parallel_commands__run() -> None:
    mock: Any = Mock()
    cmd_1 = AtomicCmd(["ls"])
    cmd_1.run = mock.run_1
    cmd_2 = AtomicCmd(["ls"])
    cmd_2.run = mock.run_2
    cmd_3 = AtomicCmd(["ls"])
    cmd_3.run = mock.run_3

    cmds = ParallelCmds((cmd_1, cmd_2, cmd_3))
    cmds.run("xTMPx")

    assert mock.mock_calls == [
        call.run_1("xTMPx"),
        call.run_2("xTMPx"),
        call.run_3("xTMPx"),
    ]


@pytest.mark.parametrize("value", [True, False])
def test_parallel_commands__ready_single(*, value: bool) -> None:
    cmd = AtomicCmd(["ls"])
    cmd.ready = Mock()
    cmd.ready.return_value = value
    cmds = ParallelCmds([cmd])
    assert cmds.ready() == value

    assert cmd.ready.mock_calls


_READY_TWO_VALUES = (
    (True, True, True),
    (False, True, False),
    (True, False, False),
    (False, False, False),
)


@pytest.mark.parametrize(("first", "second", "result"), _READY_TWO_VALUES)
def test_parallel_commands__ready_two(
    *, first: bool, second: bool, result: bool
) -> None:
    cmd_1 = AtomicCmd(["ls"])
    cmd_1.ready = Mock()
    cmd_1.ready.return_value = first

    cmd_2 = AtomicCmd(["ls"])
    cmd_2.ready = Mock()
    cmd_2.ready.return_value = second
    cmds = ParallelCmds([cmd_1, cmd_2])
    assert cmds.ready() == result

    assert cmd_1.ready.mock_calls
    assert bool(first) == bool(cmd_2.ready.call_count)


def test_parallel_commands__join_before_run() -> None:
    mock: Any = Mock()
    cmd_1 = AtomicCmd(["ls"])
    cmd_1.join = mock.join_1
    cmd_2 = AtomicCmd(["ls"])
    cmd_2.join = mock.join_2
    cmd_3 = AtomicCmd(["ls"])
    cmd_3.join = mock.join_3

    cmds = ParallelCmds((cmd_3, cmd_2, cmd_1))
    assert cmds.join() == [None, None, None]

    assert mock.mock_calls == []


def test_parallel_commands__join_after_run(tmp_path: Path) -> None:
    cmds = ParallelCmds([AtomicCmd("true") for _ in range(3)])
    cmds.run(str(tmp_path))
    assert cmds.join() == [0, 0, 0]


def _sleep_mock() -> AtomicCmd:
    return AtomicCmd(("sleep", 10))


def _false_mock() -> AtomicCmd:
    return AtomicCmd("false")


def test_parallel_commands__join_failure_1(tmp_path: Path) -> None:
    mocks = [_false_mock(), _sleep_mock(), _sleep_mock()]
    cmds = ParallelCmds(mocks)
    cmds.run(str(tmp_path))
    assert cmds.join() == [1, "SIGTERM", "SIGTERM"]


def test_parallel_commands__join_failure_2(tmp_path: Path) -> None:
    mocks = [_sleep_mock(), _false_mock(), _sleep_mock()]
    cmds = ParallelCmds(mocks)
    cmds.run(str(tmp_path))
    assert cmds.join() == ["SIGTERM", 1, "SIGTERM"]


def test_parallel_commands__join_failure_3(tmp_path: Path) -> None:
    mocks = [_sleep_mock(), _sleep_mock(), _false_mock()]
    cmds = ParallelCmds(mocks)
    cmds.run(str(tmp_path))
    assert cmds.join() == ["SIGTERM", "SIGTERM", 1]


@pytest.mark.parametrize("cls", [SequentialCmds, ParallelCmds])
def test_parallel_commands__reject_sets(
    cls: type[SequentialCmds | ParallelCmds],
) -> None:
    command = AtomicCmd(["ls"])
    seqcmd = cls([command])
    with pytest.raises(CmdError):
        ParallelCmds([seqcmd])  # pyright: ignore[reportArgumentType]


def test_parallel_commands__reject_noncommand() -> None:
    with pytest.raises(CmdError):
        ParallelCmds([object()])  # pyright: ignore[reportArgumentType]


def test_parallel_commands__reject_empty_commandset() -> None:
    with pytest.raises(CmdError):
        ParallelCmds([])


###############################################################################
###############################################################################
# Sequential commands


def test_sequential_commands__atomiccmds() -> None:
    mock: Any = Mock()
    cmd_1 = AtomicCmd(["ls"])
    cmd_1.run = mock.run_1
    cmd_1.join = mock.join_1
    cmd_1.join.return_value = [0]
    cmd_2 = AtomicCmd(["ls"])
    cmd_2.run = mock.run_2
    cmd_2.join = mock.join_2
    cmd_2.join.return_value = [0]
    cmd_3 = AtomicCmd(["ls"])
    cmd_3.run = mock.run_3
    cmd_3.join = mock.join_3
    cmd_3.join.return_value = [0]

    cmds = SequentialCmds((cmd_1, cmd_2, cmd_3))
    assert not cmds.ready()
    cmds.run("xTMPx")
    assert cmds.ready()
    assert cmds.join() == [0, 0, 0]

    assert mock.mock_calls == [
        call.run_1("xTMPx"),
        call.join_1(),
        call.run_2("xTMPx"),
        call.join_2(),
        call.run_3("xTMPx"),
        call.join_3(),
        call.join_1(),
        call.join_2(),
        call.join_3(),
    ]


def test_sequential_commands__abort_on_error_1(tmp_path: Path) -> None:
    cmd_1 = AtomicCmd("false")
    cmd_2 = AtomicCmd(("sleep", 10))
    cmd_3 = AtomicCmd(("sleep", 10))
    cmds = SequentialCmds([cmd_1, cmd_2, cmd_3])
    cmds.run(str(tmp_path))
    assert cmds.join() == [1, None, None]


def test_sequential_commands__abort_on_error_2(tmp_path: Path) -> None:
    cmd_1 = AtomicCmd("true")
    cmd_2 = AtomicCmd("false")
    cmd_3 = AtomicCmd(("sleep", 10))
    cmds = SequentialCmds([cmd_1, cmd_2, cmd_3])
    cmds.run(str(tmp_path))
    assert cmds.join() == [0, 1, None]


def test_sequential_commands__abort_on_error_3(tmp_path: Path) -> None:
    cmd_1 = AtomicCmd("true")
    cmd_2 = AtomicCmd("true")
    cmd_3 = AtomicCmd("false")
    cmds = SequentialCmds([cmd_1, cmd_2, cmd_3])
    cmds.run(str(tmp_path))
    assert cmds.join() == [0, 0, 1]


def test_sequential_commands__accept_parallel() -> None:
    command = AtomicCmd(["ls"])
    parcmd = ParallelCmds([command])
    SequentialCmds([parcmd])


def test_sequential_commands__accept_sequential() -> None:
    command = AtomicCmd(["ls"])
    seqcmd = SequentialCmds([command])
    SequentialCmds([seqcmd])


def test_sequential_commands__reject_noncommand() -> None:
    with pytest.raises(CmdError):
        SequentialCmds([object()])  # pyright: ignore[reportArgumentType]


def test_sequential_commands__reject_empty_commandset() -> None:
    with pytest.raises(CmdError):
        SequentialCmds([])
