"""[NEW FILE] Tests for the features added in this project.

The original tests (test_basic, test_functions, ...) are unchanged and test
the original VM. These tests cover ONLY the new features.

Run:  python -m unittest tests.test_extensions
"""

from __future__ import print_function

import os
import subprocess
import sys
import tempfile
import unittest

from byterun import report
from byterun.pyvm2 import (VirtualMachine, InstructionLimitExceeded,
                           ExecutionStopped)
from byterun.runner import run_source, run_file

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

FACT = "def f(n):\n    if n <= 1:\n        return 1\n    return n * f(n - 1)\nprint(f(4))\n"


class TestStatistics(unittest.TestCase):

    def test_instruction_counter(self):
        r = run_source("x = 1\n")
        # LOAD_CONST, STORE_NAME, LOAD_CONST, RETURN_VALUE
        self.assertEqual(r.statistics["instructions"], 4)

    def test_opcode_counts_add_up(self):
        r = run_source(FACT)
        s = r.statistics
        self.assertEqual(sum(s["opcode_counts"].values()), s["instructions"])
        self.assertEqual(s["unique_opcodes"], len(s["opcode_counts"]))

    def test_call_depth_and_frames(self):
        r = run_source(FACT)
        self.assertEqual(r.statistics["max_call_depth"], 5)   # module + f x4
        self.assertEqual(r.statistics["frames_created"], 5)

    def test_max_stack_depth(self):
        r = run_source("a = 1\nb = 2\nx = (a + b) * (a + b)\n")
        self.assertGreaterEqual(r.statistics["max_stack_depth"], 2)

    def test_elapsed_time_recorded(self):
        r = run_source("x = 1\n")
        self.assertTrue(r.statistics["elapsed_seconds"] >= 0)

    def test_output_matches_real_python(self):
        r = run_source(FACT)
        self.assertTrue(r.ok)
        self.assertEqual(r.output.strip(), "24")


class TestTrace(unittest.TestCase):

    def test_trace_off_by_default(self):
        self.assertEqual(run_source("x = 1\n").trace, [])

    def test_trace_has_one_line_per_instruction(self):
        r = run_source("x = 1\n", trace=True)
        self.assertEqual(len(r.trace), r.statistics["instructions"])
        self.assertIn("LOAD_CONST", r.trace[0])
        self.assertIn("stack=[]", r.trace[0])

    def test_trace_shows_stack(self):
        r = run_source("x = 7\n", trace=True)
        self.assertIn("stack=[7]", r.trace[1])      # before STORE_NAME

    def test_trace_is_capped(self):
        vm = VirtualMachine()
        vm.max_trace_lines = 3
        r = run_source("for i in range(10):\n    pass\n", vm=vm, trace=True)
        self.assertEqual(len(r.trace), 3)
        self.assertTrue(vm.trace_truncated)


class TestStack(unittest.TestCase):

    def test_stack_snapshot_in_hook(self):
        seen = []

        def hook(vm, name, args, offset):
            seen.append(vm.stack_as_list())
        run_source("x = 5\n", hook=hook)
        self.assertEqual(seen[1], ["5"])

    def test_format_stack_empty(self):
        self.assertIn("(stack is empty)", report.format_stack([]))

    def test_format_stack_order(self):
        text = report.format_stack(["a", "b", "c"])
        self.assertLess(text.index("c"), text.index("a"))   # top first
        self.assertIn("TOP", text)
        self.assertIn("BOT", text)


class TestErrors(unittest.TestCase):

    def test_syntax_error(self):
        r = run_source("x = (\n")
        self.assertFalse(r.ok)
        self.assertEqual(r.error_kind, "syntax")
        self.assertIn("SYNTAX ERROR", r.error)

    def test_runtime_error_details(self):
        src = "def a():\n    return 1 / 0\ndef b():\n    return a()\nb()\n"
        r = run_source(src)
        self.assertFalse(r.ok)
        self.assertEqual(r.error_kind, "runtime")
        info = r.vm.error_info
        self.assertEqual(info["type"], "ZeroDivisionError")
        self.assertEqual(info["function"], "a")
        self.assertEqual(info["line"], 2)
        names = [name for name, line in info["call_stack"]]
        self.assertEqual(names, ["<module>", "b", "a"])
        self.assertIn("RUNTIME ERROR", r.error)

    def test_error_line_of_last_instruction_on_line(self):
        r = run_source("x = 1\ny = undefined_name\n")
        self.assertEqual(r.vm.error_info["line"], 2)

    def test_caught_error_is_not_a_failure(self):
        r = run_source("try:\n    1/0\nexcept ZeroDivisionError:\n    print('ok')\n")
        self.assertTrue(r.ok)
        self.assertEqual(r.output.strip(), "ok")

    def test_instruction_limit(self):
        r = run_source("while True:\n    pass\n", max_instructions=100)
        self.assertEqual(r.error_kind, "limit")
        self.assertIn("LIMIT REACHED", r.error)
        self.assertEqual(r.statistics["instructions"], 101)

    def test_limit_not_hit_for_small_program(self):
        self.assertTrue(run_source("x = 1\n", max_instructions=100).ok)

    def test_hook_can_stop_vm(self):
        def hook(vm, name, args, offset):
            raise ExecutionStopped()
        r = run_source("x = 1\n", hook=hook)
        self.assertEqual(r.error_kind, "stopped")

    def test_missing_file(self):
        r = run_file(os.path.join(ROOT, "no_such_file.py"))
        self.assertEqual(r.error_kind, "file")
        self.assertIn("FILE ERROR", r.error)

    def test_run_file_ok(self):
        path = os.path.join(ROOT, "examples", "03_factorial.py")
        r = run_file(path)
        self.assertTrue(r.ok)
        self.assertIn("120", r.output)

    def test_format_error_without_info(self):
        self.assertEqual(report.format_error(None, "boom"), "boom")


class TestReset(unittest.TestCase):

    def test_reset_clears_everything(self):
        vm = VirtualMachine()
        run_source(FACT, vm=vm, trace=True)
        self.assertTrue(vm.instruction_count > 0)
        vm.reset()
        self.assertEqual(vm.instruction_count, 0)
        self.assertEqual(len(vm.opcode_counts), 0)
        self.assertEqual(vm.trace_lines, [])
        self.assertEqual(vm.frames, [])
        self.assertIsNone(vm.error_info)
        self.assertEqual(vm.max_call_depth, 0)

    def test_vm_reusable_after_error(self):
        vm = VirtualMachine()
        self.assertFalse(run_source("1/0\n", vm=vm).ok)
        r = run_source("print(5)\n", vm=vm)
        self.assertTrue(r.ok)
        self.assertEqual(r.output.strip(), "5")
        self.assertIsNone(vm.error_info)

    def test_counters_restart_for_each_run(self):
        vm = VirtualMachine()
        a = run_source("x = 1\n", vm=vm).statistics["instructions"]
        b = run_source("x = 1\n", vm=vm).statistics["instructions"]
        self.assertEqual(a, b)


class TestReports(unittest.TestCase):

    def test_summary_report_text(self):
        text = report.format_statistics(run_source(FACT).statistics)
        for word in ("EXECUTION SUMMARY", "Instructions executed",
                     "Max call depth", "Top 5 most used opcodes"):
            self.assertIn(word, text)


class TestCommandLine(unittest.TestCase):

    def run_cli(self, *args):
        cmd = [sys.executable, "-m", "byterun"] + list(args)
        proc = subprocess.Popen(cmd, cwd=ROOT, stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE)
        out, err = proc.communicate()
        return proc.returncode, out.decode("utf-8"), err.decode("utf-8")

    def test_original_usage_still_works(self):
        code, out, err = self.run_cli("examples/03_factorial.py")
        self.assertEqual(code, 0)
        self.assertIn("120", out)

    def test_stats_option(self):
        code, out, err = self.run_cli("--stats", "examples/03_factorial.py")
        self.assertEqual(code, 0)
        self.assertIn("EXECUTION SUMMARY", out)

    def test_limit_option(self):
        code, out, err = self.run_cli("--limit", "500", "examples/06_infinite_loop.py")
        self.assertEqual(code, 1)
        self.assertIn("LIMIT REACHED", out)

    def test_trace_option(self):
        code, out, err = self.run_cli("--trace", "examples/01_hello_math.py")
        self.assertEqual(code, 0)
        self.assertIn("LOAD_CONST", out)

    def test_missing_file_message(self):
        code, out, err = self.run_cli("nope.py")
        self.assertEqual(code, 2)
        self.assertIn("FILE ERROR", err)


if __name__ == "__main__":
    unittest.main()
