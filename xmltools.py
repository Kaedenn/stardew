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
  return logging.getLogger(__name__)

# Special key for object attributes
OBJ_KEY_ATTRIBS = "__attrs"

def getNodeChildren(node):
  "Get all children of a node"
  cnode = node.firstChild
  while cnode is not None:
    yield cnode
    cnode = cnode.nextSibling

def getChildNode(node, tag):
  "Get the first child with the given tag"
  for cnode in getNodeChildren(node):
    if cnode.tagName == tag:
      return cnode
  getLogger().debug("Failed to find child %s of node %s", tag, node)
  return None

def getNodeText(node):
  "Get the text of a node containing only text"
  if node is None:
    getLogger().warning("Trying to get text of None")
    return None
  cnode = node.firstChild
  if cnode and cnode.nodeType == minidom.Element.TEXT_NODE:
    return cnode.nodeValue
  return None

def isPlainTextNode(node):
  "True if the node only contains text"
  return getNodeText(node) is not None

def isCoordNode(node):
  "True if the node just has two children: 'X' and 'Y'"
  cnames = [cnode.nodeName for cnode in getNodeChildren(node)]
  if set(cnames) == set(("X", "Y")):
    return True
  return False

def nodeToCoord(node):
  "Convert a coordinate node to a coordinate pair"
  if node:
    xnode = getChildNode(node, "X")
    ynode = getChildNode(node, "Y")
    if xnode and ynode:
      return getNodeText(xnode), getNodeText(ynode)
  return None, None

def dumpNodeRec(node, mapFunc=None, interpretPoints=False):
  "Interpret XML as a Python dict"
  def doMapFunc(kval, vval):
    if mapFunc is not None:
      return mapFunc(kval, vval)
    return vval

  key = node.nodeName
  results = collections.defaultdict(dict)
  if isPlainTextNode(node):
    # unfortunately, attributes in plain text nodes are ignored
    value = doMapFunc(key, getNodeText(node))
    if value is not None:
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
