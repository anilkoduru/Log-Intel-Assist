"""
log_parser.py

Parses raw HDFS log lines into structured fields, and matches each
line's message text against HDFS_log_templates.csv to assign an EventId.

Field set (finalized in design discussion):
  timestamp, level, component_class, component_inner,
  block_id, event_id, message, raw_line

Deliberately NOT parsed as separate fields (kept only inside message/raw_line):
  pid, src_ip, dest_ip, src_port, dest_port
"""

import re
import csv
from datetime import datetime


# ---------------------------------------------------------------------------
# 1. Envelope regex
# ---------------------------------------------------------------------------
# Example line:
# 081109 203518 143 INFO dfs.DataNode$DataXceiver: Receiving block blk_-160...
#
# Groups:
#   date        -> 081109        (YYMMDD)
#   time        -> 203518        (HHMMSS)
#   pid         -> 143           (not indexed, captured only to strip it out)
#   level       -> INFO
#   comp_class  -> dfs.DataNode
#   comp_inner  -> DataXceiver   (optional — not every component has a $Inner)
#   message     -> everything after the "ComponentName: " prefix
LINE_RE = re.compile(
    r'^(?P<date>\d{6})\s+'
    r'(?P<time>\d{6})\s+'
    r'(?P<pid>\d+)\s+'
    r'(?P<level>[A-Z]+)\s+'
    r'(?P<comp_class>[\w.]+?)'
    r'(?:\$(?P<comp_inner>\w+))?'
    r':\s*'
    r'(?P<message>.*)$'
)

# Block ID appears inside the message body, e.g. blk_-1608999687919862906
BLOCK_ID_RE = re.compile(r'(blk_-?\d+)')

# HDFS_1 dataset year is not present in the raw line (only YYMMDD).
# The dataset is known to be from 2008 — set once here rather than
# guessing per line.
DATASET_YEAR_PREFIX = "20"  # 08 -> 2008


def parse_timestamp(date_str: str, time_str: str) -> str:
    """
    '081109', '203518' -> '2008-11-09T20:35:18'
    """
    full_date = DATASET_YEAR_PREFIX + date_str  # '20081109'
    dt = datetime.strptime(full_date + time_str, "%Y%m%d%H%M%S")
    return dt.isoformat()


# ---------------------------------------------------------------------------
# 2. Event template matching (against HDFS_log_templates.csv)
# ---------------------------------------------------------------------------
def load_templates(csv_path: str):
    """
    Loads HDFS_log_templates.csv and compiles each EventTemplate
    ('[*]' as wildcard) into a regex.

    Returns a list of (event_id, compiled_regex), ordered so that
    longer / more specific templates are checked before shorter,
    more generic ones (avoids e.g. E9 "Received block...of size...from"
    being shadowed by a looser pattern with fewer literal anchors).
    """
    compiled = []
    with open(csv_path, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            event_id = row['EventId']
            template = row['EventTemplate']

            # Escape everything, then turn escaped '\[\*\]' back into '.*?'
            pattern = re.escape(template).replace(r'\[\*\]', r'.*?')
            regex = re.compile(pattern, re.DOTALL)
            compiled.append((event_id, template, regex))

    # Sort by literal-character length of the template (descending) as a
    # simple specificity heuristic: templates with more fixed text are
    # less likely to accidentally match a shorter, unrelated message.
    compiled.sort(key=lambda t: len(t[1]), reverse=True)

    # Drop the template text now that sorting is done; keep (id, regex)
    return [(eid, rgx) for eid, _tmpl, rgx in compiled]


def match_event_id(message: str, templates) -> str | None:
    """
    Returns the first matching EventId for a given message, or None
    if nothing matched (worth logging/counting these during testing —
    a high 'no match' rate means the regex or template list needs work).
    """
    for event_id, regex in templates:
        if regex.search(message):
            return event_id
    return None


# ---------------------------------------------------------------------------
# 3. Full line -> structured dict
# ---------------------------------------------------------------------------
def parse_line(raw_line: str, templates) -> dict | None:
    """
    Parses one raw HDFS log line into the finalized ES document shape.
    Returns None if the line doesn't match the expected envelope format
    (worth logging these separately rather than silently dropping them).
    """
    m = LINE_RE.match(raw_line)
    if not m:
        return None

    message = m.group('message').strip()

    block_match = BLOCK_ID_RE.search(message)
    block_id = block_match.group(1) if block_match else None

    event_id = match_event_id(message, templates)

    doc = {
        "timestamp": parse_timestamp(m.group('date'), m.group('time')),
        "level": m.group('level'),
        "component_class": m.group('comp_class'),
        "component_inner": m.group('comp_inner'),  # None if no $Inner part
        "block_id": block_id,
        "event_id": event_id,
        "message": message,
        "raw_line": raw_line,
    }
    return doc


if __name__ == '__main__':
    # Quick manual sanity check against the sample line you shared
    sample = (
        "081109 203519 143 INFO dfs.DataNode$DataXceiver: Receiving block "
        "blk_-1608999687919862906 src: /10.250.10.6:40524 dest: /10.250.10.6:50010"
    )
    templates = load_templates('HDFS_log_templates.csv')
    result = parse_line(sample, templates)
    import json
    print(json.dumps(result, indent=2))