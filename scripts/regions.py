#!/usr/bin/env python3

"""
Library for associating source code across multiple nested scopes.

The RegionNode class is essentially an n-ary tree data structure with
added features and constraints aimed at tracking code across multiple
nested scopes without the exponential memory increase one would expect
from the naive implementation.

"""

import itertools
import logging

def get_logger():
  "Obtain the logger that this module uses"
  return logging.getLogger(__name__)

class RegionSlice:
  "Like itertools.islice, but supporting the all-important len()"
  def __init__(self, iterable, start, stop=None, step=None, lhint=None):
    self._seq = iterable
    self._slice = itertools.islice(iterable, start, stop, step)
    self._len = None
    if lhint is not None:
      self._len = lhint
    elif stop is not None and stop >= start:
      self._len = stop - start
    elif hasattr(iterable, "__len__"):
      self._len = len(iterable)

  def __iter__(self):
    "Iterate over the entries of this slice"
    yield from self._slice

  def __len__(self):
    "Get the length of the slice"
    return self._len

class RegionNode:
  """
  A single region, possibly containing children.

  Core assumptions:
  If a region node is closed, then all of its children are closed.
  If a child region is closed, then all previous child regions are closed.
  The path of open child regions is unique.
  """
  def __init__(self, name, start_line=None, data=None, invariant_assert=False):
    "See help(type(self))"
    self._name = name
    self._children = []
    self.start = start_line
    self.end = None
    self.data = data
    self._assert = invariant_assert

  def children(self):
    "Yield (str, RegionNode) pair for all children"
    for child in self._children:
      yield self._name, child

  @property
  def name(self):
    "Get the region's name"
    return self._name

  @property
  def open(self):
    "True if this region is open (lacks an ending)"
    return self.end is None

  def _postop_assert(self):
    "Assert the structure is still valid"
    if self._assert:
      self._assert_structured_open(recurse=True)

  def _push(self, *args, **kwargs):
    "Add a new child to this node"
    cnode = RegionNode(*args, **kwargs)
    self._children.append(cnode)
    return cnode

  def _end(self, end_line):
    "Mark this node as complete"
    self.end = end_line

  def get_open_child(self, with_index=False):
    "Get the child that's open, or None"
    if self.open:
      cidx = len(self._children) - 1
      while cidx > -1:
        if self._children[cidx].open:
          if with_index:
            return cidx, self._children[cidx]
          return self._children[cidx]
        cidx -= 1
    if with_index:
      return None, None
    return None

  def has_open_child(self):
    "True if this region entry has an incomplete child"
    return self.get_open_child() is not None

  def get_open_path(self):
    "Get a list of open nodes"
    opath = []
    if self.open:
      opath.append(self)
      if self._children and self._children[-1].open:
        opath.extend(self._children[-1].get_open_path())
    return opath

  def last_open(self):
    "Return the last/deepest child that's still open"
    opath = self.get_open_path()
    if opath:
      return opath[-1]
    return None

  def get_max_line(self):
    "Return the maximal line number"
    lmax = self.start
    if self.end is not None:
      lmax = self.end
    if self._children:
      cnode = self._children[-1]
      cmax = cnode.get_max_line()
      if cmax > lmax:
        lmax = cmax
    return lmax

  def push_region(self, *args, **kwargs):
    "Add a new region to the last open child"
    cnode = self.last_open()
    if not cnode:
      raise ValueError("Can't push a region on a closed node")
    new_cnode = cnode._push(*args, **kwargs) # pylint: disable=protected-access
    self._postop_assert()
    return new_cnode

  def end_region(self, end_line):
    "Close the inner-most open region"
    if not self.open:
      raise ValueError("Can't end a region; region is already closed")
    if self.start > end_line:
      raise ValueError(f"{end_line} must be greater than {self.start}")
    cnode = self.last_open()
    if cnode.start > end_line:
      raise ValueError(f"{end_line} must be greater than {cnode.start}")
    ended_cnode = cnode._end(end_line) # pylint: disable=protected-access
    self._postop_assert()
    return ended_cnode

  def _assert_unique_open(self, recurse=False):
    "Assert the open path is unique"
    ncopen = len([c for c in self._children if c.open])
    if self.open:
      assert ncopen in (0, 1), f"too many open children {ncopen}"
    else:
      assert ncopen == 0, "closed node has open children"
    if recurse:
      for child in self._children:
        # pylint: disable=protected-access
        child._assert_unique_open(recurse=True)

  def _assert_structured_open(self, recurse=False):
    "Assert the open path doesn't contradict itself"
    self._assert_unique_open(recurse=recurse)
    iopen, copen = self.get_open_child(with_index=True)
    if iopen is not None and copen is not None:
      cprior = [(i, c) for i, c in enumerate(self._children) if i < iopen]
      cnext = [(i, c) for i, c in enumerate(self._children) if i > iopen]
      assert not any(cn.open for ci, cn in cprior), \
          f"open node {iopen} follows open nodes {cprior}"
      assert not any(cn.open for ci, cn in cnext), \
          f"open node {iopen} proceeds open nodes {cnext}"
    else:
      assert all(not cnode.open for cnode in self._children), \
          "closed node with open children"

  def iterate_recurse(self, start_path=None, maxdepth=None):
    "Recursively iterate over the region, depth-first"
    if maxdepth is None or maxdepth > 0:
      newdepth = maxdepth-1 if maxdepth is not None else None
      path = list(start_path) if start_path is not None else []
      path.append(self.name)
      yield path, self
      for cnode in self._children:
        yield from cnode.iterate_recurse(path, newdepth)

  def __iter__(self):
    "Traverse the tree"
    yield from self.iterate_recurse()

  def __len__(self):
    "Total size of the tree"
    length = 0
    for _ in self:
      length += 1
    return length

  def __repr__(self):
    "Like __str__, but more"
    nrch = f"{len(self._children)}" if self._children else ""
    name, start, end = self.name, self.start, self.end
    return f"RegionNode[{nrch}]({name!r}, {start}, {end})"

# vim: set ts=2 sts=2 sw=2:
