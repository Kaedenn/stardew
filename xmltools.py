#!/usr/bin/env python3
# pylint: disable=invalid-name

"""
Various XML helpers
"""

import collections
import logging
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

def getChildText(node, ctag, ignorecase=False):
  "Get the text of the child node"
  if nodeHasChild(node, ctag, ignorecase=ignorecase):
    cnode = getNodeChild(node, ctag, ignorecase=ignorecase)
    if isTextNode(cnode):
      return getNodeText(cnode)
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

def walk(root, visitor=None):
  """Preorder descent over the entire tree

  Descent happens if the visitor function returns True or, if visitor is None,
  xmltools.isTextNode(node) is False.
  """
  if visitor:
    visit_func = visitor
  else:
    def visit_func(node):
      "Default visitor function if none is given"
      if isTextNode(node):
        return False
      return True

  for cnode in getNodeChildren(root):
    yield cnode
    if visit_func(cnode):
      yield from walk(cnode, visitor=visit_func)

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

def dumpNodeRec(node, mapFunc=None, xformFunc=False):
  """Interpret XML as a Python dict

  xformFunc, if specified, will be called on the initial node. Default parsing
  happens only if this function returns None. Any other value will be treated
  as that node's final value.

  mapFunc, if specified, will be called on the resulting Python type.
  """
  def doMapFunc(kval, vval):
    if mapFunc is not None:
      return mapFunc(kval, vval)
    return vval

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
        results[key].update(value)
    attribs = dict(node.attributes.items())
    if attribs:
      results[key][OBJ_KEY_ATTRIBS] = attribs
  return dict(results)

# vim: set ts=2 sts=2 sw=2:
