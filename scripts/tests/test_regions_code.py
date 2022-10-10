#!/usr/bin/env python3

"""
Test suite for Regions: this time with code
"""

import logging
import os

# pylint: disable=import-error
from regions import RegionNode, RegionSlice
# pylint: enable=import-error
from testutil import dump_region

logger = logging.getLogger(__name__)

NAMES = ["root", "foo", "bar"]
CODE = f"""
prefix
{NAMES[1]} {{
  1
  2
  {NAMES[2]} {{
    3
    4
    5
  }}
  6
  7
}}
postfix
"""
REGIONS = [
  (NAMES[0], len(CODE.splitlines())),
  (NAMES[1], len([l for l in CODE.splitlines() if l.startswith("  ")])+2),
  (NAMES[2], len([l for l in CODE.splitlines() if l.startswith("    ")])+2)
]

def test_code():
  "Test with simple code"
  assert len(NAMES) == len(REGIONS)
  root = RegionNode("root", 0, invariant_assert=True, data=NAMES[0])
  lines = CODE.splitlines()
  for lnr, line in enumerate(lines):
    if line.endswith("{"):
      logger.debug("Region begins at line %d", lnr)
      rname = line.strip(" {")
      root.last_open().push_region(rname, lnr)
    elif line.endswith("}"):
      logger.debug("Region ends at line %d", lnr)
      root.end_region(lnr)
  root.end_region(len(lines) - 1)

  assert not root.open

  rnodes = list(root)
  assert len(rnodes) == len(NAMES)
  for rdef, rref in zip(rnodes, REGIONS):
    rpath, rnode = rdef
    name, rlen = rref
    logger.debug("Verifying %r has name %r length %d",
        ".".join(rpath), name, rlen)
    assert rnode.name == name
    assert rpath[-1] == name
    assert len(RegionSlice(lines, rnode.start, rnode.end+1)) == rlen

  rslice = RegionSlice(lines, root.start, root.end+1)
  assert len(rslice) == len(lines)
  assert os.linesep.join(rslice) == CODE.rstrip(os.linesep)

  dump_region(root, msg="after all tests\n")

# vim: set ts=2 sts=2 sw=2:
