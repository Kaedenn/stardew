#!/usr/bin/env python3

"""
Various XML helpers
"""

import collections
import logging
import os
import sys
import xml.dom.minidom as minidom

def getLogger():
  "Get the logger for this module"
  return logging.getLogger(__name__)

# Special key for object attributes
OBJ_KEY_ATTRIBS = "__attrs"

def hasTag(node, tag, ignorecase=False):
  "True if the node has the given tag"
  if node.tagName == tag:
    return True
  if ignorecase and node.tagName.lower() == tag.lower():
    return True
  return False

def getNodeChildren(node, names_only=False):
  "Get all children of a node"
  cnode = node.firstChild
  while cnode is not None:
    if names_only:
      yield cnode.tagName
    else:
      yield cnode
    cnode = cnode.nextSibling

def nodeHasChild(node, tag, ignorecase=False):
  "Return True if the node has an immediate child with the given tag name"
  for cnode in getNodeChildren(node):
    if hasTag(cnode, tag, ignorecase=ignorecase):
      return True
  return False

def getNodeChild(node, tag, ignorecase=False):
  "Get the first child with the given tag"
  for cnode in getNodeChildren(node):
    if cnode.nodeType == minidom.Element.TEXT_NODE:
      continue
    if hasTag(cnode, tag, ignorecase=ignorecase):
      return cnode
  getLogger().debug("Failed to find child %s of node %s", tag, node)
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

  yield from findChildren(node, matcher, first=first)

def descend(node, slashed_path, ignorecase=False):
  "Quickly get a child node based on the slashed path"
  head, tail = slashed_path, ""
  if "/" in slashed_path:
    head, tail = slashed_path.split("/", 1)
  cnode = getNodeChild(node, head)
  if cnode:
    if tail:
      return descend(cnode, tail, ignorecase=ignorecase)
    return cnode
  return None

def descendAll(node, slashed_path, ignorecase=False):
  "Like descend(), but return all matching nodes at all levels"
  head, tail = slashed_path, ""
  if "/" in slashed_path:
    head, tail = slashed_path.split("/", 1)
  cnodes = findChildrenNodes(node, head, ignorecase=ignorecase, first=False)
  for cnode in cnodes:
    if tail:
      yield from descendAll(cnode, tail, ignorecase=ignorecase)
    else:
      yield cnode

def getNodeText(node):
  "Get the text of a node containing only text"
  cnode = node.firstChild
  if cnode and cnode.nodeType == minidom.Element.TEXT_NODE:
    return cnode.nodeValue
  return None

def isTextNode(node):
  "True if the node only contains text"
  if not node:
    return False
  if not node.firstChild:
    return False
  if node.firstChild.nextSibling:
    return False
  if node.firstChild.nodeType != minidom.Element.TEXT_NODE:
    return False
  return True

def isCoordNode(node): # XXX: move to savefile.py
  "True if the node just has two children: 'X' and 'Y'"
  cnames = [cnode.nodeName for cnode in getNodeChildren(node)]
  if set(cnames) == set(("X", "Y")):
    return True
  return False

def nodeToCoord(node): # XXX: move to savefile.py
  "Convert a coordinate node to a coordinate pair"
  if node:
    xnode = getNodeChild(node, "X")
    ynode = getNodeChild(node, "Y")
    if xnode and ynode:
      return getNodeText(xnode), getNodeText(ynode)
  return None, None

def dumpNodeRec(node, mapFunc=None, interpretPoints=False):
  """Interpret XML as a Python dict

  mapFunc, if specified, will be called on the resulting Python type.
  """
  def doMapFunc(kval, vval):
    if mapFunc is not None:
      return mapFunc(kval, vval)
    return vval

  key = node.nodeName
  results = collections.defaultdict(dict)
  if isTextNode(node):
    # unfortunately, attributes in plain text nodes are ignored
    value = doMapFunc(key, getNodeText(node))
    if value == 'true':
      results[key] = True
    elif value == 'false':
      results[key] = False
    elif value is not None:
      results[key] = value
  elif isCoordNode(node) and interpretPoints:
    results[key] = doMapFunc(key, nodeToCoord(node))
  else:
    for cnode in getNodeChildren(node):
      rawval = dumpNodeRec(cnode, mapFunc=mapFunc, interpretPoints=interpretPoints)
      value = doMapFunc(key, rawval)
      if value is not None:
        results[key].update(value)
    attribs = dict(node.attributes.items())
    if attribs:
      results[key][OBJ_KEY_ATTRIBS] = attribs
  return dict(results)

# vim: set ts=2 sts=2 sw=2:
