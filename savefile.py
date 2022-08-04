#!/usr/bin/env python3

"""
Tools for examining the Stardew Valley save files
"""

# TODO:
# Implement filtering for crops
# Implement filtering for small terrain features (if needed?)
# Implement filtering for large terrain features (if needed?)

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
from stardew import Obj as O
import xmltools

# Add "TRACE" with a level of 5 (DEBUG is 10) and logger.trace to use it
logging.TRACE = 5
logging.addLevelName(logging.TRACE, "TRACE")
logging.Logger.trace = lambda self, *a, **kw: self.log(logging.TRACE, *a, **kw)

if platform.system() == "Linux":
  SVPATH = os.path.expanduser("~/.config/StardewValley/Saves")
elif platform.system() == "Windows":
  sys.stderr.write("WARNING: This program is not tested against Windows\n")
  SVPATH = os.environ.get("HOME", "")
VALID_CATEGORIES = ("forage", "artifact", "crops")

MAP_OBJECTS = "objects"
MAP_FEATS_SMALL = "small"
MAP_FEATS_LARGE = "large"
MAP_FEATS_CROPS = "crops"

MAP_ITEM_TYPES = {
  "objects": MAP_OBJECTS,
  "small": MAP_FEATS_SMALL,
  "large": MAP_FEATS_LARGE,
  "crops": MAP_FEATS_CROPS,
  "features": "+".join((MAP_FEATS_SMALL, MAP_FEATS_LARGE)),
  "all": "+".join((MAP_OBJECTS, MAP_FEATS_SMALL, MAP_FEATS_LARGE)),
}

MAP_OBJ_VALUES = (
  MAP_OBJECTS,
  MAP_FEATS_SMALL,
  MAP_FEATS_LARGE
)

OUT_BRIEF = 0
OUT_NORMAL = 1
OUT_LONG = 2
OUT_FULL = 3

# For long-form output
VALID_FORMATTERS = ("false", "zero", "points", "crops")

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

def deduce_save_file(svname, svpath=SVPATH):
  "Determine a save file based only on the name of the farm"
  logger.debug("Searching for %s in %s", svname, svpath)
  for fname in os.listdir(svpath):
    fpath = os.path.join(svpath, fname)
    if os.path.isdir(fpath) and fname.count("_") == 1:
      farm, fid = fname.split("_")
      logger.trace("Farm %s ID %s", farm, fid)
      if farm == svname:
        logger.debug("Found %s", os.path.join(svpath, fname))
        return os.path.join(svpath, fname)
  logger.debug("Failed to find farm %s in %s", svname, svpath)
  return None

def load_save(svdir, svpath=SVPATH):
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

def is_nil_node(node):
  "True if the object is just xsi:nil"
  if not node.firstChild:
    if node.attributes:
      if dict(node.attributes.items()).get("xsi:nil") == "true":
        return True
  return False

def get_locations(root):
  "Get all map locations"
  for gloc in root.getElementsByTagName("GameLocation"):
    mapname = get_obj_name(gloc)
    if not mapname:
      mapname = stardew.LOCATION_UNKNOWN
    if mapname not in stardew.LOCATIONS:
      logger.warning("Unknown game location %s", mapname)
    yield mapname, gloc

def map_get_objects(melem):
  "Get objects within a game location"
  for node in melem.getElementsByTagName("Object"):
    if not is_nil_node(node):
      oname = get_obj_name(node)
      objpos = xmltools.nodeToCoord(xmltools.getChildNode(node, "tileLocation"))
      yield oname, objpos, node

def map_get_features(melem, large=False):
  "Get terrain features within a game location"
  small_node = xmltools.getChildNode(melem, "terrainFeatures")
  large_node = xmltools.getChildNode(melem, "largeTerrainFeatures")
  for node in xmltools.getNodeChildren(small_node):
    if not is_nil_node(node):
      knode = xmltools.descend(node, "key/Vector2")
      fnode = xmltools.descend(node, "value/TerrainFeature")
      fname = get_obj_name(fnode)
      fpos = xmltools.nodeToCoord(knode)
      yield fname, fpos, fnode
  if large:
    for node in xmltools.getNodeChildren(large_node):
      fname = get_obj_name(node)
      fpos = xmltools.nodeToCoord(xmltools.descend(node, "tilePosition"))
      yield fname, fpos, node

def get_objects(root):
  "Get objects"
  for mapname, gloc in get_locations(root):
    for oname, opos, node in map_get_objects(gloc):
      yield mapname, oname, opos, node

def get_features(root, large=False):
  "Get terrain features, optionally including large features"
  for mapname, gloc in get_locations(root):
    for fname, fpos, node in map_get_features(gloc, large=large):
      yield mapname, fname, fpos, node

def get_obj_name(node):
  "Get an object's name"
  oname = node.getAttribute("xsi:type")
  if oname:
    return oname
  cnode = xmltools.getChildNode(node, "Name", ignorecase=True)
  if cnode:
    return cnode.firstChild.nodeValue
  return None

def get_obj_type(node):
  "Get an object's type (category)"
  if xmltools.nodeHasChild(node, "type"):
    return xmltools.getNodeText(xmltools.getChildNode(node, "type"))
  return get_obj_name(node)

def is_crop(node):
  "True if the node is a non-empty HoeDirt"
  if get_obj_type(node) == "HoeDirt":
    cnode = xmltools.descend(node, "crop/seedIndex")
    if cnode and xmltools.getNodeText(cnode) != "-1":
      return True
  return False

def aggregate_objects(objlist):
  "Aggregate an interable of 4-tuples"
  bymap = collections.defaultdict(dict)
  for mapname, objname, objpos, obj in objlist:
    mcount = bymap[mapname].get(objname, 0)
    bymap[mapname][objname] = mcount + 1
  return bymap

def object_json(objnode, formatters=()):
  "Convert an XML node to JSON (crudely)"
  filt_false = ("false" in formatters)
  filt_zero = ("zero" in formatters)
  filt_points = ("points" in formatters)
  def map_func(key, value):
    orig_val = value
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
        logger.debug("Filtering out False key %s (val %r)", key, orig_val)
        return None
      if isinstance(value, (dict, list, tuple)) and not value:
        logger.debug("Filtering out empty key %s (val %r)", key, orig_val)
        return None
    if filt_zero and value == 0:
      logger.debug("Filtering out zero key %s (val %r)", key, orig_val)
      return None
    return value
  return json.dumps(
      xmltools.dumpNodeRec(objnode,
        mapFunc=map_func,
        interpretPoints=filt_points),
      indent=2, sort_keys=True)

def print_crop(objdef, verbosity=OUT_BRIEF):
  "Print a 4-tuple object representing a crop"
  mapname, objname, objpos, objnode = objdef
  notes = []
  feat_data = xmltools.dumpNodeRec(objnode)["TerrainFeature"]
  crop = feat_data["crop"]
  objname = stardew.get_object(crop["seedIndex"], field=O.NAME)
  if crop.get("dead"):
    notes.append("dead")
  if crop.get("fullGrown"):
    notes.append("ready")
  fertilizer = int(feat_data["fertilizer"])
  forage = crop["forageCrop"]
  phase = int(crop["currentPhase"])
  phase_days = int(crop.get("phaseDays", {}).get("int"))
  min_harvest = int(crop["minHarvest"])
  max_harvest = int(crop["maxHarvest"])
  if verbosity >= OUT_NORMAL:
    if crop.get("seasonsToGrowIn"):
      seasons = crop["seasonsToGrowIn"]
      seasons = seasons.get("string", seasons)
      # TODO: color text appropriately
      notes.append(f"{seasons}")
  if verbosity >= OUT_LONG:
    if forage:
      notes.append("forage")
    if fertilizer > 0:
      fertilizer = stardew.get_object(fertilizer, field=O.NAME)
      notes.append(f"fertilizer={fertilizer!r}")
  if verbosity >= OUT_FULL:
    notes.append(f"phase={phase} days={phase_days}")
    if min_harvest == max_harvest:
      notes.append(f"yield={min_harvest}")
    elif min_harvest and max_harvest:
      notes.append(f"yield={min_harvest} to {max_harvest}")
  print("{} {} at ({}, {}) {}".format(
    C(C.GRN, mapname),
    C(C.CYN, C.BOLD, objname),
    C(C.BOLD, f"{objpos[0]}"),
    C(C.BOLD, f"{objpos[1]}"),
    "; ".join(notes)))

def print_object(objdef, long=False, formatters=(), verbosity=OUT_BRIEF):
  "Print a 4-tuple object"
  mapname, objname, objpos, objnode = objdef
  if not long:
    if "crops" in formatters and is_crop(objnode):
      print_crop(objdef, verbosity=verbosity)
    else:
      mapname = C(C.GRN, mapname)
      objname = C(C.CYN, C.BOLD, objname)
      objx = C(C.BOLD, f"{objpos[0]}")
      objy = C(C.BOLD, f"{objpos[1]}")
      # TODO: adjust based on verbosity level
      print("{} {} at ({}, {})".format(mapname, objname, objx, objy))
  else:
    print(object_json(objnode, formatters=formatters))

def matches(seq, term):
  "True if seq includes term, False if seq forbids term, None otherwise"
  if not term:
    return None
  for item in seq:
    if item.startswith("!") and fnmatch.fnmatch(item[1:], term):
      return False
  for item in seq:
    if not item.startswith("!") and fnmatch.fnmatch(item, term):
      return True
  return None

def get_all_objects(root,
    mapnames,
    objnames,
    objtypes,
    objcats,
    features=MAP_OBJECTS):
  "Get all objects (as 4-tuples) matching any of the given conditions"

  def update_show(new_show, curr_show):
    "Determine if we should update the show value"
    if curr_show is None:
      return new_show
    if new_show is None:
      return curr_show
    if curr_show is False or new_show is False:
      return False
    return curr_show or new_show

  def test_item(seq, term, curr_show):
    "Determine if we should show the object"
    new_show = None
    if term is not None:
      mat = matches(seq, term)
      if mat is not None:
        new_show = True
    return update_show(new_show, curr_show)

  def get_things():
    "Get the selected things"
    things = features.split("+")
    if MAP_OBJECTS in things:
      logger.debug("Selecting objects")
      for mname, oname, opos, obj in get_objects(root):
        yield MAP_OBJECTS, mname, oname, opos, obj
    if MAP_FEATS_CROPS in things:
      logger.debug("Selecting crop features")
      for mname, oname, opos, obj in get_features(root, large=False):
        if is_crop(obj):
          yield MAP_FEATS_CROPS, mname, oname, opos, obj
    elif MAP_FEATS_SMALL in things:
      logger.debug("Selecting small features")
      for mname, oname, opos, obj in get_features(root, large=False):
        yield MAP_FEATS_SMALL, mname, oname, opos, obj
    if MAP_FEATS_LARGE in things:
      logger.debug("Selecting large features")
      for mname, oname, opos, obj in get_features(root, large=True):
        yield MAP_FEATS_LARGE, mname, oname, opos, obj

  for kind, mname, oname, opos, obj in get_things():
    show = None # tri-bool

    # process maps first
    if mapnames and not matches(mapnames, mname):
      show = False

    if objnames or objtypes or objcats:
      show = test_item(objnames, oname, show)
      show = test_item(objtypes, get_obj_type(obj), show)
      if kind == MAP_OBJECTS:
        if matches(objcats, "artifact") and oname in stardew.ARTIFACT:
          show = update_show(True, show)
        elif matches(objcats, "forage") and oname in stardew.FORAGE:
          show = update_show(True, show)
      elif kind == MAP_FEATS_CROPS:
        pass # TODO: implement
      elif kind == MAP_FEATS_SMALL:
        pass # TODO: implement
      elif kind == MAP_FEATS_LARGE:
        pass # TODO: implement
    elif show is None:
      # no specifications matches everything
      show = True

    if show is True:
      logger.trace("%s %s %s object", mname, oname, opos)
      yield mname, oname, opos, obj

def get_object_counts(objs, mapname=None, sort=False):
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

  bymap = aggregate_objects(objs)
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

class ArgFormatter(argparse.RawDescriptionHelpFormatter):
  "Replacement argparse formatter class"

  def is_append_action(self, action):
    "Hack to determine if the action is append"
    try:
      for cls in action.__class__.mro():
        clsname = cls.__name__
        return "AppendAction" in clsname or "AppendConstAction" in clsname
    except (AttributeError, ValueError, KeyError, IndexError):
      pass
    return False

  @staticmethod
  def test_add_default(action):
    "True if we should append %(default)s to help"
    add_default = True
    if '%(default)' in action.help:
      add_default = False
    elif action.const is True and action.default is False:
      add_default = False
    elif action.default is argparse.SUPPRESS or action.default is None:
      add_default = False
    elif not (action.option_strings
        or action.nargs in (argparse.OPTIONAL, argparse.ZERO_OR_MORE)):
      add_default = False
    return add_default

  def _get_help_string(self, action):
    "Format the help string for the given action"
    ahelp = action.help
    if self.test_add_default(action):
      ahelp = ahelp + ' (default: %(default)s)'
    if self.is_append_action(action):
      ahelp = "(multi) " + ahelp
    return ahelp

def main():
  "Entry point"
  ap = argparse.ArgumentParser(epilog="""
The following logic is used to determine the path to your farm file:
  If -f,--file is given, use that.
  Otherwise, if --farm is given, then scan the save path (see -P,--save-path).
  If this fails, the program aborts with an error.
  Otherwise, if --list is given, then list all farms in the save path and exit.
  Otherwise, print the program usage and exit.

The following arguments can be specified multiple times:
  -n,--name  -F,--formatter  -m,--map  -t,--type  -C,--category  -i,--include

The following arguments support negation by prefixing the value with '!':
  -n,--name  -m,--map  -t,--type

The following arguments support simple glob patterns via fnmatch:
  -n,--name  -m,--map  -t,--type

The -i,--include argument accepts the following values:
  objects     objects (forage, artifact spots, placed things)
  crops       hoe dirt with a crop
  small       small terrain features (trees, hoe dirt, flooring, fruit trees)
  large       large terrain features (bushes)
  features    both small and large terrain features
  all         objects and terrain features

Pass -v to enable verbose logging. Pass -v twice (or -vv) for trace logging.
""", formatter_class=ArgFormatter)
  ag = ap.add_argument_group("farm selection")
  mg = ag.add_mutually_exclusive_group()
  mg.add_argument("--farm", metavar="NAME",
      help="farm name")
  mg.add_argument("-f", "--file", help="path to save file")
  mg.add_argument("--list", action="store_true",
      help="list available save files")
  ag.add_argument("-P", "--save-path", default=SVPATH,
      help="path to saves")
  ag = ap.add_argument_group("object enumeration")
  ag.add_argument("-i", "--include", action="append",
      choices=MAP_ITEM_TYPES.keys(),
      help=f"get specific things")
  ag.add_argument("-n", "--name", action="append", metavar="NAME",
      help="select objects based on name")
  ag = ap.add_argument_group("output configuration")
  ag.add_argument("-c", "--count", action="store_true",
      help="show aggregate information about object counts")
  ag.add_argument("-s", "--sort", action="store_true",
      help="sort output where possible")
  ag.add_argument("-l", "--verbosity-level", type=int, default=OUT_BRIEF,
      choices=range(OUT_FULL+1),
      help="output level: amount of information displayed")
  ag = ap.add_argument_group("output filtering")
  ag.add_argument("-m", "--map", action="append", metavar="MAP",
      help="limit to specific maps")
  ag.add_argument("-t", "--type", action="append", metavar="TYPE",
      help="limit to particular classes")
  ag.add_argument("-C", "--category", action="append",
      choices=VALID_CATEGORIES,
      help="limit to specific categories of objects")
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
  mg.add_argument("-v", "--verbose", action="count",
      help="enable verbose-level output, twice to enable trace-level output")
  args = ap.parse_args()
  if args.verbose == 1:
    logger.setLevel(logging.DEBUG)
    xmltools.getLogger().setLevel(logging.DEBUG)
  elif args.verbose == 2:
    logger.setLevel(logging.TRACE)
    xmltools.getLogger().setLevel(logging.TRACE)
  if args.no_color:
    C.disable()

  logger.debug("Data: %s", stardew.DATA_PATH)
  logger.debug("NPCS: %d", len(stardew.NPCS))
  logger.debug("LOCATIONS: %d", len(stardew.LOCATIONS))
  logger.debug("OBJECTS: %d", len(stardew.OBJECTS))

  svpath = args.save_path
  if args.list:
    # Simply list the save files available
    for savename in os.listdir(svpath):
      savepath = os.path.join(svpath, savename)
      savefile = os.path.join(savepath, savename)
      if os.path.isdir(savepath) and os.path.exists(savefile):
        print(os.path.join(savepath, savename))
    raise SystemExit(0)

  if not (args.farm or args.file):
    ap.print_usage()
    raise SystemExit(0)

  savepath = args.file
  if args.farm:
    savepath = deduce_save_file(args.farm, svpath=svpath)

  if not savepath or not os.path.exists(savepath):
    ap.error("Failed to find farm")

  root = load_save(savepath, svpath=svpath)

  feature_kinds = MAP_OBJECTS
  if args.include is not None:
    given_kinds = set()
    for want_kind in args.include:
      given_kinds.update(MAP_ITEM_TYPES[want_kind].split("+"))
    feature_kinds = "+".join(given_kinds)

  mapnames = args.map if args.map else []
  objnames = args.name if args.name else []
  objtypes = args.type if args.type else []
  objcats = args.category if args.category else []
  objs = list(get_all_objects(root,
    mapnames=mapnames,
    objnames=objnames,
    objtypes=objtypes,
    objcats=objcats,
    features=feature_kinds))

  if args.count:
    prefix = "overall"
    if args.map:
      prefix = "+".join(args.map)
    for objname, objcount in get_object_counts(objs, sort=args.sort):
      prefix = C(C.GRN, prefix)
      objname = C(C.CYN, objname)
      print("{} {} {}".format(prefix, objname, objcount))
  else:
    formatters = args.formatter if args.formatter else []
    if args.sort:
      objs.sort(key=lambda odef: (odef[0], odef[1], odef[2]))
    for objdef in objs:
      print_object(objdef, long=args.long, formatters=formatters,
          verbosity=args.verbosity_level)

if __name__ == "__main__":
  main()

# vim: set ts=2 sts=2 sw=2:
