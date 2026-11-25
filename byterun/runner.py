"""[NEW FILE] A safe, easy way to run a program on the VM.

`run_source()` is used by the command line, the GUI and the new tests.
It never lets an error crash the caller: every problem (syntax error,
runtime error, infinite loop, user stop) is returned inside the result.
"""

from __future__ import print_function

import logging
import sys

import six

from .pyvm2 import (VirtualMachine, VirtualMachineError,
                    InstructionLimitExceeded, ExecutionStopped)
from . import report

# The VM logs caught exceptions; this stops Python 2 printing a warning.
logging.getLogger("byterun").addHandler(logging.NullHandler())


class ExecutionResult(object):
    """Everything that happened during one run."""

    def __init__(self):
        self.ok = False             # True if the program finished normally
        self.output = ""            # text printed by the program
        self.error = None           # error message (string) or None
        self.error_kind = None      # "syntax", "runtime", "limit", "stopped"
        self.return_value = None
        self.statistics = {}        # copy of vm.get_statistics()
        self.trace = []             # list of trace lines
        self.vm = None


def run_source(source, filename="<program>", vm=None, trace=False,
               max_instructions=None, hook=None, output_stream=None,
               trace_stream=None):
    """Compile `source` (a string) and run it on a VirtualMachine.

    Input : source           - Python source code text
            filename         - name shown in error messages
            vm               - an existing VirtualMachine to reuse (or None)
            trace            - True to record one trace line per instruction
            max_instructions - stop after this many instructions (or None)
            hook             - function called before every instruction
            output_stream    - object to collect print() output (or None)
            trace_stream     - object that receives trace lines live (or None)
    Output: an ExecutionResult object. This function does not raise errors.
    """
    result = ExecutionResult()
    if vm is None:
        vm = VirtualMachine()
    else:
        vm.reset()
    vm.trace_enabled = trace
    vm.trace_stream = trace_stream
    vm.max_instructions = max_instructions
    vm.instruction_hook = hook
    result.vm = vm

    # Step 1: compile the text into a code object (can fail: SyntaxError).
    try:
        code = compile(source, filename, "exec", 0, 1)
    except SyntaxError as err:
        result.error_kind = "syntax"
        result.error = "SYNTAX ERROR: %s (line %s)" % (err.msg, err.lineno)
        return result
    except (TypeError, ValueError) as err:       # e.g. null bytes in source
        result.error_kind = "syntax"
        result.error = "COMPILE ERROR: %s" % err
        return result

    # Step 2: run it, catching print() output so we can show it later.
    if output_stream is None:
        output_stream = six.StringIO()
    real_stdout = sys.stdout
    sys.stdout = output_stream
    try:
        result.return_value = vm.run_code(code)
        result.ok = True
    except InstructionLimitExceeded as err:
        result.error_kind = "limit"
        result.error = "LIMIT REACHED: %s" % err
    except ExecutionStopped:
        result.error_kind = "stopped"
        result.error = "Execution was stopped by the user."
    except VirtualMachineError as err:
        result.error_kind = "runtime"
        result.error = "VM ERROR: %s" % err
    except BaseException as err:
        result.error_kind = "runtime"
        result.error = report.format_error(
            vm.error_info, "%s: %s" % (type(err).__name__, err))
    finally:
        sys.stdout = real_stdout

    # A plain file (like sys.stdout) has no getvalue(); its text is already shown.
    getvalue = getattr(output_stream, "getvalue", None)
    result.output = getvalue() if getvalue else ""
    result.statistics = vm.get_statistics()
    result.trace = list(vm.trace_lines)
    return result


def run_file(path, **options):
    """Read the file at `path` and run it with run_source().

    A missing or unreadable file is reported in the result, not raised.
    """
    try:
        with open(path, "r") as handle:
            source = handle.read()
    except (IOError, OSError) as err:
        result = ExecutionResult()
        result.error_kind = "file"
        result.error = "FILE ERROR: cannot read '%s' (%s)" % (path, err)
        return result
    return run_source(source, filename=path, **options)
