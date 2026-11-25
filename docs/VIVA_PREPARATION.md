---
title: "Viva Preparation – Python Virtual Machine (Byterun extension)"
---

# Part A – Simple explanations

**What is a Python Virtual Machine?**
A program that runs Python programs. Python first translates your source code into *bytecode* (simple instructions) and the virtual machine (PVM) executes those instructions. The normal PVM (CPython) is written in C. Byterun is a PVM written in Python.

**What is bytecode?**
A compact list of low-level instructions such as `LOAD_CONST`, `BINARY_ADD`, `STORE_NAME`. It is not machine code; it is for the virtual machine. You can see it with `import dis; dis.dis(func)`.

**How does a virtual machine execute instructions?**
It repeats three steps: **fetch** the next instruction, **decode** it (find the opcode and argument), **execute** it. Byterun does this in `run_frame` → `parse_byte_and_args` → `dispatch`.

**What is a stack?**
A "last in, first out" list. The VM puts values on top (push) and takes them from the top (pop). For `1 + 2`: push 1, push 2, `BINARY_ADD` pops both and pushes 3.

**What is the program counter?**
The number saying which byte of the bytecode to read next. In Byterun it is `frame.f_lasti`. Jumps (loops, if) just change this number.

**How does the original GitHub project work?**
`__main__` → `execfile` compiles the file → `VirtualMachine.run_code` makes a `Frame` → `run_frame` loops fetching instructions → `dispatch` calls `byte_<OPCODE>` methods that push/pop the frame's stack → function calls create new frames → when the frame returns, the result is returned.

**What modifications did we make?**
One hook (`before_instruction`) in the main loop, plus helper methods in `pyvm2.py`; a new `runner.py` (safe running), `report.py` (text reports), `gui.py` (Tkinter window); new command-line options; examples; 32 new tests.

**Why did we add these features?**
Statistics, trace and stack view help us *see* how the VM works. Error handling and the instruction limit make it safe and friendly. The GUI makes it easy to demonstrate. Reset lets us reuse the VM.

**Advantages of our modified project?**
Original behaviour kept (98 original tests pass); small tagged changes; educational (step-by-step view); safe (no hangs); tested; no extra libraries.

# Part B – 27 viva questions and answers

1. **What is the purpose of your project?** To extend an existing open-source Python VM (Byterun) with tracing, statistics, stack visualisation, better error handling, a loop guard, reset and a GUI.
2. **Which GitHub project did you use?** nedbat/byterun by Ned Batchelder, commit `62f9b1a`, MIT licence.
3. **Why did you choose Byterun?** It is small (about 1 000 lines in the VM), written in pure Python, has a clear fetch-decode-execute loop and a good test suite, so it is easy to understand and extend.
4. **Why does the project need Python 2.7?** Bytecode format changes between Python versions. Byterun implements the 2.7 / 3.3 format. On Python 3.12 it fails with `unknown bytecode type: RESUME`; on 3.4.5 many class tests fail. On 2.7 all 98 original tests pass.
5. **What is the difference between interpreter and virtual machine?** An interpreter reads source and executes it; Python's design is hybrid: compile to bytecode, then the VM interprets the bytecode. The VM is the part that executes bytecode.
6. **What is a code object?** The compiled form of a piece of code. It holds `co_code` (bytecode), `co_consts`, `co_names`, `co_varnames`, `co_lnotab` (line table), etc. Each function has its own code object.
7. **What is a frame?** The runtime state of one function call: value stack, block stack, local and global variables, and the program counter (`f_lasti`). Byterun's `Frame` is in `pyobj.py`.
8. **What is the value stack and what is the block stack?** The value stack holds temporary values for calculations. The block stack remembers active loops, `try/except/finally` and `with` blocks so `break`, `continue` and exceptions know where to jump.
9. **What is the call stack?** The list of frames in progress (`vm.frames`). It grows when a function is called and shrinks on return; deep recursion makes it deep (our factorial example reaches depth 9).
10. **Explain `dispatch`.** It builds the name `byte_` + opcode name and calls that method with `getattr`. Operators like `BINARY_ADD` go to `binaryOperator`. Exceptions are caught and converted into the value `'exception'`.
11. **Where exactly did you hook your code and why there?** In `run_frame`, right after `parse_byte_and_args`, by calling `before_instruction`. Every instruction of every frame goes through that line, so one hook gives counters, trace, limit and GUI stepping without touching the 80 instruction methods.
12. **How does the instruction counter work?** `before_instruction` adds 1 to `instruction_count` and to `opcode_counts[name]` (a `Counter`) before each instruction.
13. **How does the trace work?** If `trace_enabled` is true, `add_trace_line` formats the counter, call depth, offset, opcode, argument and stack into a string and stores/prints it. It is capped at 20 000 lines to save memory.
14. **How is the stack visualised?** `stack_as_list` copies the stack as short strings; `report.format_stack` draws it as a box with the top first, marked TOP and BOT. The GUI shows it at each step.
15. **How does the instruction limit work and why is it needed?** If `instruction_count > max_instructions`, `InstructionLimitExceeded` is raised. It stops infinite loops like `while True: pass`, which would otherwise freeze the program or the window.
16. **How does step-by-step execution in the GUI work?** The VM runs in a worker thread. In step mode the hook saves a snapshot and waits on a `threading.Event`. The Step button sets the event, so exactly one instruction runs, then the hook pauses again. The main thread polls every 40 ms and updates the window.
17. **Why use a thread in the GUI?** Without it, a running VM would block Tkinter's main loop and the window would freeze. Tkinter widgets can only be changed from the main thread, so the worker only produces data and the main thread displays it.
18. **How does your error handling work?** `runner.run_source` catches syntax errors (compile step), runtime errors, limit, stop and file errors, and returns them as an `ExecutionResult`. `record_error` stores function, line, instruction, stack and call stack of the first error; `format_error` prints it. The GUI also validates the limit box and empty program.
19. **What does `reset()` do?** Clears frames, return value, last exception, counters, trace and error info so the VM can run another program; settings are kept. The GUI Reset also stops a running program.
20. **Did you break any original functionality? How do you know?** No. The 98 original tests, which compare the VM's output with real Python, still pass; without new options the original code path runs.
21. **What bug did you find and fix?** The original `Frame.line_number()` can give the next line for the last instruction of a line. I added `line_of_instruction` (uses `f_lasti - 1`) for errors and the GUI, and tested it.
22. **What are the limitations?** Needs Python 2.7; one program at a time; no `raw_input` in the GUI; trace capped; it is slow because it is Python running on Python.
23. **What is `Counter`?** A dictionary from `collections` that counts items; `most_common(5)` returns the five largest counts. We use it for opcode statistics.
24. **How did you test the GUI?** With an automated script under a virtual display (Xvfb) that calls the button actions and checks the status/outputs, and by taking screenshots; the real logic (runner, VM) has unit tests.
25. **What future improvements are possible?** Port to modern bytecode, breakpoints, locals/globals inspector, step-over/step-out, CSV export of statistics, stdin box.
26. **(Bonus) What does `1 + 2` look like in bytecode?** `LOAD_CONST 1`, `LOAD_CONST 2`, `BINARY_ADD`, `STORE_NAME x`; stack: `[] → [1] → [1,2] → [3] → []` (CPython 2.7 may fold it into `LOAD_CONST 3`; use variables to see the addition).
27. **(Bonus) Who wrote the original, and which licence?** Ned Batchelder (based on *pyvm2* by Paul Swartz), MIT licence. We keep the licence and give credit.

# Part C – 5-minute demo script
1. Show the original: `python -m byterun examples/03_factorial.py`.
2. Show statistics: `python -m byterun --stats examples/03_factorial.py` – explain instructions, call depth 9.
3. Show trace: `python -m byterun --trace examples/01_hello_math.py` – point at the stack column.
4. Show safety: `python -m byterun --limit 1000 examples/06_infinite_loop.py`.
5. Show error: `python -m byterun --stats examples/05_error_demo.py`.
6. Open GUI: `python run_gui.py` → File › Load Example › 03_factorial → Step 10 times (stack, highlighted line) → Run → Statistics tab → Reset.
7. Show tests: `python -m unittest tests.test_basic ... tests.test_extensions` → 130 OK.
8. Show `docs/CHANGES_to_original_files.diff` to prove the changes are on the original files.
