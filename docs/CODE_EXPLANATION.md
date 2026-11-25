# Code explanation – every newly added function

Legend: **[orig]** = existing Byterun code, **[NEW]** = written for this project.

## 0. How the ORIGINAL VM works (read this first)

1. `__main__.py` reads the command line and calls `execfile.run_python_file`.
2. `execfile.py` compiles the file into a **code object** (`compile()`), then creates a `VirtualMachine` and calls `vm.run_code(code, ...)`.
3. A code object contains `co_code` (the **bytecode**: a string of bytes, one opcode per instruction, some followed by a 2-byte argument), `co_consts` (constants), `co_names` (variable names).
4. `run_code` builds a **Frame** (`pyobj.Frame`): a frame holds the **value stack** (`frame.stack`), the **block stack** (loops/try), local/global variables, and `f_lasti` = the **program counter** (offset of the next byte to read).
5. `run_frame` is the main loop:
   * `parse_byte_and_args()` – FETCH + DECODE: reads one opcode (e.g. 100 → `LOAD_CONST`) and its argument, moves `f_lasti` forward.
   * `dispatch()` – EXECUTE: finds the method named `byte_<OPNAME>` (80 of them, e.g. `byte_LOAD_CONST`, `byte_STORE_NAME`) and calls it. Binary/unary operators go to `binaryOperator()` etc. which use Python's `operator` module.
   * If the instruction caused a jump/return/exception, `manage_block_stack()` handles it.
6. Calling a function creates a new Frame (`pyobj.Function.__call__` → `vm.make_frame` → `vm.run_frame`), pushed on `vm.frames` (the **call stack**).

Example: `x = 1 + 2` becomes `LOAD_CONST 1; LOAD_CONST 2; BINARY_ADD; STORE_NAME x`
(or `LOAD_CONST 3; STORE_NAME x` because the compiler pre-computes constants).
Stack: `[] → [1] → [1,2] → [3] → []`.

The best place to add features is **one single point: the line in `run_frame` right after an instruction is decoded** – every instruction of every function passes there.

## 1. Changes inside `byterun/pyvm2.py` (original file)

### `class InstructionLimitExceeded(VirtualMachineError)` / `class ExecutionStopped(VirtualMachineError)`
* **Purpose:** two special error types. *Limit* = program ran too many instructions. *Stopped* = user pressed Reset in the GUI.
* **Why:** lets other code tell "my safety feature stopped the program" apart from "the program had a bug".

### `VirtualMachine.__init__` (extended)
Adds settings: `trace_enabled`, `trace_stream`, `max_trace_lines`, `max_instructions`, `instruction_hook`, then calls `reset_statistics()`.

### `reset_statistics(self)` **[NEW]**
* **Purpose:** put all counters to zero/empty.
* **Input:** none. **Output:** none (changes the object).
* **How:** assigns `instruction_count = 0`, an empty `Counter()` for opcodes, `max_stack_depth = 0`, `max_call_depth = 0`, `frames_created = 0`, empty `trace_lines`, `error_info = None`, times `None`.
* **Why:** used at start-up and by `reset()` so each run starts clean.

### `reset(self)` **[NEW]**
* **Purpose:** return the VM to a clean state to run another program (the "Reset functionality").
* **Input/Output:** none.
* **How:** empties `frames`, `frame`, `return_value`, `last_exception`, then calls `reset_statistics()`. Settings (trace on/off, limit) are kept.
* **Why:** after an error the VM still has half-finished frames; reset removes them so the VM can be reused.

### `before_instruction(self, byteName, arguments, opoffset)` **[NEW]**
* **Purpose:** the single hook called before *every* instruction.
* **Input:** instruction name, argument list, offset in the bytecode.
* **Output:** none; may raise `InstructionLimitExceeded`.
* **How:** (1) `instruction_count += 1`; (2) `opcode_counts[name] += 1`; (3) updates `max_stack_depth` from `len(frame.stack)`; (4) if tracing, calls `add_trace_line`; (5) if the count passed `max_instructions`, raises the limit error; (6) calls `instruction_hook` if set (GUI step mode uses this to pause).
* **Why:** one place = one small change to the original loop, but gives statistics, trace, safety and stepping.

### `add_trace_line(self, byteName, arguments, opoffset)` **[NEW]**
* **Purpose:** create one readable line, e.g. `#7 depth=1  12 CALL_FUNCTION 1   stack=[<Function f>, 21]`.
* **How:** formats counter, call depth, offset, opcode, argument (cut to 40 chars) and the stack; stores it in `trace_lines` (max 20 000 lines so memory stays small; sets `trace_truncated`), and writes it to `trace_stream` if given.
* **Why:** shows learners exactly how the stack changes, instruction by instruction.

### `stack_as_list(self)` / `stack_as_text(self)` **[NEW]**
* **Purpose:** copy of the current value stack as short strings (`['5', "'hi'"]`) or one line `[5, 'hi']`.
* **Input:** none. **Output:** list of str / str. Bottom of stack is first.
* **How:** `repr(item)[:40]` for each item in `frame.stack`.
* **Why:** a safe snapshot for the trace, errors and GUI (long objects are shortened).

### `line_of_instruction(self, frame)` **[NEW]**
* **Purpose:** the source line of the instruction just fetched.
* **Input:** a frame. **Output:** int line number.
* **How:** walks the code's `co_lnotab` table (byte-offset→line table) using `f_lasti - 1`, the last byte of the instruction.
* **Why:** the original `Frame.line_number()` can report the *next* line for the last instruction of a line, which would highlight the wrong line in the GUI and in error messages (I tested this: see `test_error_line_of_last_instruction_on_line`).

### `record_error(self, byteName)` **[NEW]**
* **Purpose:** remember *where* the first error happened.
* **Input:** name of the failing instruction. **Output:** none; fills `error_info`.
* **How:** called from `dispatch` when an exception is caught. Stores type, message, opcode, function, file, line, stack and the full call stack (function names + lines). If the same exception object travels up through outer frames it is **not** recorded again, so the *original* location is kept.
* **Why:** a beginner gets "ZeroDivisionError in function divide, line 3" instead of a confusing internal traceback.

### `get_statistics(self)` **[NEW]**
* **Purpose:** return all numbers in one dictionary (instructions, unique opcodes, opcode_counts, 5 most common, max stack, max call depth, frames, elapsed seconds).
* **Why:** one clean object for the report, the GUI and the tests.

### `push_frame` (extended) / `run_code` (extended) / `dispatch` (extended) / `run_frame` (extended)
Each has 1–5 added lines marked `[NEW]`: `push_frame` counts frames and call depth; `run_code` records start/end time (in `try/finally`, so the time is stored even when there is an error); `dispatch` calls `record_error`; `run_frame` calls `before_instruction`.

## 2. `byterun/runner.py` (new file)

### `class ExecutionResult`
Plain container: `ok`, `output`, `error`, `error_kind` (`syntax`/`runtime`/`limit`/`stopped`/`file`), `return_value`, `statistics`, `trace`, `vm`.

### `run_source(source, filename, vm, trace, max_instructions, hook, output_stream, trace_stream)`
* **Purpose:** compile text and run it on the VM **without ever crashing the caller**.
* **Output:** an `ExecutionResult`.
* **How:** (1) reset/create VM and apply settings; (2) `compile()` – a `SyntaxError` becomes a message with line number; (3) temporarily replace `sys.stdout` to capture `print` output; (4) call `vm.run_code`; (5) catch limit, stopped, VM and any other error and convert to text; (6) always restore `sys.stdout` (`finally`); (7) copy statistics and trace into the result.
* **Why:** CLI, GUI and tests all share this one safe entry point ("better error handling").

### `run_file(path, **options)`
Reads a file then calls `run_source`. A missing/unreadable file gives `error_kind == "file"` and a `FILE ERROR` message instead of a traceback.

## 3. `byterun/report.py` (new file)

### `format_stack(stack_items, width=34)`
Draws the stack as a box, **top first**, with `TOP`/`BOT` labels and index numbers; `(stack is empty)` if empty. Input: list of strings (bottom first). Output: multi-line string.

### `format_statistics(stats)`
Builds the "EXECUTION SUMMARY REPORT": instructions, different opcodes, frames, max call depth, max stack depth, time, speed (instructions/second), top-5 opcodes with percentages. Input: dict from `get_statistics()`.

### `format_error(error_info, error_text=None)`
Builds the multi-line friendly error message (type, message, function, line, instruction, stack, call stack).

## 4. `byterun/gui.py` (new file)

### `make_snapshot(vm, byte_name, arguments, offset)`
Copies what the window needs (instruction, offset, line, function, stack, call stack, counter) into a dict. Safe to pass between threads because it holds only strings/numbers.

### `class ExecutionController`
Runs the VM in a **worker thread** so the window does not freeze.
* `start(source, mode, trace, limit)` – stops any old run, creates the thread.
* `_work(...)` – thread body: calls `run_source`, stores the result, sets `finished`.
* `_hook(...)` – called before each instruction; in *step* mode it saves a snapshot and **waits on a `threading.Event`** until the user presses Step.
* `step()` – releases the event (runs one instruction). `run_to_end()` – switches to full speed. `stop()` – sets a flag, releases the event and joins the thread (the hook then raises `ExecutionStopped`).

### `class PVMApp`
* `build_widgets/build_menu/make_text/add_tab` – create the window (toolbar, source box, instruction panel, stack panel, tabs Output/Trace/Statistics/Errors, status bar, File menu with the examples).
* `open_file`, `load_path` – load a program; unreadable file → message in the Errors tab.
* `read_limit` – validates the "Max instructions" box (must be a positive integer or empty).
* `begin`, `on_run`, `on_step`, `on_reset`, `on_close` – button actions. Empty program or invalid limit → `INPUT ERROR` message.
* `poll` – every 40 ms copies new information (output, trace, statistics, snapshot, final result) from the worker to the window. Tk widgets may only be touched by the main thread, which is why the worker never updates them directly.
* `show_snapshot`, `highlight_line`, `show_result`, `set_state`, `set_text`, `show_error` – display helpers.
* `main(path=None)` – creates the window.

## 5. `byterun/__main__.py` (original file, extended)
New options `--trace/-t`, `--stats/-s`, `--limit/-l N`, `--gui/-g`; `prog` became optional (so `--gui` needs no file); friendly message when the file does not exist. If none of the new options is used, the **original code path runs unchanged**.
