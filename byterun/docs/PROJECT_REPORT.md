---
title: "Python Virtual Machine (PVM) – Enhancement of the Byterun Bytecode Interpreter"
---

# 1. Project Title
**Python Virtual Machine (PVM): Adding Tracing, Statistics, Stack Visualisation, Error Handling and a Tkinter Interface to the Open-Source Byterun Bytecode Interpreter**

*Student name / Roll no. / Class / Guide: ____________ (fill in)*

# 2. Abstract
A Python Virtual Machine executes the *bytecode* that the Python compiler generates, one instruction at a time, using a *value stack* and a *program counter*. Byterun, an open-source project by Ned Batchelder, is a PVM written in pure Python, which makes it ideal for studying how Python really runs programs. In this project the original Byterun source code (commit `62f9b1a`) was downloaded, studied and extended. Eight additions were made: an instruction counter with per-opcode statistics, an execution trace, stack inspection and visualisation, an execution summary report, improved error handling with exact error location and call stack, an infinite-loop guard, a reset function and a Tkinter graphical interface that can run a program or execute it step by step. All original functionality is preserved: the 98 original tests still pass, and 32 new tests were written for the new features (130/130 passing on Python 2.7).

# 3. Introduction
When we run `python hello.py`, Python first compiles the source into bytecode and then a virtual machine executes it. Byterun re-implements that second step in Python, so every instruction can be inspected with ordinary Python code. Because Byterun has no way to *show* what is happening, it is hard for a beginner to learn from. This project adds the missing observation, safety and interface features.

# 4. Problem Statement
The original Byterun can run programs but: (a) gives no information about how many instructions ran or which were used; (b) cannot show the stack or the instruction being executed; (c) shows internal tracebacks that are hard for a beginner to read; (d) runs forever on an infinite loop; (e) cannot be reused cleanly after an error; (f) has no graphical interface. The problem is to extend Byterun to solve these without breaking existing behaviour.

# 5. Objectives
1. Study and explain the architecture of an existing open-source PVM.
2. Add at least four meaningful features that fit the existing design.
3. Preserve original behaviour (all original tests must still pass).
4. Provide a simple Tkinter interface for loading, running, stepping and inspecting programs.
5. Test every new feature and document the results honestly.

# 6. Existing System (original Byterun)
* Repository: https://github.com/nedbat/byterun – author Ned Batchelder, based on *pyvm2* by Paul Swartz; MIT licence.
* ~1 000-line `pyvm2.py` containing `VirtualMachine`, plus `pyobj.py` (Frame, Block, Function, Method, Generator), `execfile.py` (run a file/module) and `__main__.py` (command line).
* Supports Python 2.7 and 3.3 bytecode: 80 `byte_*` instruction methods, functions, closures, classes, generators, exceptions, `with` statements.
* Command line: `python -m byterun [-m] [-v] prog`. `-v` writes a very verbose log.
* **Limitations observed:** no statistics, no stack view, no loop protection, raw tracebacks, no GUI, and it does not run on modern Python (see Section 16).

# 7. Proposed System
The proposed system keeps the original VM and adds one **hook** (`before_instruction`) in the main loop plus three new modules (`runner`, `report`, `gui`). Features:

| # | Feature | Description |
|---|---|---|
| F1 | Instruction counter & opcode statistics | counts every instruction and each opcode |
| F2 | Execution trace | one line per instruction with offset, call depth and stack |
| F3 | Stack inspection/visualisation | text drawing of the stack, live in the GUI |
| F4 | Execution summary report | counts, depths, time, speed, top-5 opcodes |
| F5 | Better error handling | syntax/runtime/file/input errors with function, line, instruction, stack and call stack |
| F6 | Instruction limit | stops infinite loops safely |
| F7 | Reset functionality | VM and GUI return to a clean state |
| F8 | Tkinter GUI | load, Run, Step, stack, output, trace, statistics, errors |

# 8. Technologies Used
Python 2.7 (VM core requirement), `six` (2/3 compatibility, already used by Byterun), standard library only for new code: `dis`, `collections.Counter`, `time`, `threading`, `unittest`, `Tkinter`/`ttk`. Git/GitHub for the original code. Tools used for testing: Xvfb (virtual screen) to run the GUI test and take screenshots.

# 9. System Architecture

```
 source text / file
        |
   compile()  -->  code object (bytecode)
        |
  runner.run_source()  ---- catches errors, captures output --->  ExecutionResult
        |
  VirtualMachine.run_code --> run_frame loop:
        |        fetch+decode  parse_byte_and_args()
        |        [NEW] before_instruction()  --> counters, trace, limit, GUI hook
        |        execute        dispatch() -> byte_<OPCODE>()
        |        block/exception handling  manage_block_stack()
        v
  report.py (format stack / statistics / errors)  -->  CLI text or GUI panels
```
GUI: main thread (Tk window, polls every 40 ms) ⇄ worker thread (runs the VM; in step mode waits on a `threading.Event`).

# 10. Explanation of the Original GitHub Source Code

| File | Role |
|---|---|
| `byterun/__main__.py` | parses command line, chooses run-file or run-module |
| `byterun/execfile.py` | compiles the program, creates a `VirtualMachine`, runs it |
| `byterun/pyvm2.py` | the virtual machine: stack helpers (`push`, `pop`, `popn`, `peek`), frame handling (`make_frame`, `push_frame`, `pop_frame`), the loop `run_frame`, decoder `parse_byte_and_args`, `dispatch`, block stack, and 80 `byte_*` methods |
| `byterun/pyobj.py` | objects the VM needs: `Frame` (stack, block stack, `f_lasti` = program counter), `Block`, `Function`, `Method`, `Generator`, cells for closures |
| `tests/` | 98 tests; each runs a snippet in the VM **and** in real Python and compares output and exceptions |

**Execution cycle (fetch – decode – execute):** `parse_byte_and_args` reads one opcode byte at `f_lasti`, reads a 2-byte argument if the opcode needs one, resolves it (constant, name, local, jump target) and advances `f_lasti`. `dispatch` calls `byte_<NAME>`. Return values such as `'return'`, `'break'`, `'exception'` tell `run_frame` when to unwind the block stack or leave the frame. A function call creates a new `Frame` and recursively calls `run_frame`.

# 11. Newly Implemented Features
See `docs/CODE_EXPLANATION.md` for function-by-function details (name, purpose, input, output, how, why). Short description of each feature:

* **F1 Counter/statistics** – `before_instruction` increments `instruction_count` and `opcode_counts[name]`.
* **F2 Trace** – `add_trace_line` stores e.g. `#6 depth=1  15 CALL_FUNCTION 1   stack=[<Function f>, 21]`.
* **F3 Stack view** – `stack_as_list` + `report.format_stack` (top first, TOP/BOT labels).
* **F4 Summary** – `get_statistics` + `report.format_statistics`.
* **F5 Errors** – `record_error`, `line_of_instruction`, `runner.run_source/run_file`, `report.format_error`, input validation in the GUI, friendly missing-file message.
* **F6 Limit** – `InstructionLimitExceeded` raised when count > `max_instructions`.
* **F7 Reset** – `VirtualMachine.reset()`, GUI Reset button (also stops a running program).
* **F8 GUI** – `gui.py`.

**Bug-fix made on the way:** the original `Frame.line_number()` can return the line *after* the current one for the last instruction on a line. A new method `line_of_instruction` fixes this for errors and the GUI; the original method is left untouched.

# 12. Implementation Details
* Files changed: `byterun/pyvm2.py` (+179 lines, 1 changed), `byterun/__main__.py` (+51), `requirements.txt` (changed from `tox`/`six` to `six`).
* New files: `byterun/runner.py` (120 lines), `report.py` (87), `gui.py` (468), `run_gui.py`, `tests/test_extensions.py` (236 lines), 7 example programs.
* Every added line in original files is tagged `[NEW]`; exact diff in `docs/CHANGES_to_original_files.diff`.
* Design choice: one hook instead of changing each `byte_*` method – minimal risk to original behaviour.
* Statistics are sampled *before* each instruction, so `max_stack_depth` is the deepest stack observed at an instruction boundary.
* GUI threading: Tk is not thread-safe, so the worker thread only stores plain data; the main thread copies it into widgets.

# 13. Screenshots
Real screenshots (taken from the running GUI under a virtual screen) are in `docs/screenshots/`:
1. `01_loaded.png` – program loaded.
2. `02_stepping.png` – paused at instruction #15 of `03_factorial.py`; source line highlighted; stack and call stack shown.
3. `03_finished_stats.png` – finished run with the Statistics tab.
4. `04_error.png` – error demo: location, instruction, call stack.

**To capture your own:** run `python run_gui.py`, load an example, press Step several times, then use `Win+Shift+S` (Windows), `Cmd+Shift+4` (Mac) or PrtScn (Linux). Suggested set: loaded program, mid-step (stack visible), Statistics tab, Errors tab, Trace tab.

# 14. Testing and Results
Environment: Python 2.7.15 (conda-forge). All figures below were produced by running the code.

**Test suite** (`docs/test_results_py27.txt`): `Ran 130 tests ... OK`
* 98 original tests (unchanged) – **pass** → original functionality preserved.
* 32 new tests – **pass**: statistics (6), trace (4), stack (3), errors/limits/files (10), reset (3), report (1), command-line (5).

**Baseline before my changes** (original code, same machine): Python 2.7: 98/98 pass. Python 3.4.5: 35 failures + 1 error out of 101 (all class-related, original bug/incompatibility). Python 3.12: every test fails.

**Example programs** (measured):

| Program | Result | Instructions | Frames | Max call depth | Max stack |
|---|---|---|---|---|---|
| 01_hello_math | OK | 41 | 1 | 1 | 3 |
| 02_loop_sum | OK | 87 | 1 | 1 | 3 |
| 03_factorial | OK | 163 | 14 | 9 | 4 |
| 04_fibonacci | OK | 205 | 2 | 2 | 4 |
| 05_error_demo | runtime error shown with call stack `<module> › calculate › divide` | 18 | 3 | 3 | 3 |
| 06_infinite_loop (limit 5000) | stopped safely | 5001 | 1 | 1 | 2 |
| 07_class_demo | OK | 62 | 5 | 2 | 3 |

Output of examples 01–04 and 07 is **identical** to real Python 2.7 (compared with `cmp`).

**GUI test** (automated, Xvfb): load example → step 15 times (status shows "Paused before instruction #15") → Run to end (163 instructions, output correct) → error program (Errors tab, line highlighted) → infinite loop (limit message) → invalid limit text (INPUT ERROR) → empty program (INPUT ERROR) → syntax error (SYNTAX ERROR) → Reset during stepping (state returns to idle). All behaved as expected.

# 15. Advantages
* Original code and tests preserved; changes are small, tagged and reviewable.
* Makes the invisible visible: learners can watch the stack change.
* Safe: no infinite-loop hangs, no unexplained crashes, clear error locations.
* Beginner-friendly CLI options and simple GUI; no third-party packages except `six`.
* Well tested (32 new tests) and documented.

# 16. Limitations
* The VM core only supports **Python 2.7 bytecode** (and partly 3.3). It does not run on Python ≥ 3.6 (new "wordcode" format and many new opcodes such as `RESUME`) – this is an inherited limitation of Byterun. The project therefore must be run with Python 2.7.
* Python 2.7 is end-of-life; use it only in an isolated environment.
* The GUI executes one program at a time; user programs that read input (`raw_input`) are not supported in the window.
* Trace is capped at 20 000 lines; the GUI shows only the stack of the current frame.
* Running very large programs is slow (a Python interpreter running inside Python).

# 17. Future Scope
* Port the VM to modern Python bytecode (3.8–3.12).
* Breakpoints, "step over/step out", and variable (locals/globals) inspector in the GUI.
* Export statistics to CSV, charts of opcode frequency.
* Show disassembly side by side with source.
* Input support (stdin box) for interactive programs.

# 18. Conclusion
The project met its aims: a real open-source PVM was studied, extended with eight working features and a Tkinter interface, original behaviour was preserved (98/98 original tests) and the additions were verified (32 new tests, example comparison and automated GUI test). It also showed an important practical fact about virtual machines – they are tied to the bytecode version they implement – which explains why Byterun needs Python 2.7.

# 19. GitHub Repository Reference
* Original project: https://github.com/nedbat/byterun (commit `62f9b1a9c85f52c28b78cc8942243c5c962b1954`, 15 Oct 2019). © 2013 Ned Batchelder, MIT licence.
* Our modified version: submitted as the ZIP file. (If you upload it to your own GitHub account, add that link here, and state clearly that it is a modification of nedbat/byterun.)
