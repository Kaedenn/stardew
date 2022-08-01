#!/usr/bin/env python3

"""
Tools for examining the Stardew Valley save files
"""

import argparse
import collections
import fnmatch
import functools
import json
import logging
import os
import platform
import sys
import xml.dom.minidom as minidom

from colorterm import ColorFormatter as C
import stardew
import xmltools

# Add "TRACE" with a level of 5 (DEBUG is 10) and logger.trace to use it
logging.TRACE = 5
logging.addLevelName(logging.TRACE, "TRACE")
logging.Logger.trace = lambda self, *a, **kw: self.log(logging.TRACE, *a, **kw)

if platform.system() == "Linux":
  SVPATH = os.path.expanduser("~/.config/StardewValley/Saves")
elif platform.system() == "Windows":
  sys.stderr.write("WARNING: This program is not tested against Windows\n")
VALID_CATEGORIES = ("forage", "artifact")

MAP_OBJECTS = "objects"
MAP_FEATS_SMALL = "small"
MAP_FEATS_LARGE = "large"
MAP_FEATS_ALL = "+".join((MAP_FEATS_SMALL, MAP_FEATS_LARGE))
MAP_ALL = "+".join((MAP_OBJECTS, MAP_FEATS_ALL))

MAP_OBJ_VALUES = (
  MAP_OBJECTS,
  MAP_FEATS_SMALL,
  MAP_FEATS_LARGE
)

# For long-form output
VALID_FORMATTERS = ("false", "zero", "points")

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

def cmp(obj1, obj2):
  "Three-way compare two objects like Python2 did"
  return (obj1 > obj2) - (obj1 < obj2)

def deduceSaveFile(svname, svpath=SVPATH):
  "Determine a save file based only on the name of the farm"
  logger.debug("Searching for %s in %s", svname, svpath)
  for fname in os.listdir(svpath):
    fpath = os.path.join(svpath, fname)
    if os.path.isdir(fpath) and fname.count("_") == 1:
      farm, fid = fname.split("_")
      if farm == svname:
        logger.debug("Found %s", os.path.join(svpath, fname))
        return os.path.join(svpath, fname)
  logger.debug("Failed to find farm %s in %s", svname, svpath)
  return None

def loadSave(svdir, svpath=SVPATH):
  "Load a save file by name, directory path, or file path"
  if os.path.isabs(svdir):
    path = svdir
    svname = os.path.basename(svdir)
  else:
    path = os.path.join(svpath, svdir)
    svname = svdir
  logger.debug("Save dir: %s name %s", path, svname)
  fpath = path
  if os.path.isdir(path):
    fpath = os.path.join(path, svname)
  return minidom.parse(open(fpath, "rt"))

def isNilObject(node):
  "True if the object is just xsi:nil"
  if not node.firstChild:
    if node.attributes:
      if dict(node.attributes.items()).get("xsi:nil") == "true":
        return True
  return False

def getLocations(root):
  "Get all map locations"
  for gloc in root.getElementsByTagName("GameLocation"):
    mapname = getObjName(gloc)
    if not mapname:
      mapname = stardew.LOCATION_UNKNOWN
    if mapname not in stardew.LOCATIONS:
      logger.warning("Unknown game location %s", mapname)
    yield mapname, gloc

def mapGetObjects(melem):
  "Get objects within a game location"
  for node in melem.getElementsByTagName("Object"):
    if not isNilObject(node):
      oname = getObjName(node)
      objpos = xmltools.nodeToCoord(xmltools.getChildNode(node, "tileLocation"))
      yield oname, objpos, node

def mapGetFeatures(melem, large=False):
  "Get terrain features within a game location"
  fnodes = []
  small_node = xmltools.getChildNode(melem, "terrainFeatures")
  large_node = xmltools.getChildNode(melem, "largeTerrainFeatures")
  for node in xmltools.getNodeChildren(small_node):
    if not isNilObject(node):
      knode = xmltools.descend(node, "key/Vector2")
      fnode = xmltools.descend(node, "value/TerrainFeature")
      fname = getObjName(fnode)
      fpos = xmltools.nodeToCoord(knode)
      yield fname, fpos, fnode
  if large:
    for node in xmltools.getNodeChildren(large_node):
      fname = getObjName(node)
      fpos = xmltools.nodeToCoord(xmltools.descend(node, "tilePosition"))
      yield fname, fpos, node

def getObjects(root):
  "Get objects"
  for mapname, gloc in getLocations(root):
    for oname, opos, node in mapGetObjects(gloc):
      yield mapname, oname, opos, node

def getFeatures(root, large=False):
  "Get terrain features, optionally including large features"
  for mapname, gloc in getLocations(root):
    for fname, fpos, node in mapGetFeatures(gloc, large=large):
      yield mapname, fname, fpos, node

def getObjName(node):
  "Get an object's name"
  oname = node.getAttribute("xsi:type")
  if oname:
    return oname
  cnode = xmltools.getChildNode(node, "Name", ignorecase=True)
  if cnode:
    return cnode.firstChild.nodeValue
  return None

def getObjType(node):
  "Get an object's type (category)"
  if xmltools.nodeHasChild(node, "type"):
    return xmltools.getNodeText(xmltools.getChildNode(node, "type"))
  return getObjName(node)

def aggregateObjects(objlist):
  "Aggregate an interable of 4-tuples"
  bymap = collections.defaultdict(dict)
  for mapname, objname, objpos, obj in objlist:
    mcount = bymap[mapname].get(objname, 0)
    bymap[mapname][objname] = mcount + 1
  return bymap

def objectJSON(objnode, formatters=()):
  "Convert an XML node to JSON (crudely)"
  filt_false = ("false" in formatters)
  filt_zero = ("zero" in formatters)
  filt_points = ("points" in formatters)
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

def printObject(objdef, long=False, formatters=()):
  "Print a 4-tuple object"
  mapname, objname, objpos, objnode = objdef
  if not long:
    mapname = C(C.GRN, mapname)
    objname = C(C.CYN, C.BOLD, objname)
    objx = C(C.BOLD, f"{objpos[0]}")
    objy = C(C.BOLD, f"{objpos[1]}")
    print("{} {} at ({}, {})".format(mapname, objname, objx, objy))
  else:
    print(objectJSON(objnode, formatters=formatters))

def matches(seq, term):
  "True if seq includes term, False if seq forbids term, None otherwise"
  def match(expect, value):
    "True if expect matches the value"
    return fnmatch.fnmatch(expect, value)

  if not term:
    return None

  # parse exclusions first
  for item in seq:
    if item.startswith("!") and match(item[1:], term):
      return False
  for item in seq:
    if not item.startswith("!") and match(item, term):
      return True
  return None

def getAllObjects(root,
    mapnames,
    objnames,
    objtypes,
    objcats,
    features=MAP_OBJECTS):
  "Get all objects (as 4-tuples) matching any of the given conditions"

  def update_show(seq, term, curr_show):
    "Determine if we should show the object"
    if curr_show is False: # false takes precedence over all
      return False
    if term is not None:
      mat = matches(seq, term)
      if mat is not None:
        return mat
    return curr_show

  def chainfunc():
    "Get the selected things"
    things = features.split("+")
    if MAP_OBJECTS in things:
      logger.debug("Selecting objects")
      for mname, oname, opos, obj in getObjects(root):
        yield MAP_OBJECTS, mname, oname, opos, obj
    if MAP_FEATS_SMALL in things:
      logger.debug("Selecting small features")
      for mname, oname, opos, obj in getFeatures(root, large=False):
        yield MAP_FEATS_SMALL, mname, oname, opos, obj
    if MAP_FEATS_LARGE in things:
      logger.debug("Selecting large features")
      for mname, oname, opos, obj in getFeatures(root, large=True):
        yield MAP_FEATS_LARGE, mname, oname, opos, obj
  for kind, mname, oname, opos, obj in chainfunc():
    show = None # tri-bool
    # no specifications matches everything
    if not (mapnames or objnames or objtypes or objcats):
      show = True
    else:
      show = update_show(objnames, oname, show)
      show = update_show(objtypes, getObjType(obj), show)
      if show is None:
        if kind == MAP_OBJECTS:
          if matches(objcats, "artifact") and oname in stardew.ARTIFACT:
            show = True
          elif matches(objcats, "forage") and oname in stardew.FORAGE:
            show = True
        elif kind == MAP_FEATS_SMALL:
          pass # TODO: implement
        elif kind == MAP_FEATS_LARGE:
          pass # TODO: implement
      # map names are exclusive
      if mapnames and not matches(mapnames, mname):
        show = False
    if show is True:
      logger.trace("%s %s %s object", mname, oname, opos)
      yield mname, oname, opos, obj

def getObjectCounts(objs, mapname=None, sort=False):
  "Get aggregate object counts"
  @functools.cmp_to_key
  def entry_sort_key(kv1, kv2):
    "Compare two entries"
    name1, count1 = kv1
    name2, count2 = kv2
    if count1 < count2:
      return 1  # reversed
    if count1 > count2:
      return -1 # reversed
    return cmp(name1, name2)

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
      entries.sort(key=entry_sort_key)
    return entries
  return []

def main():
  "Entry point"
  ap = argparse.ArgumentParser(epilog="""
The following logic is used to determine the path to your farm file:
  If -f,--file is given, use that.
  Otherwise, if --farm is given, then scan the save path (see -P,--save-path).
  Otherwise, if --list is given, then list all farms in the save path.
  Otherwise, print the program usage and exit.

The following arguments can be specified multiple times:
  -n,--name  -F,--formatter  -m,--map  -t,--type  -C,--category

The following arguments support negation by prefixing the value with '!':
  -n,--name  -m,--map  -t,--type

The following arguments support simple glob patterns via fnmatch:
  -n,--name  -m,--map  -t,--type
  """, formatter_class=argparse.RawTextHelpFormatter)
  ag = ap.add_argument_group("farm selection")
  mg = ag.add_mutually_exclusive_group()
  mg.add_argument("--farm", metavar="NAME",
      help="farm name")
  mg.add_argument("-f", "--file", help="path to save file")
  mg.add_argument("--list", action="store_true",
      help="list available save files")
  ag.add_argument("-P", "--save-path", default=SVPATH,
      help="path to saves (default: %(default)s)")
  ag = ap.add_argument_group("object enumeration")
  ag.add_argument("-i", "--include", metavar="THING", action="append",
      choices=MAP_OBJ_VALUES,
      help="get specific things (default: {})".format(MAP_OBJECTS))
  ag.add_argument("-n", "--name", action="append", metavar="NAME",
      help="select object(s) based on name")
  ag = ap.add_argument_group("output configuration")
  ag.add_argument("-c", "--count", action="store_true",
      help="show aggregate information about object counts")
  ag.add_argument("-s", "--sort", action="store_true",
      help="sort output where possible")
  ag = ap.add_argument_group("output filtering")
  ag.add_argument("-m", "--map", action="append", metavar="MAP",
      help="limit to specific map(s)")
  ag.add_argument("-t", "--type", action="append", metavar="TYPE",
      help="limit to particular class(es)")
  ag.add_argument("-C", "--category", action="append",
      choices=VALID_CATEGORIES,
      help="limit to specific category(ies) of objects")
  ag = ap.add_argument_group("XML output configuration")
  ag.add_argument("-L", "--long", action="store_true",
      help="display long-form object information")
  ag.add_argument("-F", "--formatter", action="append",
      choices=VALID_FORMATTERS,
      help="apply specific formatter(s) on long-form output")
  ag = ap.add_argument_group("logging and diagnostics")
  ag.add_argument("--no-color", action="store_true",
      help="disable color output")
  mg = ag.add_mutually_exclusive_group()
  mg.add_argument("-v", "--verbose", action="store_true",
      help="enable verbose-level output")
  mg.add_argument("--trace", action="store_true",
      help="enable trace-level output")
  args = ap.parse_args()
  if args.verbose:
    logger.setLevel(logging.DEBUG)
    xmltools.getLogger().setLevel(logging.DEBUG)
  elif args.trace:
    logger.setLevel(logging.TRACE)
    xmltools.getLogger().setLevel(logging.TRACE)
  if args.no_color:
    C.disable()

  svpath = args.save_path
  if args.list:
    for savename in os.listdir(svpath):
      savepath = os.path.join(svpath, savename)
      savefile = os.path.join(savepath, savename)
      if os.path.isdir(savepath) and os.path.exists(savefile):
        print(os.path.join(savepath, savename))
  elif not (args.farm or args.file):
    ap.print_usage()
    raise SystemExit(0)

  savepath = args.file
  if args.farm:
    savepath = deduceSaveFile(args.farm, svpath=svpath)

  if not savepath or not os.path.exists(savepath):
    ap.error("Failed to find farm")

  root = loadSave(savepath, svpath=svpath)

  feature_kinds = MAP_OBJECTS
  if args.include is not None:
    feature_kinds = "+".join(args.include)

  mapnames = args.map if args.map else []
  objnames = args.name if args.name else []
  objtypes = args.type if args.type else []
  objcats = args.category if args.category else []
  objs = list(getAllObjects(root,
    mapnames=mapnames,
    objnames=objnames,
    objtypes=objtypes,
    objcats=objcats,
    features=feature_kinds))

  if args.count:
    prefix = "overall"
    if args.map:
      prefix = "+".join(args.map)
    for objname, objcount in getObjectCounts(objs, sort=args.sort):
      prefix = C(C.GRN, prefix)
      objname = C(C.CYN, objname)
      print("{} {} {}".format(prefix, objname, objcount))
  else:
    formatters = args.formatter if args.formatter else []
    if args.sort:
      objs.sort(key=lambda odef: (odef[0], odef[1], odef[2]))
    for objdef in objs:
      printObject(objdef, long=args.long, formatters=formatters)

if __name__ == "__main__":
  main()

# vim: set ts=2 sts=2 sw=2:
