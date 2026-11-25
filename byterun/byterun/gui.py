"""[NEW FILE] A simple Tkinter window for the Python Virtual Machine.

What the window can do:
  * load a program (open a file, pick an example, or type/paste code)
  * Run it at full speed, or Step through it one instruction at a time
  * show the value stack, the current instruction and the current source line
  * show the program output, the trace, the statistics and any error

How it works (simple version):
  The VM runs in a separate "worker" thread so the window never freezes.
  Before every instruction the VM calls our hook function. In step mode the
  hook stores a snapshot of the VM and then WAITS until the user presses the
  Step button. The window checks for new snapshots every 40 milliseconds.

Works with Python 2.7 (Tkinter) and Python 3 (tkinter).
Start it with:   python run_gui.py      or      python -m byterun --gui
"""

from __future__ import print_function

import glob
import os
import threading

import six

# Python 2 calls the module "Tkinter", Python 3 calls it "tkinter".
try:
    import Tkinter as tk
    import ttk
    import tkFileDialog as filedialog
except ImportError:                                  # Python 3
    import tkinter as tk
    from tkinter import ttk
    from tkinter import filedialog

from .pyvm2 import ExecutionStopped
from . import runner, report

DEFAULT_LIMIT = "100000"        # protects the window from infinite loops
POLL_MS = 40                    # how often the window checks the VM thread
FONT = ("Courier", 10)


# ----------------------------------------------------------------------
# Part 1: the controller - runs the VM in a worker thread
# ----------------------------------------------------------------------

def make_snapshot(vm, byte_name, arguments, offset):
    """Copy the VM facts we want to display into a plain dictionary.

    Input : the VM and the instruction about to run.
    Output: a dictionary of strings/numbers (safe to hand to the window).
    """
    frame = vm.frame
    arg_text = repr(arguments[0])[:60] if arguments else ""
    return {
        "opname": byte_name,
        "arg": arg_text,
        "offset": offset,
        "line": vm.line_of_instruction(frame),
        "function": frame.f_code.co_name,
        "stack": vm.stack_as_list(),
        "depth": len(vm.frames),
        "call_stack": [f.f_code.co_name for f in vm.frames],
        "count": vm.instruction_count,
    }


class ExecutionController(object):
    """Runs one program in a worker thread and supports step-by-step mode."""

    def __init__(self):
        self.thread = None
        self.clear()

    def clear(self):
        """Forget everything about the previous run."""
        self.mode = "step"              # "step" or "run"
        self.stop_requested = False
        self.waiting = False            # True while paused before an instruction
        self.release = threading.Event()
        self.snapshot = None
        self.version = 0                # grows by 1 for every new snapshot
        self.result = None              # set when the run is over
        self.finished = False
        self.vm = None
        self.output = six.StringIO()

    def is_active(self):
        """True while a program is running or paused."""
        return self.thread is not None and not self.finished

    def start(self, source, mode, trace, limit):
        """Start a new run in a worker thread."""
        self.stop()
        self.clear()
        self.mode = mode
        self.vm = runner.VirtualMachine()
        self.thread = threading.Thread(
            target=self._work, args=(source, trace, limit))
        self.thread.daemon = True
        self.thread.start()

    def _work(self, source, trace, limit):
        """Body of the worker thread."""
        result = runner.run_source(
            source, filename="<window>", vm=self.vm, trace=trace,
            max_instructions=limit, hook=self._hook,
            output_stream=self.output)
        self.result = result
        self.finished = True

    def _hook(self, vm, byte_name, arguments, offset):
        """Called by the VM before every instruction (in the worker thread)."""
        if self.stop_requested:
            raise ExecutionStopped()
        if self.mode == "step":
            self.snapshot = make_snapshot(vm, byte_name, arguments, offset)
            self.version += 1
            self.release.clear()
            self.waiting = True
            self.release.wait()          # sleep until the user presses Step
            self.waiting = False
            if self.stop_requested:
                raise ExecutionStopped()

    def step(self):
        """Let the VM execute exactly one instruction."""
        if self.waiting:
            self.release.set()

    def run_to_end(self):
        """Switch to full speed and let the VM finish."""
        self.mode = "run"
        self.release.set()

    def stop(self):
        """Stop the worker thread (if any) and wait for it to end."""
        if self.thread is not None:
            self.stop_requested = True
            self.release.set()
            self.thread.join(2.0)
            self.thread = None


# ----------------------------------------------------------------------
# Part 2: the window
# ----------------------------------------------------------------------

class PVMApp(object):
    """The main window."""

    def __init__(self, root):
        self.root = root
        self.controller = ExecutionController()
        self.shown_version = 0
        self.trace_shown = 0
        self.output_len = -1
        self.build_widgets()
        self.set_state("idle")
        root.protocol("WM_DELETE_WINDOW", self.on_close)
        root.after(POLL_MS, self.poll)

    # ---------------- building the window ----------------

    def build_widgets(self):
        root = self.root
        root.title("Python Virtual Machine - based on Byterun")
        root.geometry("1000x720")
        self.build_menu()

        # Toolbar
        bar = tk.Frame(root)
        bar.pack(side=tk.TOP, fill=tk.X, padx=6, pady=4)
        self.btn_open = tk.Button(bar, text="Open File...", command=self.open_file)
        self.btn_run = tk.Button(bar, text="Run", width=8, command=self.on_run)
        self.btn_step = tk.Button(bar, text="Step", width=8, command=self.on_step)
        self.btn_reset = tk.Button(bar, text="Reset", width=8, command=self.on_reset)
        for button in (self.btn_open, self.btn_run, self.btn_step, self.btn_reset):
            button.pack(side=tk.LEFT, padx=3)
        tk.Label(bar, text="  Max instructions:").pack(side=tk.LEFT)
        self.limit_var = tk.StringVar(value=DEFAULT_LIMIT)
        tk.Entry(bar, textvariable=self.limit_var, width=9).pack(side=tk.LEFT)
        self.trace_var = tk.IntVar(value=1)
        tk.Checkbutton(bar, text="Record trace",
                       variable=self.trace_var).pack(side=tk.LEFT, padx=10)

        # Status bar (bottom)
        self.status_var = tk.StringVar()
        tk.Label(root, textvariable=self.status_var, anchor="w", relief=tk.SUNKEN,
                 ).pack(side=tk.BOTTOM, fill=tk.X)

        # Middle: source (left) and VM state (right)
        middle = tk.PanedWindow(root, orient=tk.HORIZONTAL)
        middle.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=6)

        src_frame = tk.LabelFrame(middle, text="Program (Python source)")
        self.source_text = self.make_text(src_frame, width=48, height=18, editable=True)
        self.source_text.tag_configure("current", background="#ffe680")
        middle.add(src_frame)

        right = tk.Frame(middle)
        middle.add(right)
        inst_frame = tk.LabelFrame(right, text="Current instruction (about to execute)")
        inst_frame.pack(fill=tk.X)
        self.inst_text = tk.Text(inst_frame, height=6, width=44, font=FONT,
                                 state=tk.DISABLED)
        self.inst_text.pack(fill=tk.X)
        stack_frame = tk.LabelFrame(right, text="Value stack (top first)")
        stack_frame.pack(fill=tk.BOTH, expand=True)
        self.stack_text = self.make_text(stack_frame, width=44, height=10)

        # Bottom: tabs
        self.tabs = ttk.Notebook(root)
        self.tabs.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=6, pady=4)
        self.output_text = self.add_tab("Output")
        self.trace_text = self.add_tab("Trace")
        self.stats_text = self.add_tab("Statistics")
        self.error_text = self.add_tab("Errors")
        self.error_text.tag_configure("bad", foreground="#b00020")

    def build_menu(self):
        menubar = tk.Menu(self.root)
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="Open File...", command=self.open_file)
        examples = tk.Menu(file_menu, tearoff=0)
        folder = os.path.join(os.path.dirname(os.path.dirname(
            os.path.abspath(__file__))), "examples")
        for path in sorted(glob.glob(os.path.join(folder, "*.py"))):
            examples.add_command(
                label=os.path.basename(path),
                command=lambda p=path: self.load_path(p))
        file_menu.add_cascade(label="Load Example", menu=examples)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.on_close)
        menubar.add_cascade(label="File", menu=file_menu)
        self.root.config(menu=menubar)

    def make_text(self, parent, width, height, editable=False):
        """Create a Text box with a vertical scrollbar."""
        scroll = tk.Scrollbar(parent)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)
        text = tk.Text(parent, width=width, height=height, font=FONT,
                       yscrollcommand=scroll.set, wrap=tk.NONE,
                       state=tk.NORMAL if editable else tk.DISABLED)
        text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll.config(command=text.yview)
        return text

    def add_tab(self, title):
        frame = tk.Frame(self.tabs)
        self.tabs.add(frame, text=title)
        return self.make_text(frame, width=100, height=9)

    # ---------------- small helpers ----------------

    def set_text(self, widget, text):
        """Replace all text of a read-only Text widget."""
        widget.config(state=tk.NORMAL)
        widget.delete("1.0", tk.END)
        widget.insert(tk.END, text)
        widget.config(state=tk.DISABLED)

    def set_state(self, state, message=None):
        """Enable/disable buttons for: idle, paused, running, finished."""
        self.state = state
        editable = state in ("idle", "finished")
        self.source_text.config(state=tk.NORMAL if editable else tk.DISABLED)
        self.btn_open.config(state=tk.NORMAL if editable else tk.DISABLED)
        self.btn_step.config(state=tk.DISABLED if state == "running" else tk.NORMAL)
        self.btn_run.config(state=tk.DISABLED if state == "running" else tk.NORMAL)
        default = {"idle": "Ready. Load a program, then press Run or Step.",
                   "paused": "Paused. Press Step for the next instruction, "
                             "or Run to finish.",
                   "running": "Running...",
                   "finished": "Finished."}
        self.status_var.set(message or default[state])

    def show_error(self, text):
        self.set_text(self.error_text, text)
        if text:
            self.tabs.select(3)          # jump to the Errors tab

    # ---------------- loading a program ----------------

    def open_file(self):
        path = filedialog.askopenfilename(
            title="Open a Python program",
            filetypes=[("Python files", "*.py"), ("All files", "*.*")])
        if path:
            self.load_path(path)

    def load_path(self, path):
        """Read a file into the source box; report problems nicely."""
        try:
            with open(path, "r") as handle:
                text = handle.read()
        except (IOError, OSError) as err:
            self.show_error("FILE ERROR: cannot read '%s' (%s)" % (path, err))
            return
        self.on_reset()
        self.source_text.config(state=tk.NORMAL)
        self.source_text.delete("1.0", tk.END)
        self.source_text.insert(tk.END, text)
        self.status_var.set("Loaded: %s" % path)

    # ---------------- button actions ----------------

    def read_limit(self):
        """Return (ok, limit). limit is None when the box is empty."""
        text = self.limit_var.get().strip()
        if text == "":
            return True, None
        try:
            value = int(text)
        except ValueError:
            value = 0
        if value <= 0:
            self.show_error("INPUT ERROR: 'Max instructions' must be a "
                            "positive whole number (or empty for no limit).")
            return False, None
        return True, value

    def begin(self, mode):
        """Start a new run in the given mode ('run' or 'step')."""
        ok, limit = self.read_limit()
        if not ok:
            return
        source = self.source_text.get("1.0", tk.END)
        if source.strip() == "":
            self.show_error("INPUT ERROR: there is no program to run. "
                            "Load a file or type some code first.")
            return
        self.clear_views()
        self.controller.start(source, mode, bool(self.trace_var.get()), limit)
        self.set_state("running" if mode == "run" else "paused",
                       "Starting..." if mode == "step" else None)

    def on_run(self):
        if self.state == "paused":
            self.controller.run_to_end()
            self.set_state("running")
        else:
            self.begin("run")

    def on_step(self):
        if self.state == "paused":
            self.controller.step()
            self.set_state("running", "Executing one instruction...")
        else:
            self.begin("step")

    def on_reset(self):
        """Stop any running program and clear every panel."""
        self.controller.stop()
        self.controller.clear()
        self.clear_views()
        self.set_state("idle")

    def on_close(self):
        self.controller.stop()
        self.root.destroy()

    def clear_views(self):
        self.shown_version = 0
        self.trace_shown = 0
        self.output_len = -1
        for widget in (self.output_text, self.trace_text, self.stats_text,
                       self.error_text, self.inst_text, self.stack_text):
            self.set_text(widget, "")
        self.source_text.tag_remove("current", "1.0", tk.END)

    # ---------------- refreshing the window ----------------

    def poll(self):
        """Runs every POLL_MS: copy new information from the VM thread."""
        c = self.controller
        try:
            if c.vm is not None:
                self.refresh_output()
                self.refresh_trace()
                self.refresh_stats()
            if c.waiting and c.version != self.shown_version:
                self.shown_version = c.version
                self.show_snapshot(c.snapshot)
                self.set_state("paused", "Paused before instruction #%d. Press "
                               "Step or Run." % (c.snapshot["count"]))
            if c.finished and self.state in ("running", "paused"):
                self.show_result(c.result)
        finally:
            self.root.after(POLL_MS, self.poll)

    def refresh_output(self):
        text = self.controller.output.getvalue()
        if len(text) != self.output_len:
            self.output_len = len(text)
            self.set_text(self.output_text, text)

    def refresh_trace(self):
        lines = self.controller.vm.trace_lines
        if len(lines) > self.trace_shown:
            new_lines = lines[self.trace_shown:]
            self.trace_shown += len(new_lines)
            self.trace_text.config(state=tk.NORMAL)
            self.trace_text.insert(tk.END, "\n".join(new_lines) + "\n")
            self.trace_text.see(tk.END)
            self.trace_text.config(state=tk.DISABLED)

    def refresh_stats(self):
        stats = self.controller.vm.get_statistics()
        if stats["instructions"]:
            self.set_text(self.stats_text, report.format_statistics(stats))

    def show_snapshot(self, snap):
        """Display the paused state of the VM."""
        self.set_text(self.inst_text,
                      "Instruction : %s %s\nOffset      : %d\n"
                      "Source line : %d\nFunction    : %s\n"
                      "Call stack  : %s\nInstruction#: %d" % (
                          snap["opname"], snap["arg"], snap["offset"],
                          snap["line"], snap["function"],
                          " > ".join(snap["call_stack"]), snap["count"]))
        self.set_text(self.stack_text, report.format_stack(snap["stack"]))
        self.highlight_line(snap["line"])

    def highlight_line(self, line):
        self.source_text.tag_remove("current", "1.0", tk.END)
        self.source_text.tag_add("current", "%d.0" % line, "%d.0 lineend" % line)
        self.source_text.see("%d.0" % line)

    def show_result(self, result):
        """Called once when the program has ended."""
        self.refresh_output()
        self.refresh_trace()
        stats = result.statistics
        if stats:
            self.set_text(self.stats_text, report.format_statistics(stats))
        if result.ok:
            self.show_error("")
            self.set_state("finished", "Finished successfully. %d instructions "
                           "executed." % stats["instructions"])
        else:
            self.show_error(result.error)
            self.set_state("finished", "Stopped: " + result.error.split("\n")[0])
        self.source_text.tag_remove("current", "1.0", tk.END)
        if result.vm is not None and result.vm.error_info is not None:
            line = result.vm.error_info["line"]
            self.highlight_line(line)               # show where the error was
        self.set_text(self.inst_text, "(program ended)")
        if result.vm is not None and result.vm.frame is not None:
            self.set_text(self.stack_text,
                          report.format_stack(result.vm.stack_as_list()))
        else:
            self.set_text(self.stack_text, report.format_stack([]))


def main(path=None):
    """Create the window and start the program. `path` is optional."""
    root = tk.Tk()
    app = PVMApp(root)
    if path:
        app.load_path(path)
    root.mainloop()


if __name__ == "__main__":
    main()
