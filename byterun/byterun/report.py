"""[NEW FILE] Functions that turn VM data into readable text.

Everything here only *formats* information; nothing here runs bytecode.
"""

from __future__ import print_function, division


def format_stack(stack_items, width=34):
    """Draw a value stack as a small text picture.

    Input : stack_items - list of strings, BOTTOM of the stack first.
    Output: a multi-line string, TOP of the stack shown first.

    Example output:
        +----------------------------------+
        | TOP  2: 'hello'                  |
        |      1: 42                       |
        | BOT  0: 7                        |
        +----------------------------------+
    """
    border = "+" + "-" * (width + 8) + "+"
    if not stack_items:
        return "\n".join([border, "| " + "(stack is empty)".ljust(width + 6) + " |", border])
    lines = [border]
    last = len(stack_items) - 1
    for index in range(last, -1, -1):          # walk from top to bottom
        if index == last:
            label = "TOP "
        elif index == 0:
            label = "BOT "
        else:
            label = "    "
        text = "%s %d: %s" % (label, index, stack_items[index])
        lines.append("| " + text[:width + 6].ljust(width + 6) + " |")
    lines.append(border)
    return "\n".join(lines)


def format_statistics(stats):
    """Turn the dictionary from vm.get_statistics() into a report string."""
    lines = []
    lines.append("=" * 44)
    lines.append("        EXECUTION SUMMARY REPORT")
    lines.append("=" * 44)
    lines.append("Instructions executed : %d" % stats["instructions"])
    lines.append("Different opcodes used: %d" % stats["unique_opcodes"])
    lines.append("Frames (calls) created: %d" % stats["frames_created"])
    lines.append("Max call depth        : %d" % stats["max_call_depth"])
    lines.append("Max stack depth       : %d" % stats["max_stack_depth"])
    if stats["elapsed_seconds"] is None:
        lines.append("Execution time        : (not available)")
    else:
        lines.append("Execution time        : %.6f seconds" % stats["elapsed_seconds"])
        if stats["elapsed_seconds"] > 0:
            speed = stats["instructions"] / stats["elapsed_seconds"]
            lines.append("Speed                 : %d instructions/second" % speed)
    lines.append("-" * 44)
    lines.append("Top 5 most used opcodes:")
    if not stats["most_common"]:
        lines.append("   (none)")
    for name, count in stats["most_common"]:
        percent = 100.0 * count / stats["instructions"]
        lines.append("   %-22s %6d  (%.1f%%)" % (name, count, percent))
    lines.append("=" * 44)
    return "\n".join(lines)


def format_error(error_info, error_text=None):
    """Build a friendly error message.

    Input : error_info - dictionary from vm.error_info (may be None)
            error_text - fallback text if the VM has no details
    Output: a multi-line string.
    """
    if error_info is None:
        return error_text or "(no error)"
    lines = []
    lines.append("RUNTIME ERROR: %s: %s" % (error_info["type"], error_info["message"]))
    lines.append("  Where      : function '%s', line %s of %s" % (
        error_info["function"], error_info["line"], error_info["filename"]))
    lines.append("  Instruction: %s" % error_info["opcode"])
    lines.append("  Stack then : [%s]" % ", ".join(error_info["stack"]))
    lines.append("  Call stack (oldest first):")
    for name, line in error_info["call_stack"]:
        lines.append("      %s  (line %s)" % (name, line))
    return "\n".join(lines)
