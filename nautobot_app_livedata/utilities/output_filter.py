"""Utility helpers for post-processing command output in Nautobot App Livedata."""

import re
from typing import Callable

from netutils.constants import BASE_INTERFACES
from netutils.interface import split_interface

BOUNDARY_CHAR_CLASS = r"A-Za-z0-9_/"
KNOWN_INTERFACE_PREFIXES = frozenset(BASE_INTERFACES)
# Matches an optional interface-type prefix followed by a dotted/slashed number
# (e.g. "GigabitEthernet4/0/36"), so EXACT filters can match full interface names
# embedded in larger lines such as syslog output.
INTERFACE_MENTION_RE = re.compile(r"(?P<type>[A-Za-z][A-Za-z-]*)?(?P<number>\d+(?:[./]\d+)+)(?![A-Za-z0-9_])")


def _exact_match_predicate(pattern: str) -> Callable[[str], bool]:
    """Build a predicate that returns ``True`` when ``pattern`` is matched as a standalone token."""

    boundary_regex = re.compile(rf"(?<![{BOUNDARY_CHAR_CLASS}]){re.escape(pattern)}(?![{BOUNDARY_CHAR_CLASS}])")

    def predicate(line: str) -> bool:
        stripped_line = line.strip()
        if boundary_regex.search(line):
            return True
        try:
            interface_type, interface_number = split_interface(stripped_line)
        except ValueError:
            interface_type, interface_number = None, None
        if interface_type in KNOWN_INTERFACE_PREFIXES and interface_number == pattern:
            return True
        # Match interface mentions embedded in larger lines (e.g. log output), such
        # as "Interface GigabitEthernet4/0/36, changed state to up" with pattern "4/0/36".
        for match in INTERFACE_MENTION_RE.finditer(line):
            mentioned_type = match.group("type") or ""
            mentioned_number = match.group("number")
            if mentioned_number == pattern and (not mentioned_type or mentioned_type in KNOWN_INTERFACE_PREFIXES):
                return True
        return False

    return predicate


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
            predicate = _exact_match_predicate(pattern)
            output = "\n".join(line for line in output.splitlines() if predicate(line))
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
