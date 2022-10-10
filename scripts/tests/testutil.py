#!/usr/bin/env python3

"""
Test helpers
"""

import glob
import logging
import os
import sys

logger = logging.getLogger(__name__)

def provide_module(modname, hint=os.pardir):
  "Modify sys.path to allow for importing the named module"
  for path in (os.curdir, hint):
    if glob.glob(os.path.join(path, f"{modname}.*")):
      sys.path.append(path)
      return True
  logger.error("Failed to find module %r (hint=%r)", modname, hint)
  return False

def stringify_call(func, args, kwargs):
  "Stringify the function call for logging"
  fname = func.__name__
  fargs = []
  fargs.extend(f"{arg!r}" for arg in args)
  fargs.extend(f"{aname}={arg!r}" for aname, arg in kwargs.items())
  return f"{fname}({', '.join(fargs)})"

def assert_raises(func, *args, exc_class=Exception, **kwargs):
  "Assert the function raises the given exception when called"
  callstr = stringify_call(func, args, kwargs)
  try:
    logger.debug("Calling %s, expecting %s...", callstr, exc_class)
    func(*args, **kwargs)
    assert False, f"{callstr} did not raise as expected"
  except Exception as e:
    logger.debug("Received %r", e)
    if not isinstance(e, exc_class):
      assert False, f"{callstr} raised {type(e)}, not {exc_class}"

def dump_region(root, to=sys.stderr, msg=None, with_opath=False):
  "Dump a region tree"
  if msg:
    to.write(msg)
  for cnames, cnode in root:
    cpath = ".".join(cnames)
    cstart = cnode.start
    cend = cnode.end
    to.write(f"{cpath} [{cstart} -- {cend}]")
    to.write(os.linesep)
  if with_opath:
    opath = root.get_open_path()
    cpath = ".".join(cnode.name for cnode in opath)
    to.write(f"{root} open path: {cpath}")
    to.write(os.linesep)


# vim: set ts=2 sts=2 sw=2:
