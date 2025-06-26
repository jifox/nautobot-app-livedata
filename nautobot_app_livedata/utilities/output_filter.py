"""
Output filtering utilities for Nautobot App Livedata.

Provides functions to apply post-processing filters to device command output, such as EXACT, LAST, and FIRST filters.
"""

import re


def apply_output_filter(output: str, filter_instruction: str) -> str:
    """
    Apply one or more filters to the output string based on the filter_instruction.
    Multiple filters can be chained using '!!' as a separator, e.g. 'EXACT:foo!!LAST:10!!'.
    Supported filters:
      - EXACT:<pattern>: Only lines that contain <pattern> as a whole word (ignoring leading/trailing whitespace)
      - LAST:<N>: Only the last N lines
      - FIRST:<N>: Only the first N lines
    """
    if not filter_instruction:
        return output
    # Split by '!!' and filter out empty segments
    filters = [f for f in filter_instruction.split("!!") if f.strip()]
    for filt in filters:
        if filt.startswith("EXACT:"):
            pattern = filt[len("EXACT:") :].strip()
            regex = re.compile(rf"(^|\S*){re.escape(pattern)}(\D|$)")
            output = "\n".join(line for line in output.splitlines() if regex.search(line.strip()))
        elif filt.startswith("LAST:"):
            n_str = filt[len("LAST:") :]
            try:
                n = int(n_str)
            except ValueError:
                continue  # skip invalid LAST filter
            output = "\n".join(output.splitlines()[-n:])
        elif filt.startswith("FIRST:"):
            n_str = filt[len("FIRST:") :]
            try:
                n = int(n_str)
            except ValueError:
                continue  # skip invalid FIRST filter
            output = "\n".join(output.splitlines()[:n])
        else:
            # Unknown filter, skip
            continue
    return output
