#!/usr/bin/env python3

"""
Process a monolithic decompiled C# assembly into manageable pieces.
"""

import argparse
import logging
import os
import re

# pylint: disable=import-error
import regions
from regions import RegionSlice, RegionNode
# pylint: enable=import-error

logging.basicConfig(format="%(module)s:%(lineno)s: %(levelname)s: %(message)s",
                    level=logging.INFO)
logger = logging.getLogger(__name__)

P_TAB = "^[\t]*"
P_ICHR = "[A-Za-z_][A-Z-a-z0-9_]"
P_NAME = P_ICHR + "+"
P_DOTTED_NAME = rf"{P_NAME}(?:\.{P_NAME})*"
P_TEMPLATE = rf"{P_DOTTED_NAME}(?:<{P_DOTTED_NAME}>)"
P_VIS = r"(?P<visibility>public|private|protected)?"
P_TYPE_ATTR = r"[ ]*(?P<typeattr>abstract|static)?"
P_INHERIT = r"(?: : (?P<ancestors>.*))?"
P_DECL_PRE = P_VIS + P_TYPE_ATTR
PAT_NAMESPACE = re.compile(rf"{P_TAB}(?P<kind>namespace) (?P<name>{P_DOTTED_NAME})$")
PAT_CLASS = re.compile(f"{P_TAB}{P_DECL_PRE} (?P<kind>class) (?P<name>{P_NAME}){P_INHERIT}")
PAT_ENUM = re.compile(f"{P_TAB}{P_DECL_PRE} (?P<kind>enum) (?P<name>{P_NAME})")
PAT_INTERFACE = re.compile(f"{P_TAB}{P_DECL_PRE} (?P<kind>interface) (?P<name>{P_NAME}){P_INHERIT}")

def check_indent(line):
  "Count the number of indentations for this line"
  return len(line) - len(line.lstrip("\t"))

def check_batch_begin(line, line_nr, lead_indent):
  "Determine if the line opens a new batch"
  indent = check_indent(line)
  mpats = [PAT_NAMESPACE, PAT_CLASS, PAT_INTERFACE, PAT_ENUM]
  for matpat in mpats:
    mat_obj = matpat.match(line)
    if mat_obj is not None:
      logger.debug("Line %d opens a batch at indent %d", line_nr, lead_indent)
      mkind = mat_obj.group("kind")
      mname = mat_obj.group("name")
      return mkind, mname
  return None, None

def is_batch_end(line, line_nr, lead_indent):
  "True if the line ends a batch"
  if check_indent(line) == lead_indent:
    if line.lstrip("\t").rstrip("\r\n") == "}":
      return True
  return False

def split_batches(fobj):
  "Iteratively split a file object into batches"
  broot = RegionNode("", 0, data="root")
  bindents = []
  lines = fobj.read().splitlines() # required for regions implementation logic
  for lnr, line in enumerate(lines):
    indent = bindents[-1] if bindents else 0
    bkind, bpath = check_batch_begin(line, lnr, indent)
    if bpath is not None:
      logger.debug("%s %s begins at %d", bkind, bpath, lnr)
      broot.last_open().push_region(bpath, lnr, data=bkind)
      bindents.append(check_indent(line))
    elif is_batch_end(line, lnr, indent):
      broot.end_region(lnr)
      bindents.pop()
  lastline = len(lines) - 1
  broot.end_region(lastline)
  if broot.open:
    logger.warning("Root region still open")

  logger.debug("Parsed %d batches", len(broot))
  for bpath, bnode in broot:
    bkind = bnode.data
    if bkind != "root":
      yield bpath[1:], RegionSlice(lines, bnode.start, bnode.end+1)

def write_batch(bpath, blines, opath, as_dirs=False):
  "Write a single batch to a file"
  fpath = opath
  fname = ".".join(bpath) + ".cs"
  if as_dirs:
    fpath = os.path.join(opath, *bpath[:-1])
    fname = bpath[-1] + ".cs"
    if not os.path.exists(fpath):
      os.makedirs(fpath)
  logger.debug("Writing %d lines to %s/%s", len(blines), fpath, fname)
  with open(os.path.join(fpath, fname), "wt") as fobj:
    for line in blines:
      fobj.write(line)
      fobj.write(os.linesep)

def main(): # pylint: disable=missing-function-docstring
  ap = argparse.ArgumentParser()
  ap.add_argument("path", help="path to monolithic disassembly text file")
  ap.add_argument("--classes", action="store_true",
      help="dump only classes; skip namespaces")
  ap.add_argument("--prune", metavar="NUM", type=int, default=0,
      help="strip the first %(metavar)s names")
  ap.add_argument("-O", "--opath", metavar="PATH", default=os.curdir,
      help="output batches to %(metavar)s (default %(default)s)")
  ap.add_argument("--bpath-as-dirs", action="store_true",
      help="create Foo/Bar/Baz.cs instead of Foo.Bar.Baz.cs")
  ap.add_argument("-v", "--verbose", action="store_true",
      help="enable verbose output")
  args = ap.parse_args()
  if args.verbose:
    logger.setLevel(logging.DEBUG)
    regions.get_logger().setLevel(logging.DEBUG)

  with open(args.path, "rt") as fobj:
    for batch_path, batch_lines in split_batches(fobj):
      logger.debug("Batch %r: %d lines", batch_path, len(batch_lines))
      bpath = ".".join(batch_path[args.prune:]).split(".")
      if not bpath:
        logger.warning("Pruned %r to emptiness!", batch_path)
        bpath = batch_path
      write_batch(bpath, batch_lines, args.opath, as_dirs=args.bpath_as_dirs)

if __name__ == "__main__":
  main()

# vim: set ts=2 sts=2 sw=2:
