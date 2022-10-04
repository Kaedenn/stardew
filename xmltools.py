#!/usr/bin/env python3
# pylint: disable=invalid-name

"""
Various XML helpers

This module provides numerous helper functions to assist processing
minidom XML elements.

There are a few known issues, namely the horribly non-optimal O(n)
iterations whenever we want to find a specific child node. Due to
XML being fundamentally non-unique, this would require some sort of
caching or API modification to fix. I'll address this if/when it
becomes an issue.
"""

# The naming convention used below, although clearly non-Pythonic,
# resembles the various DOM APIs and tries to be consistent with those.

import collections
import logging
import xml.dom.minidom as minidom

# Commonly-used constants
TEXT_NODE = minidom.Element.TEXT_NODE

def getLogger():
  """
  Get the logger for this module
  """
  return logging.getLogger(__name__)

# Special key for object attributes
OBJ_KEY_ATTRIBS = "__attrs"

def hasTag(node, tag, ignorecase=False):
  """
  True if the node has the given tag
  """
  if node.tagName == tag:
    return True
  if ignorecase and node.tagName.lower() == tag.lower():
    return True
  return False

def getNodeChildren(node, names_only=False):
  """
  Get all children of a node

  Returns just the tag names if names_only is True.
  """
  if node:
    for cnode in node.childNodes:
      if isTextElement(cnode):
        continue
      if names_only:
        yield cnode.tagName
      else:
        yield cnode

def nodeHasChild(node, tag, ignorecase=False):
  """
  Return True if the node has an immediate child with the given tag name
  """
  for cnode in getNodeChildren(node):
    if hasTag(cnode, tag, ignorecase=ignorecase):
      return True
  return False

def getNodeChild(node, tag, ignorecase=False):
  """
  Get the first child with the given tag
  """
  for cnode in getNodeChildren(node):
    if cnode.nodeType != minidom.Element.TEXT_NODE:
      if hasTag(cnode, tag, ignorecase=ignorecase):
        return cnode
  return None

def isTextNode(node):
  """
  True if the node only contains text
  """
  if not node:
    return False
  if not node.firstChild:
    return False
  if node.firstChild.nextSibling:
    return False
  return isTextElement(node.firstChild)

def isTextElement(node):
  """
  True if the given node _is_ text
  """
  return node.nodeType == minidom.Element.TEXT_NODE

def getNodeText(node):
  """
  Get the text of a node containing only text
  """
  if isTextNode(node):
    return node.firstChild.nodeValue
  return None

def getChildText(node, ctag, ignorecase=False, to=None, silent=True):
  """
  Get the text of the child node

  The "to" parameter enables special processing:
    The special value "bool" returns True and False for "true" and "false"
    All other values return `to(text)`

  If silent is True, then any ValueError caused by `to(text)` is ignored
  """
  if nodeHasChild(node, ctag, ignorecase=ignorecase):
    cnode = getNodeChild(node, ctag, ignorecase=ignorecase)
    if isTextNode(cnode):
      ctext = getNodeText(cnode)
      if to == "bool":
        if ctext == "true":
          return True
        if ctext == "false":
          return False
      elif to is not None:
        try:
          return to(ctext)
        except ValueError as e:
          getLogger().debug("node %s/%s text %r as %r failed: %r",
              node.tagName, ctag, ctext, to, e)
          if not silent:
            raise
      return ctext
  return None

def findChildren(node, func, first=True):
  """
  Recursively find children satisfying the function. If first is True, yield
  only the first match. Otherwise, yield all of them.
  """
  for cnode in getNodeChildren(node):
    if func(cnode):
      yield cnode
      if first:
        break
    elif not isTextNode(cnode):
      yield from findChildren(cnode, func, first=first)

def findChildrenNodes(node, tag, ignorecase=False, first=True):
  """
  Recursively find children with the given tag. If first is True, yield only
  the first match. Otherwise, yield all of them.
  """
  def matcher(cnode):
    "True if the node has the above tag"
    if cnode.nodeType != minidom.Element.TEXT_NODE:
      return hasTag(cnode, tag, ignorecase=ignorecase)
    return False

  yield from findChildren(node, matcher, first=first)

def descendFast(node, slashed_path, ignorecase=False):
  """
  Quickly get a child node based on the slashed path

  Requires the intermediate nodes be unique to avoid descending down
  the wrong path
  """
  head, tail = slashed_path, ""
  if "/" in slashed_path:
    head, tail = slashed_path.split("/", 1)
  cnode = getNodeChild(node, head)
  if cnode:
    if tail:
      return descend(cnode, tail, ignorecase=ignorecase)
    return cnode
  return None

def descend(node, slashed_path, ignorecase=False):
  """
  Like descendFast, but reliably handle inconsistent nesting
  """
  for cnode in descendAll(node, slashed_path, ignorecase=ignorecase):
    return cnode
  return None

def descendAll(node, slashed_path, ignorecase=False):
  """
  Like descend(), but return all matching nodes
  """
  head, tail = slashed_path, ""
  if "/" in slashed_path:
    head, tail = slashed_path.split("/", 1)
  cnodes = findChildrenNodes(node, head, ignorecase=ignorecase, first=False)
  for cnode in cnodes:
    if tail:
      yield from descendAll(cnode, tail, ignorecase=ignorecase)
    else:
      yield cnode

def dumpNodeRec(node, mapFunc=None, xformFunc=False):
  """Interpret XML as a Python dict

  xformFunc, if specified, will be called on the initial node. Default parsing
  happens only if this function returns None. Any other value will be treated
  as that node's final value.

  mapFunc, if specified, will be called on the resulting Python type.

  If an element has a child repeated more than once, then the child's values
  will be converted to a list.
  """
  def doMapFunc(kval, vval):
    if mapFunc is not None:
      return mapFunc(kval, vval)
    return vval

  def doMerge(dest, src):
    "Merge src and dest, returning the result"
    if isinstance(dest, list):
      return dest + [src]
    return [dest, src]

  def doMergeFunc(value, newvalue):
    "Merge newvalue into the existing value, in-place"
    shared = set(key for key in value if key in newvalue)
    for key in newvalue:
      if key in shared:
        value[key] = doMerge(value[key], newvalue[key])
      else:
        value[key] = newvalue[key]

  key = node.nodeName
  results = collections.defaultdict(dict)
  if xformFunc:
    xformValue = xformFunc(node)
    if xformValue is not None:
      return {key: xformValue}

  if isTextNode(node):
    # unfortunately, attributes in plain text nodes are ignored
    value = doMapFunc(key, getNodeText(node))
    if value == 'true':
      results[key] = True
    elif value == 'false':
      results[key] = False
    elif value is not None:
      results[key] = value
  else:
    for cnode in getNodeChildren(node):
      rawval = dumpNodeRec(cnode, mapFunc=mapFunc, xformFunc=xformFunc)
      value = doMapFunc(key, rawval)
      if value is not None:
        doMergeFunc(results[key], value)
    attribs = dict(node.attributes.items())
    if attribs:
      results[key][OBJ_KEY_ATTRIBS] = attribs
  return dict(results)

# vim: set ts=2 sts=2 sw=2:
