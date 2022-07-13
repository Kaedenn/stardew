#!/usr/bin/env python3

"""
Tools for examining the Stardew Valley save files
"""

import argparse
import collections
import json
import logging
import os
import sys
import xml.dom.minidom as minidom

import xmltools
from stardew import LOCATIONS, LOCATION_UNKNOWN, FORAGE

SVPATH = os.path.expanduser("~/.config/StardewValley/Saves")
VALID_FILTERS = ("false", "zero", "points")
VALID_CATEGORIES = ("forage",)

logging.basicConfig(format="%(module)s:%(lineno)s: %(levelname)s: %(message)s",
                    level=logging.INFO)
logger = logging.getLogger(__name__)

def isdigit(value):
  "True if value is a number"
  if not value.isdigit():
    if value.startswith("-") and value[1:].isdigit():
      return True
    return False
  return True

def loadSave(svdir):
  "Load a save file by name, directory path, or file path"
  if os.path.isabs(svdir):
    path = svdir
    svname = os.path.basename(svdir)
  else:
    path = os.path.join(SVPATH, svdir)
    svname = svdir
  logger.debug("Save dir: %s name %s", path, svname)
  fpath = path
  if os.path.isdir(path):
    fpath = os.path.join(path, svname)
  return minidom.parse(open(fpath, "rt"))

def isNilObject(obj):
  "True if the object is just xsi:nil"
  if not obj.firstChild:
    if obj.attributes:
      if dict(obj.attributes.items()).get("xsi:nil") == "true":
        return True
  return False

def getObjects(svfile):
  "Get objects, optionally limited to those of a given name"
  for gloc in svfile.getElementsByTagName("GameLocation"):
    mapname = gloc.getAttribute("xsi:type")
    if not mapname:
      mapname = LOCATION_UNKNOWN
    if mapname not in LOCATIONS:
      logger.warning("Unknown game location %s", mapname)
    for obj in gloc.getElementsByTagName("Object"):
      if not isNilObject(obj):
        oname = getObjName(obj)
        objpos = xmltools.nodeToCoord(xmltools.getChildNode(obj, "tileLocation"))
        yield mapname, oname, objpos, obj

def getObjName(obj):
  "Get an object's name"
  oname = obj.getAttribute("xsi:type")
  if oname:
    return oname
  cnode = xmltools.getChildNode(obj, "Name")
  if cnode:
    return cnode.firstChild.nodeValue
  cnode = xmltools.getChildNode(obj, "name")
  if cnode:
    return cnode.firstChild.nodeValue
  return None

def getObjType(obj):
  "Get an object's type (category)"
  return xmltools.getNodeText(xmltools.getChildNode(obj, "type"))

def aggregateObjects(objlist):
  "Aggregate an interable of 4-tuples"
  bymap = collections.defaultdict(dict)
  for mapname, objname, objpos, obj in objlist:
    mcount = bymap[mapname].get(objname, 0)
    bymap[mapname][objname] = mcount + 1
  return bymap

def objectJSON(objnode, filters=()):
  "Convert an XML node to JSON (crudely)"
  filt_false = ("false" in filters)
  filt_zero = ("zero" in filters)
  filt_points = ("points" in filters)
  def mapFunc(key, value):
    origVal = value
    if isinstance(value, str):
      if value in ("true", "false"):
        value = (value == "true")
      elif isdigit(value):
        value = int(value)
    elif isinstance(value, (list, tuple)) \
        and len(value) == 2 \
        and isdigit(value[0]) and isdigit(value[1]):
      value = (int(value[0]), int(value[1]))
    if filt_false:
      if value is False:
        logger.debug("Filtering out False key %s (val %r)", key, origVal)
        return None
      if isinstance(value, (dict, list, tuple)) and not value:
        logger.debug("Filtering out empty key %s (val %r)", key, origVal)
        return None
    if filt_zero and value == 0:
      logger.debug("Filtering out zero key %s (val %r)", key, origVal)
      return None
    return value
  return json.dumps(
      xmltools.dumpNodeRec(objnode,
        mapFunc=mapFunc,
        interpretPoints=filt_points),
      indent=2, sort_keys=True)

def printObject(objdef, long=False, filters=()):
  "Print a 4-tuple object"
  mapname, objname, objpos, objnode = objdef
  if not long:
    print("{} {} at ({}, {})".format(mapname, objname, objpos[0], objpos[1]))
  else:
    print(objectJSON(objnode, filters=filters))

def getAllObjects(root, mapname=None, objname=None, objtype=None, objcat=None):
  "Get all objects (as 4-tuples) matching the given conditions"
  for mname, oname, opos, obj in getObjects(root):
    if mapname is not None and mname != mapname:
      continue
    if objname is not None and oname != objname:
      continue
    if objtype is not None and getObjType(obj) != objtype:
      continue
    if objcat is not None:
      if objcat == "forage" and oname not in FORAGE:
        continue
    yield mname, oname, opos, obj

def getObjectCounts(objs, mapname=None, sort=False):
  "Get aggregate object counts"
  bymap = aggregateObjects(objs)
  if not mapname:
    byname = collections.defaultdict(int)
    for objnames in bymap.values():
      for objname, objcount in objnames.items():
        byname[objname] += objcount
  else:
    byname = bymap.get(mapname)
  if byname:
    entries = list(byname.items())
    if sort:
      entries.sort(key=lambda kv: kv[1], reverse=True)
    return entries
  return []

def main():
  "Entry point"
  ap = argparse.ArgumentParser()
  ap.add_argument("-f", "--file", help="path to save file")
  ag = ap.add_argument_group("output")
  ag.add_argument("-n", "--name", metavar="NAME",
      help="limit output to a specific object kind")
  ag.add_argument("-c", "--count", action="store_true",
      help="show information about what objects exist")
  ag.add_argument("-L", "--long", action="store_true",
      help="display full object information")
  ag.add_argument("-s", "--sort", action="store_true",
      help="sort output where possible")
  ag = ap.add_argument_group("filtering")
  ag.add_argument("-m", "--map", metavar="MAP",
      help="limit to objects in a specific map")
  ag.add_argument("-t", "--type", metavar="TYPE",
      help="limit to objects of a given item class")
  ag.add_argument("-C", "--category", choices=VALID_CATEGORIES,
      help="limit output to a specific category of items")
  ag.add_argument("-F", "--filter", action="append", choices=VALID_FILTERS,
      help="apply specific filter(s) on the output")
  ap.add_argument("-v", "--verbose", action="store_true",
      help="verbose output")
  args = ap.parse_args()
  if args.verbose:
    logger.setLevel(logging.DEBUG)
    xmltools.getLogger().setLevel(logging.DEBUG)

  if not args.file:
    print("No save given; choices:")
    for f in os.listdir(SVPATH):
      if "." not in f:
        print(os.path.join(SVPATH, f))
    raise SystemExit(1)

  root = loadSave(args.file)

  objs = list(getAllObjects(root,
    mapname=args.map,
    objname=args.name,
    objtype=args.type,
    objcat=args.category))

  if args.count:
    prefix = "overall" if not args.map else args.map
    for objname, objcount in getObjectCounts(objs):
      print("{}: {} {}".format(prefix, objname, objcount))
  else:
    filters = args.filter if args.filter else []
    if args.sort:
      objs.sort(key=lambda odef: (odef[0], odef[1], odef[2]))
    for objdef in objs:
      printObject(objdef, long=args.long, filters=filters)

if __name__ == "__main__":
  main()

# vim: set ts=2 sts=2 sw=2:
