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
import sys
import xml.dom.minidom as minidom

from utility.colorterm import ColorFormatter as C
import stardew
from stardew import Data as D
import xmltools

import utility.tracelog

SVPATH = os.path.join(stardew.get_game_dir(), "Saves")

CATEGORIES = (
  "forage",
  "artifact",
  "cropready",
  "cropdead",
  "nofert",
  "fertnocrop"
)

MAP_OBJECTS = "objects"
MAP_FEATS_SMALL = "small"
MAP_FEATS_LARGE = "large"
MAP_CROPS = "crops"
MAP_TREES = "trees"
MAP_FRUIT_TREES = "fruittrees"
MAP_ANIMALS = "animals"
MAP_SLIMES = "slimes"

MAP_ITEM_TYPES = {
  MAP_OBJECTS: MAP_OBJECTS,
  MAP_FEATS_SMALL: MAP_FEATS_SMALL,
  MAP_FEATS_LARGE: MAP_FEATS_LARGE,
  MAP_CROPS: MAP_CROPS,
  MAP_TREES: MAP_TREES,
  MAP_FRUIT_TREES: MAP_FRUIT_TREES,
  MAP_ANIMALS: MAP_ANIMALS,
  MAP_SLIMES: MAP_SLIMES,
  "alltrees": "+".join((MAP_TREES, MAP_FRUIT_TREES)),
  "features": "+".join((MAP_FEATS_SMALL, MAP_FEATS_LARGE)),
  "all": "+".join((
    MAP_OBJECTS,
    MAP_CROPS,
    MAP_FEATS_SMALL,
    MAP_FEATS_LARGE,
    MAP_TREES,
    MAP_FRUIT_TREES
  )),
}

CROP_BRIEF = 0
CROP_NORMAL = 1
CROP_LONG = 2
CROP_FULL = 3
CROP_LEVELS = {
  "brief": CROP_BRIEF,
  "normal": CROP_NORMAL,
  "long": CROP_LONG,
  "full": CROP_FULL
}

# For long-form output
FORMATTERS = ("false", "zero", "points")

utility.tracelog.hotpatch(logging)
logging.basicConfig(format="%(module)s:%(lineno)s: %(levelname)s: %(message)s",
                    level=logging.INFO)
logger = logging.getLogger(__name__)

class MapEntry:
  "Abstraction of a thing with an X, Y location"
  def __init__(self, kind, mapname, objname, objpos, objnode):
    "Constructor"
    self._kind = kind
    self._mapname = mapname
    self._objname = objname
    self._objpos = objpos
    self._objnode = objnode

  @property
  def kind(self):
    "What kind of thing are we looking at?"
    return self._kind

  @property
  def map(self):
    "What map is this thing on?"
    return self._mapname

  @property
  def name(self):
    "What is this thing's name?"
    return self._objname

  @property
  def pos(self):
    "Where is this thing, in tile coordinates?"
    return self._objpos

  @property
  def node(self):
    "The underlying XML node"
    return self._objnode

def isdigit(value):
  "True if value is an integer"
  try:
    int(value)
    return True
  except ValueError:
    return False

def isnumber(value):
  "True if value is a number"
  try:
    float(value)
    return True
  except ValueError:
    return False

def cmp(obj1, obj2):
  "Three-way compare two objects like Python2 did"
  return (obj1 > obj2) - (obj1 < obj2)

def is_farm_save(svpath):
  "True if the path looks like it's a farm's save directory"
  if os.path.isdir(svpath):
    svname = os.path.basename(svpath)
    if os.path.isfile(os.path.join(svpath, svname)):
      if svname.count("_") == 1 and svname[svname.index("_")+1:].isdigit():
        return True
  return False

def deduce_save_file(svname, svpath=SVPATH):
  "Determine a save file based only on the name of the farm"
  logger.debug("Searching for %s in %s", svname, svpath)

  # Handle cases where we're passed a path
  if os.path.exists(svname):
    if os.path.isdir(svname):
      fname = os.path.basename(svname.rstrip("/"))
      return os.path.join(svname, fname)
    if os.path.isfile(svname):
      return svname

  for fname in os.listdir(svpath):
    fpath = os.path.join(svpath, fname)
    if is_farm_save(fpath):
      farm, farmid = fname.split("_")
      logger.trace("Found farm %s with ID %s at %s", farm, farmid, fpath)
      if svname in (fname, farm):
        logger.debug("Found %s", os.path.join(svpath, fname))
        return os.path.join(svpath, fname)

  return None

def load_save_file(svpath):
  "Load a save by either directory or file path"
  if os.path.isdir(svpath):
    svdir = svpath
    svname = os.path.basename(svpath)
  else:
    svdir, svname = os.path.split(svpath)
  svfile = os.path.join(svdir, svname)
  logger.debug("Loading %s from %s", svname, svdir)
  return minidom.parse(open(svfile, "rt"))

def is_nil_node(node):
  "True if the object is just xsi:nil"
  if not node.firstChild:
    if node.getAttribute("xsi:nil") == "true":
      return True
  return False

def is_coord_node(node):
  "True if the node is an X, Y location"
  if xmltools.isTextNode(node):
    return False
  if set(xmltools.getNodeChildren(node, names_only=True)) == set(("X", "Y")):
    return True
  return False

def node_to_coord(node):
  "Convert a Vector2 node to a pair of points"
  if is_coord_node(node):
    xnode = xmltools.getNodeChild(node, "X")
    ynode = xmltools.getNodeChild(node, "Y")
    xvalue = xmltools.getNodeText(xnode)
    yvalue = xmltools.getNodeText(ynode)
    if isdigit(xvalue) and isdigit(yvalue):
      xvalue = int(xvalue)
      yvalue = int(yvalue)
    return xvalue, yvalue
  return None

def get_locations(root):
  "Get all map locations"
  for gloc in root.getElementsByTagName("GameLocation"):
    mapname = get_obj_name(gloc)
    if not mapname:
      mapname = stardew.LOCATION_UNKNOWN
    if mapname not in stardew.LOCATIONS:
      logger.warning("Unknown game location %s", mapname)
    yield mapname, gloc

def get_location(root, name):
  "Get a named location, for convenience"
  for lname, loc in get_locations(root):
    if lname == name:
      return loc
  logger.warning("Failed to find location named %r", name)
  return None

def map_get_objects(melem): # TODO: merge into get_objects()?
  "Get objects within a game location"
  for node in melem.getElementsByTagName("Object"):
    if not is_nil_node(node):
      oname = get_obj_name(node)
      objpos = node_to_coord(xmltools.getNodeChild(node, "tileLocation"))
      yield oname, objpos, node

def map_get_features(melem, large=False): # TODO: merge into get_features()?
  "Get terrain features within a game location"
  small_node = xmltools.getNodeChild(melem, "terrainFeatures")
  for node in xmltools.getNodeChildren(small_node):
    if not is_nil_node(node):
      knode = xmltools.descend(node, "key/Vector2")
      fnode = xmltools.descend(node, "value/TerrainFeature")
      fname = get_obj_name(fnode)
      fpos = node_to_coord(knode)
      yield fname, fpos, fnode
  if large:
    large_node = xmltools.getNodeChild(melem, "largeTerrainFeatures")
    for node in xmltools.getNodeChildren(large_node):
      fname = get_obj_name(node)
      fpos = node_to_coord(xmltools.descend(node, "tilePosition"))
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

def get_trees(root, fruit=False):
  "Get trees (or fruit trees)"
  return ()

def get_animals(root):
  "Get livestock"
  bpath = "buildings/Building/indoors"
  apath = "animals/item/value/FarmAnimal"
  # modding decision: allow buildings on maps other than Farm
  for mapname, gloc in get_locations(root):
    for bldg in xmltools.descendAll(gloc, bpath):
      btype = bldg.getAttribute("xsi:type")
      logger.debug("Examining building %s", btype)
      for anode in xmltools.descendAll(bldg, apath):
        atype = xmltools.getChildText(anode, "type")
        apos = node_to_coord(xmltools.getNodeChild(anode, "homeLocation"))
        yield mapname, atype, apos, anode

def get_slimes(root):
  "Get slimes within slime hutches"
  return ()

def get_obj_name(node):
  "Get an object's name"
  if xmltools.nodeHasChild(node, "name", ignorecase=True):
    cnode = xmltools.getNodeChild(node, "name", ignorecase=True)
    return xmltools.getNodeText(cnode)
  if node.hasAttribute("xsi:type"):
    return node.getAttribute("xsi:type")
  return None

def get_obj_type(node):
  "Get an object's type (category)"
  if xmltools.nodeHasChild(node, "type"):
    return xmltools.getNodeText(xmltools.getNodeChild(node, "type"))
  return get_obj_name(node)

def obj_get_map(node):
  "Get the map location containing the given object"
  pnode = node.parentNode
  while pnode:
    if pnode.tagName == "GameLocation":
      return get_obj_name(pnode)
    pnode = pnode.parentNode
  return None

def is_crop(node):
  "True if the node is a non-empty HoeDirt"
  if get_obj_type(node) == "HoeDirt":
    if xmltools.nodeHasChild(node, "crop"):
      cnode = xmltools.descend(node, "crop/seedIndex")
      if cnode and xmltools.getNodeText(cnode) != "-1":
        return True
  return False

def aggregate_objects(objlist):
  "Aggregate an interable of 4-tuples"
  bymap = collections.defaultdict(dict)
  for objdef in objlist:
    mcount = bymap[objdef.map].get(objdef.name, 0)
    bymap[objdef.map][objdef.name] = mcount + 1
  return bymap

def node_to_dict(objnode, formatters=None):
  "Convert an XML node to a Python dictionary (crudely)"
  filter_false = formatters and "false" in formatters
  filter_zero = formatters and "zero" in formatters
  filter_points = formatters and "points" in formatters

  def transform_func(node):
    "Apply a transformation on a single node"
    if filter_points:
      if is_coord_node(node):
        return node_to_coord(node)
    return None

  def map_func(key, value):
    orig_val = value

    # booleans, numbers
    if isinstance(value, str):
      if value in ("true", "false"):
        value = (value == "true")
      elif isdigit(value):
        value = int(value)
      elif isnumber(value):
        value = float(value)

    # pairs of numbers
    if isinstance(value, (list, tuple)) \
        and len(value) == 2 \
        and isdigit(value[0]) and isdigit(value[1]):
      value = (int(value[0]), int(value[1]))

    if filter_false:
      if value is False:
        logger.debug("Filtering out False key %s (val %r)", key, orig_val)
        return None
      if isinstance(value, (dict, list, tuple)) and not value:
        logger.debug("Filtering out empty key %s (val %r)", key, orig_val)
        return None
    if filter_zero and value == 0:
      logger.debug("Filtering out zero key %s (val %r)", key, orig_val)
      return None
    return value

  return xmltools.dumpNodeRec(objnode,
      mapFunc=map_func,
      xformFunc=transform_func)

def node_to_json(objnode, formatters=None):
  "Convert an XML node to JSON (crudely)"
  data = node_to_dict(objnode, formatters=formatters)
  return json.dumps(data, indent=2, sort_keys=True)

def crop_get_seed(node, name=False):
  "Get the crop's seed ID. Returns the name instead if name is True"
  cnode = xmltools.descend(node, "crop/seedIndex")
  if cnode is not None:
    cropid = xmltools.getNodeText(cnode)
    if name:
      return stardew.get_object(cropid, field=D.NAME)
    return cropid
  return None

def crop_get_produce(node, name=False):
  "Get the crop's produce by item ID or name"
  cnode = xmltools.descend(node, "crop/indexOfHarvest")
  if cnode is not None:
    produce = xmltools.getNodeText(cnode)
    if name:
      return stardew.get_object(produce, field=D.NAME)
    return produce
  return None

def crop_is_ready(node):
  "True if the crop is ready for harvest"
  phase_days = list(xmltools.descendAll(node, "crop/phaseDays/int"))
  phase_node = xmltools.descend(node, "crop/currentPhase")
  if phase_days and phase_node:
    phase = xmltools.getNodeText(phase_node)
    if isdigit(phase):
      if int(phase) >= len(phase_days) - 1:
        return True
  return False

def crop_is_dead(node):
  "True if the crop is dead"
  cnode = xmltools.descend(node, "crop/dead")
  if cnode is not None:
    dead = xmltools.getNodeText(cnode)
    if dead == "true":
      return True
    return False
  return None

def feature_get_fertilizer(node, name=False):
  "Get the fertilizer ID or name"
  if xmltools.nodeHasChild(node, "fertilizer"):
    cnode = xmltools.getNodeChild(node, "fertilizer")
    if xmltools.isTextNode(cnode):
      fertid = xmltools.getNodeText(cnode)
      if name:
        return stardew.get_object(fertid, field=D.NAME)
      return fertid
  return None

def print_crop(objdef, crop_level=CROP_BRIEF):
  "Print a 4-tuple object representing a crop"
  feature = node_to_dict(objdef.node)
  if "TerrainFeature" in feature:
    feature = feature["TerrainFeature"]
  else:
    logger.error("Malformed feature %r; trying to recover...", feature)
  crop = feature["crop"]
  cropname = stardew.get_object(crop["seedIndex"], field=D.NAME)
  fertilizer = feature["fertilizer"]

  logger.trace(feature)

  labels = [] # colored strings, joined by spaces
  notes = []  # uncolored strings, joined by semicolons

  if crop.get("dead"):
    labels.append(C(C.BRN, "dead"))
  if crop.get("fullGrown"):
    labels.append(C(C.GRN, C.BOLD, "ready"))

  if crop_level >= CROP_NORMAL:
    if fertilizer == 0:
      labels.append(C(C.RED, "unfertilized"))

  # TODO: color appropriately
  if crop_level >= CROP_LONG:
    if fertilizer > 0:
      labels.append(C(C.ITAL, stardew.get_object(fertilizer, field=D.NAME)))
    if crop.get("seasonsToGrowIn"):
      seasons = crop["seasonsToGrowIn"]
      seasons = seasons.get("string", seasons)
      notes.append(f"{seasons}")
    if crop["forageCrop"]:
      notes.append("forage")
    if crop["regrowAfterHarvest"] > 0:
      notes.append("regrows")
    if crop["chanceForExtraCrops"] > 0:
      chance = crop["chanceForExtraCrops"] * 100
      notes.append(f"extra={chance}%")

  # TODO: color appropriately
  if crop_level >= CROP_FULL:
    phase = int(crop["currentPhase"])
    phase_day = crop.get("dayOfCurrentPhase", "?")
    min_harvest = int(crop["minHarvest"])
    max_harvest = int(crop["maxHarvest"])
    notes.append(f"phase={phase} day={phase_day}")
    if min_harvest == max_harvest:
      notes.append(f"yield={min_harvest}")
    elif min_harvest and max_harvest:
      notes.append(f"yield={min_harvest} to {max_harvest}")

  print("{} {} at ({}, {}) {} {}".format(
    C(C.GRN, objdef.map),
    C(C.CYN, C.BOLD, cropname),
    C(C.BOLD, f"{objdef.pos[0]}"),
    C(C.BOLD, f"{objdef.pos[1]}"),
    " ".join(labels),
    "; ".join(notes)).replace("  ", " ").strip())

def print_animal(objdef): # TODO: formatting arguments
  "Print an animal"
  objkind = objdef.kind
  mapname = objdef.map
  objname = objdef.name
  objpos = objdef.pos
  objnode = objdef.node

  aname = xmltools.getChildText(objnode, "name")
  age = xmltools.getChildText(objnode, "age")
  love = xmltools.getChildText(objnode, "friendshipTowardFarmer")
  joy = xmltools.getChildText(objnode, "happiness")

  print("{} {} \"{}\" at ({}, {}) {}y {}m love {} joy {}".format(
    C(C.GRN, mapname),
    C(C.CYN, C.BOLD, objname),
    C(C.CYN, C.BOLD, C.ITAL, aname),
    C(C.BOLD, f"{objpos[0]}"),
    C(C.BOLD, f"{objpos[1]}"),
    C(C.BLU_B, C.BOLD, f"{int(age)//12}"),
    C(C.BLU_B, C.BOLD, f"{int(age)%12}"),
    C(C.CYN, C.BOLD, love),
    C(C.CYN, C.BOLD, joy)
  ))

def print_object(objdef, long=False, formatters=None, crop_level=CROP_BRIEF):
  "Print an arbitrary map thing"
  objkind = objdef.kind
  mapname = objdef.map
  objname = objdef.name
  objpos = objdef.pos
  objnode = objdef.node

  if long:
    print(node_to_json(objnode, formatters=formatters))
  elif objkind == MAP_CROPS and is_crop(objnode):
    print_crop(objdef, crop_level=crop_level)
  elif objkind == MAP_TREES:
    pass
  elif objkind == MAP_FRUIT_TREES:
    pass
  elif objkind == MAP_ANIMALS:
    print_animal(objdef)
  elif objkind == MAP_SLIMES:
    pass
  else:
    # TODO: add HoeDirt output (for fertilizer-no-crop)
    mapname = C(C.GRN, mapname)
    objname = C(C.CYN, C.BOLD, objname)
    objx = C(C.BOLD, f"{objpos[0]}")
    objy = C(C.BOLD, f"{objpos[1]}")
    print("{} {} at ({}, {})".format(mapname, objname, objx, objy))

def matches(seq, term):
  "True if seq includes term, False if seq forbids term, None otherwise"
  match = None
  if not term or not seq:
    return None
  for item in seq:
    if item.startswith("!") and fnmatch.fnmatch(term, item[1:]):
      match = False
    elif not item.startswith("!") and fnmatch.fnmatch(term, item):
      match = True
  return match

def matches_map(mapnames, mapname):
  "True if the map is included False if forbidden, None otherwise"
  if not mapname or not mapnames:
    return None
  has_neg = any(x.startswith("!") for x in mapnames)
  has_pos = any(not x.startswith("!") for x in mapnames)
  match = matches(mapnames, mapname)
  # exclusive logic changes what None maps to
  if match is None:
    if has_neg and not has_pos:
      match = True
    elif has_pos and not has_neg:
      match = False
  return match

def get_map_things(root, things):
  "Get the requested content; used by get_all_objects"
  show_objs = MAP_OBJECTS in things
  show_crops = MAP_CROPS in things
  show_small = MAP_FEATS_SMALL in things
  show_large = MAP_FEATS_LARGE in things
  show_trees = MAP_TREES in things
  show_fruit_trees = MAP_FRUIT_TREES in things
  show_animals = MAP_ANIMALS in things
  show_slimes = MAP_SLIMES in things

  if show_objs:
    logger.debug("Selecting objects")
    for mname, oname, opos, obj in get_objects(root):
      yield MAP_OBJECTS, mname, oname, opos, obj

  if show_crops or show_small:
    name = "crops" if show_crops else "small features"
    logger.debug("Selecting %s", name)
    for mname, oname, opos, obj in get_features(root, large=False):
      if show_crops and is_crop(obj):
        yield MAP_CROPS, mname, oname, opos, obj
      if show_small:
        yield MAP_FEATS_SMALL, mname, oname, opos, obj

  if show_large:
    logger.debug("Selecting large features")
    for mname, oname, opos, obj in get_features(root, large=True):
      yield MAP_FEATS_LARGE, mname, oname, opos, obj

  if show_trees or show_fruit_trees:
    logger.error("Not implemented yet")

  if show_animals:
    for mname, oname, opos, obj in get_animals(root):
      logger.debug("Found animal %s %s %s %s", mname, oname, opos, obj)
      yield MAP_ANIMALS, mname, oname, opos, obj

  if show_slimes:
    logger.error("Not implemented yet")

def get_all_objects(root, mapnames, objnames, objtypes, objcats, kinds):
  "Get all objects (as 4-tuples) matching any of the given conditions"

  def update_show(new_show, curr_show):
    "Update the show value, honoring False precedence"
    if curr_show is None:
      return new_show
    if new_show is None:
      return curr_show
    if curr_show is False or new_show is False:
      return False
    return curr_show or new_show

  def test_show(seq, term, curr_show):
    "Determine if we should show the object"
    new_show = None
    if term is not None:
      mat = matches(seq, term)
      if mat is not None:
        new_show = True
    return update_show(new_show, curr_show)

  things = kinds.split("+")
  for kind, mname, oname, opos, obj in get_map_things(root, things):
    show = None # tri-bool: False, unset, True

    # maps are exclusive and require special logic
    if mapnames and matches_map(mapnames, mname) is False:
      show = False

    # everything else is inclusive
    if objnames or objtypes or objcats:
      show = test_show(objnames, oname, show)
      show = test_show(objtypes, get_obj_type(obj), show)
      if kind == MAP_OBJECTS:
        if matches(objcats, "artifact") and oname in stardew.ARTIFACT:
          show = update_show(True, show)
        elif matches(objcats, "forage") and oname in stardew.FORAGE:
          show = update_show(True, show)
      elif kind == MAP_CROPS:
        show = test_show(objnames, crop_get_seed(obj, name=True), show)
        if matches(objcats, "cropready") and crop_is_ready(obj):
          show = update_show(True, show)
        if matches(objcats, "cropdead") and crop_is_dead(obj):
          show = update_show(True, show)
        if matches(objcats, "nofert") and feature_get_fertilizer(obj) is None:
          show = update_show(True, show)
        # TODO: produce filtering
        # TODO: fertilizer filtering
      elif kind == MAP_FEATS_SMALL:
        if matches(objcats, "fertnocrop") and oname == "HoeDirt":
          if not is_crop(obj) and feature_get_fertilizer(obj) != "0":
            show = update_show(True, show)
      elif kind == MAP_FEATS_LARGE:
        pass # TODO: filtering
      elif kind == MAP_TREES:
        pass # TODO: filtering
      elif kind == MAP_FRUIT_TREES:
        pass # TODO: filtering
      elif kind == MAP_ANIMALS:
        pass # TODO: filtering
      elif kind == MAP_SLIMES:
        pass # TODO: filtering
    elif show is None:
      # no specifications matches everything
      show = True

    if show is True:
      yield MapEntry(kind, mname, oname, opos, obj)

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

def _deduce_feature_kinds(includes, categories):
  "Deduce what kinds of things the user wants to examine"
  kinds = set()
  if includes:
    for want_kind in includes:
      kinds.update(MAP_ITEM_TYPES[want_kind].split("+"))
  if categories:
    if "forage" in categories and MAP_OBJECTS not in kinds:
      kinds.add(MAP_OBJECTS)
    if "artifact" in categories and MAP_OBJECTS not in kinds:
      kinds.add(MAP_OBJECTS)
    if "cropready" in categories and MAP_CROPS not in kinds:
      kinds.add(MAP_CROPS)
    if "cropdead" in categories and MAP_CROPS not in kinds:
      kinds.add(MAP_CROPS)
    if "nofert" in categories and MAP_CROPS not in kinds:
      kinds.add(MAP_CROPS)
    if "fertnocrop" in categories and MAP_FEATS_SMALL not in kinds:
      kinds.add(MAP_FEATS_SMALL)
  if not kinds:
    # default to objects
    kinds.add(MAP_OBJECTS)
  return "+".join(kinds)

def _print_saves(savepath):
  "Print a list of available saves"
  for svname in os.listdir(savepath):
    svpath = os.path.join(savepath, svname)
    if is_farm_save(svpath):
      print(svpath)

def _print_counts(objs, maps, sort):
  "Print aggregate counts"
  # TODO: process crops as crops, not as terrain features
  prefix = "anywhere"
  if maps:
    prefix = "+".join(maps)
  for objname, objcount in get_object_counts(objs, sort=sort):
    prefix = C(C.GRN, prefix)
    objname = C(C.CYN, objname)
    print("{} {} {}".format(prefix, objname, objcount))

def _print_objects(objs, sort, long, formatters, level):
  "Print the selected objects"
  if sort:
    def sort_key(odef):
      return (odef.map, odef.name, odef.pos)
    objs.sort(key=sort_key)
  for objdef in objs:
    print_object(objdef, long=long, formatters=formatters, crop_level=level)

class ArgFormatter(argparse.RawDescriptionHelpFormatter):
  "Replacement argparse formatter class"

  def is_append_action(self, action): # pylint: disable=no-self-use
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
You can specify which save to process by one of the following:
  1) The farm's name
  2) The farm's name and ID (the name of the save file)
  3) Path to the farm's save directory
  4) Path to the farm's save file
Use --list to enumerate the available saves.

The following arguments can be specified multiple times:
  -n,--name  -m,--map  -t,--type  -i,--include  -C,--category  -F,--formatter

The following arguments support negation by prefixing the value with '!':
  -n,--name  -m,--map  -t,--type

The following arguments support simple glob patterns using fnmatch:
  -n,--name  -m,--map  -t,--type

Note that order matters for -n, -m, and -t! If multiple values apply, the last
value will have the final say. For instance,
  -m 'Island*' -m '!IslandWest' means "entire island except farm"
  -m '!Island*' -m 'IslandWest' means "none of the island except farm"

-i,--include accepts the following values:
  objects     objects (forage, artifact spots, placed things)
  crops       hoe dirt with a crop
  small       small terrain features (trees, hoe dirt, flooring, fruit trees)
  large       large terrain features (bushes)
  trees       normal (not fruit) trees
  fruittrees  fruit trees
  alltrees    both normal and fruit trees
  animals     livestock: cows, pigs, goats, etc
  slimes      slimes within a slime hutch
  features    both small and large terrain features
  all         objects, crops, and terrain features

-C,--category acts as a filter and accepts the following values:
  forage      forageables
  artifact    artifact spots (equivalent to -n "Artifact Spot")
  cropready   (with -i crops) list only the crops that are ready
  cropdead    (with -i crops) list only the crops that are dead
  nofert      (with -i crops) list crops without fertilizer
  fertnocrop  (with -i small, -i features) list fertilized HoeDirt with no crop

Note that -C,--category can be specified without -i,--include:
  forage      implies -i objects
  artifact    implies -i objects
  cropready   implies -i crops
  cropdead    implies -i crops
  nofert      implies -i crops
  fertnocrop  implies -i small

-F,--formatter applies transformation to the output of -L,--long:
  false       omit elements with value "false"
  zero        omit elements with value "0"
  points      transform "X", "Y" to pairs of numbers

--crop-level expects a number between {B} and {F} inclusive:
  {B}           include dead and ready
  {N}           include crop seasons
  {L}           include crop forage and fertilizer
  {F}           include crop phase, yield, and harvest count

Pass -v once for verbose logging or twice (or -vv) for trace logging.
""".format(B=CROP_BRIEF, N=CROP_NORMAL, L=CROP_LONG, F=CROP_FULL),
      formatter_class=ArgFormatter)

  ag = ap.add_argument_group("farm selection")
  ag.add_argument("farm", nargs="?", help="farm name (see below)")
  ag.add_argument("--list", action="store_true",
      help="list available save files")
  ag.add_argument("-P", "--save-path", default=SVPATH, metavar="PATH",
      help="path to saves")

  ag = ap.add_argument_group("object enumeration")
  ag.add_argument("-i", "--include", action="append", metavar="INCLUDE",
      choices=MAP_ITEM_TYPES.keys(), dest="includes",
      help="things to display")
  ag.add_argument("-n", "--name", action="append", metavar="NAME",
      dest="names",
      help="select objects based on name")

  ag = ap.add_argument_group("output configuration")
  ag.add_argument("-c", "--count", action="store_true",
      help="show aggregate information about object counts")
  ag.add_argument("-s", "--sort", action="store_true",
      help="sort output where possible")
  ag.add_argument("-l", "--crop-level", choices=CROP_LEVELS.keys(),
      help="amount of crop information to display")

  ag = ap.add_argument_group("output filtering")
  ag.add_argument("-m", "--map", action="append", metavar="MAP",
      dest="maps",
      help="limit output to items within specific map(s)")
  ag.add_argument("-t", "--type", action="append", metavar="TYPE",
      dest="types",
      help="limit objects to those with a specific <type></type> value")
  ag.add_argument("-C", "--category", action="append", metavar="CATEGORY",
      choices=CATEGORIES, dest="categories",
      help="categories of objects to show")

  ag = ap.add_argument_group("detailed output configuration")
  ag.add_argument("-L", "--long", action="store_true",
      help="display detailed long-form object information")
  ag.add_argument("-F", "--formatter", action="append", metavar="FORMATTER",
      choices=FORMATTERS, dest="formatters",
      help="apply specific formatter(s) on long-form output")

  ag = ap.add_argument_group("logging and diagnostics")
  ag.add_argument("--no-color", action="store_true",
      help="disable color output")
  mg = ag.add_mutually_exclusive_group()
  mg.add_argument("-v", "--verbose", action="count", default=0,
      help="-v for verbose output, -vv for trace output")

  args = ap.parse_args()
  if args.verbose == 1:
    logger.setLevel(logging.DEBUG)
    xmltools.getLogger().setLevel(logging.DEBUG)
  elif args.verbose >= 2:
    logger.setLevel(utility.tracelog.TRACE)
    xmltools.getLogger().setLevel(utility.tracelog.TRACE)
  if args.no_color:
    C.disable()

  if args.farm:
    savepath = deduce_save_file(args.farm, svpath=args.save_path)
    if not savepath or not os.path.exists(savepath):
      ap.error("Failed to find farm matching {!r}".format(args.farm))
  else:
    if args.list:
      _print_saves(args.save_path)
    else:
      sys.stderr.write("No farm specified; see --help for usage\n")
    raise SystemExit(0)

  root = load_save_file(savepath)

  objs = list(get_all_objects(root,
    mapnames=args.maps,
    objnames=args.names,
    objtypes=args.types,
    objcats=args.categories,
    kinds=_deduce_feature_kinds(args.includes, args.categories)))

  if args.count:
    _print_counts(objs, args.maps, args.sort)
  else:
    crop_level = CROP_BRIEF
    if args.crop_level:
      crop_level = CROP_LEVELS.get(args.crop_level)
    _print_objects(objs, args.sort, args.long, args.formatters, crop_level)

if __name__ == "__main__":
  main()

# vim: set ts=2 sts=2 sw=2:
