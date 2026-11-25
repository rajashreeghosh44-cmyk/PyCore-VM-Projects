"""A main program for Byterun."""

import argparse
import logging
import os
import sys

from . import execfile

parser = argparse.ArgumentParser(
    prog="byterun",
    description="Run Python programs with a Python bytecode interpreter.",
)
parser.add_argument(
    '-m', dest='module', action='store_true',
    help="prog is a module name, not a file name.",
)
parser.add_argument(
    '-v', '--verbose', dest='verbose', action='store_true',
    help="trace the execution of the bytecode.",
)
# [NEW] Extra command line options added for the college project.
parser.add_argument(
    '-t', '--trace', dest='trace', action='store_true',
    help="[NEW] print one trace line per executed instruction (with the stack).",
)
parser.add_argument(
    '-s', '--stats', dest='stats', action='store_true',
    help="[NEW] print an execution summary report after the program ends.",
)
parser.add_argument(
    '-l', '--limit', dest='limit', type=int, default=None, metavar='N',
    help="[NEW] stop the program after N instructions (stops infinite loops).",
)
parser.add_argument(
    '-g', '--gui', dest='gui', action='store_true',
    help="[NEW] open the Tkinter window instead of running from the command line.",
)
parser.add_argument(
    'prog', nargs='?',      # [NEW] nargs='?' so that --gui needs no program name
    help="The program to run.",
)
parser.add_argument(
    'args', nargs=argparse.REMAINDER,
    help="Arguments to pass to the program.",
)
args = parser.parse_args()

# [NEW] --gui: open the window and stop here.
if args.gui:
    from . import gui
    gui.main(args.prog)
    sys.exit(0)

if args.prog is None:
    parser.error("the following arguments are required: prog")

# [NEW] Friendly message instead of a long traceback for a missing file.
if not args.module and not os.path.isfile(args.prog):
    sys.stderr.write("FILE ERROR: cannot find the file '%s'\n" % args.prog)
    sys.exit(2)

# [NEW] If any new option was used, run through the new runner so that we can
# show the trace / statistics and handle errors nicely.
if args.trace or args.stats or args.limit is not None:
    from . import runner, report
    result = runner.run_file(
        args.prog, trace=args.trace, max_instructions=args.limit,
        trace_stream=sys.stdout if args.trace else None,
        output_stream=sys.stdout if args.trace else None,
    )
    if not args.trace:
        sys.stdout.write(result.output)
    if result.error:
        sys.stdout.write(result.error + "\n")
    if args.stats and result.statistics:
        print(report.format_statistics(result.statistics))
    sys.exit(0 if result.ok else 1)

if args.module:
    run_fn = execfile.run_python_module
else:
    run_fn = execfile.run_python_file

level = logging.DEBUG if args.verbose else logging.WARNING
logging.basicConfig(level=level)

argv = [args.prog] + args.args
run_fn(args.prog, argv)
