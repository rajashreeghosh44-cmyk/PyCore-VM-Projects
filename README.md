# Python Virtual Machine (PVM) – Enhanced Byterun

A college project that **extends the real open-source project
[nedbat/byterun](https://github.com/nedbat/byterun)** (a Python bytecode
virtual machine written in Python by Ned Batchelder, MIT licence).

* Original repository : https://github.com/nedbat/byterun
* Commit used          : `62f9b1a9c85f52c28b78cc8942243c5c962b1954` (15 Oct 2019, "BUG: Fix missing builtins.")
* Our work              : new features added on top of the original source (see below)

---------------------------------------------------------------------

## 1. IMPORTANT – which Python version to use

Byterun is from 2013–2019 and executes the bytecode format of **Python 2.7**
(and, partly, Python 3.3). Bytecode changes in every Python release, so:

| Python version | Result (real tests I ran) |
|---|---|
| **2.7** (recommended) | All **98 original tests pass** + all **32 new tests pass** = 130/130 |
| 3.4.5 | 32 new tests pass; 36 of 101 original tests pass (class-building is broken in the *original* code – not caused by our changes) |
| 3.12 | The VM cannot run at all (`unknown bytecode type: RESUME`) – new opcodes did not exist in 2019 |

**Practical solution: run the project on Python 2.7.** Options:

* **Windows/Mac:** install Python 2.7.18 from python.org/downloads/release/python-2718/ (includes Tkinter and pip).
  Then: `py -2.7 -m pip install six` (or `python -m pip install six`).
* **Anaconda/Miniconda (any OS):**
  `conda create -n pvm -c conda-forge python=2.7 six` then `conda activate pvm`
* **Linux:** `micromamba`/`conda` as above (many distributions no longer ship Python 2).

Check with `python --version` → must say `Python 2.7.x`.
(The new code is also written to be Python-3 compatible, so it is ready if the VM core is ever ported.)

## 2. How to run

Open a terminal **in this folder** (the one that contains `byterun/` and `examples/`).

```bash
# Run a program on the VM (original behaviour, unchanged)
python -m byterun examples/03_factorial.py

# NEW options (put them BEFORE the program name)
python -m byterun --stats examples/03_factorial.py     # execution summary report
python -m byterun --trace examples/02_loop_sum.py      # instruction-by-instruction trace
python -m byterun --limit 1000 examples/06_infinite_loop.py   # stop infinite loops
python -m byterun examples/05_error_demo.py            # (original) raw traceback
python -m byterun --stats examples/05_error_demo.py    # friendly error report + summary

# NEW: graphical window
python run_gui.py
# or
python -m byterun --gui examples/03_factorial.py
```

## 3. Run the tests

```bash
python -m unittest tests.test_basic tests.test_exceptions tests.test_functions tests.test_with tests.test_extensions
```
Expected: `Ran 130 tests ... OK`.
(Do **not** use `unittest discover -s tests`: the original test helper treats the `-s` flag as "don't capture output".)
Saved result: `docs/test_results_py27.txt`.

## 4. What is new (summary)

| # | Feature | Where |
|---|---|---|
| 1 | Instruction counter + per-opcode statistics | `pyvm2.py` |
| 2 | Execution trace (instruction, offset, depth, stack) | `pyvm2.py`, `--trace` |
| 3 | Stack inspection & visualisation (text drawing) | `pyvm2.py`, `report.py`, GUI |
| 4 | Execution summary report (counts, depth, time, speed, top-5 opcodes) | `report.py`, `--stats` |
| 5 | Better error handling (syntax / runtime / missing file / bad input, error location + call stack) | `runner.py`, `pyvm2.py`, `report.py` |
| 6 | Infinite-loop protection (instruction limit) | `pyvm2.py`, `--limit` |
| 7 | Reset functionality | `VirtualMachine.reset()`, GUI Reset button |
| 8 | Tkinter GUI: load, Run, Step, stack, output, trace, statistics, errors | `gui.py`, `run_gui.py` |

## 5. Project layout

```
byterun/
  __main__.py   ORIGINAL (modified: new command-line options)
  pyvm2.py      ORIGINAL (modified: hooks + new methods, all marked [NEW])
  pyobj.py      ORIGINAL (not changed)
  execfile.py   ORIGINAL (not changed)
  runner.py     NEW  – safe "compile and run" helper
  report.py     NEW  – text formatting (stack drawing, summary, errors)
  gui.py        NEW  – Tkinter window
examples/       NEW  – 7 sample programs
tests/
  test_basic.py, test_exceptions.py, test_functions.py, test_with.py, vmtest.py   ORIGINAL
  test_extensions.py   NEW – 32 tests for the new features
docs/           NEW  – report, viva, code explanation, screenshots, test results, diff
run_gui.py      NEW
```
Every line added to an original file is tagged `[NEW]`. The exact differences are in
`docs/CHANGES_to_original_files.diff` (produced with `git diff` against the original commit).

## 6. Documents
* `docs/PROJECT_REPORT.docx` (also `.md`) – full project report
* `docs/CODE_EXPLANATION.md` – every new function explained
* `docs/VIVA_PREPARATION.docx` (also `.md`) – concepts + 27 viva questions
* `docs/screenshots/` – real screenshots of the GUI

## 7. Licence
The original code is © 2013 Ned Batchelder, MIT licence (see `LICENSE`).
Keep the licence file and credit the original author in your submission.
