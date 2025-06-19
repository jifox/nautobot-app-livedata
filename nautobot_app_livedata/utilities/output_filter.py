"""
Output filtering utilities for Nautobot App Livedata.

Provides functions to apply post-processing filters to device command output, such as EXACT and LAST filters.
"""

import re


def apply_output_filter(output: str, filter_instruction: str) -> str:
    """
    Apply a filter to the output string based on the filter_instruction.
    Supported filters:
      - EXACT:<pattern>: Only lines that contain <pattern> as a whole word (ignoring leading/trailing whitespace)
      - LAST:<N>: Only the last N lines
    """
    if not filter_instruction:
        return output
    if filter_instruction.startswith("EXACT:"):
        pattern = filter_instruction[len("EXACT:") :].strip()
        # Match pattern as a whole word, ignoring leading/trailing whitespace
        regex = re.compile(rf"(^|\s){re.escape(pattern)}(\s|$)")
        return "\n".join(line for line in output.splitlines() if regex.search(line.strip()))
    if filter_instruction.startswith("LAST:"):
        try:
            n = int(filter_instruction[len("LAST:") :])
            return "\n".join(output.splitlines()[-n:])
        except Exception:
            return output
    # Unknown filter, return output unchanged
    return output
