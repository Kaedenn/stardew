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
import re
import sys
import textwrap
import xml.dom.minidom as minidom

from utility.colorterm import ColorFormatter as C
import stardew
from stardew import Data as D
import xmltools

import utility.tracelog

SVPATH = os.path.join(stardew.get_game_dir(), "Saves")

MAP_OBJECTS = "objects"
MAP_FEATS_SMALL = "small"
MAP_FEATS_LARGE = "large"
MAP_CROPS = "crops"
MAP_TREES = "trees"
MAP_FRUIT_TREES = "fruittrees"
MAP_ANIMALS = "animals"
MAP_SLIMES = "slimes"
MAP_MACHINES = "machines"
MAP_ITEM_TYPES = {
  MAP_OBJECTS: MAP_OBJECTS,
  MAP_FEATS_SMALL: MAP_FEATS_SMALL,
  MAP_FEATS_LARGE: MAP_FEATS_LARGE,
  MAP_CROPS: MAP_CROPS,
  MAP_TREES: MAP_TREES,
  MAP_FRUIT_TREES: MAP_FRUIT_TREES,
  MAP_ANIMALS: MAP_ANIMALS,
  MAP_SLIMES: MAP_SLIMES,
  MAP_MACHINES: MAP_MACHINES
}
MAP_ITEM_TYPES["all"] = "+".join(MAP_ITEM_TYPES.values())
MAP_ITEM_TYPES["alltrees"] = "+".join((MAP_TREES, MAP_FRUIT_TREES))
MAP_ITEM_TYPES["features"] = "+".join((MAP_FEATS_SMALL, MAP_FEATS_LARGE))

CAT_FORAGE = "forage"
CAT_ARTIFACT = "artifact"
CAT_CROPREADY = "cropready"
CAT_CROPDEAD = "cropdead"
CAT_NOFERT = "nofert"
CAT_FERTNOCROP = "fertnocrop"
CAT_READY = "ready"
CATEGORY_MAP = {
  CAT_FORAGE: MAP_OBJECTS,
  CAT_ARTIFACT: MAP_OBJECTS,
  CAT_CROPREADY: MAP_CROPS,
  CAT_CROPDEAD: MAP_CROPS,
  CAT_NOFERT: MAP_CROPS,
  CAT_FERTNOCROP: MAP_FEATS_SMALL,
  CAT_READY: MAP_MACHINES
}

# Omit the following machines
MACHINE_OMIT = (
  "Sprinkler",
  "Quality Sprinkler",
  "Iridium Sprinkler",
  "Wood Fence",
  "Stone Fence",
  "Iron Fence",
  "Hardwood Fence",
  "Worm Bin",
  "Coffee Maker",
  "Statue Of Endless Fortune",
  "Statue Of Perfection",
  "Statue Of True Perfection"
)

LEVEL_BRIEF = 0
LEVEL_NORMAL = 1
LEVEL_LONG = 2
LEVEL_FULL = 3
DATA_LEVELS = {
  "brief": LEVEL_BRIEF,
  "normal": LEVEL_NORMAL,
  "long": LEVEL_LONG,
  "full": LEVEL_FULL
}

# For long-form output
FORMATTERS = ("false", "zero", "points", "rawxml")

SEASON_COLORS = {
  stardew.Seasons.SPRING: (C.GRN_B, C.BOLD),
  stardew.Seasons.SUMMER: (C.YEL_B, C.BOLD),
  stardew.Seasons.FALL: (C.BRN, C.BOLD),
  stardew.Seasons.WINTER: (C.CYN_B, C.BOLD),
  stardew.Seasons.ISLAND: (C.YEL_B, C.BOLD)
}

QUALITY_COLORS = {
  stardew.Quality.NORMAL: (C.WHT, C.BOLD,),
  stardew.Quality.SILVER: (C.WHT_B, C.BOLD),
  stardew.Quality.GOLD: (C.YEL_B, C.BOLD),
  stardew.Quality.IRIDIUM: (C.MAG_B, C.BOLD)
}

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

  def disp_name(self):
    "What is this thing's display name?"
    if self.kind == MAP_CROPS:
      return crop_get_seed(self.node, name=True)
    return self.name

  def same_thing(self, other):
    "True if the two objects are the same kind of object"
    if self.kind == other.kind:
      if self.disp_name() == other.disp_name():
        return True
    return False

def isnumber(value):
  "True if value is an integer"
  try:
    int(value)
    return True
  except ValueError:
    return False

def isfloat(value):
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
  root = minidom.parse(open(svfile, "rt"))
  logger.debug("Loaded %s", svfile)
  return root

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
    xvalue = xmltools.getChildText(node, "X")
    yvalue = xmltools.getChildText(node, "Y")
    if isnumber(xvalue) and isnumber(yvalue):
      xvalue = int(xvalue)
      yvalue = int(yvalue)
    return xvalue, yvalue
  return None

def get_locations(root):
  "Get all map locations"
  for mnode in root.getElementsByTagName("GameLocation"):
    mapname = get_obj_name(mnode)
    if not mapname:
      mapname = stardew.LOC_UNKNOWN
    if mapname not in stardew.LOCATIONS:
      logger.warning("Unknown game location %s", mapname)
      logger.info("Please add modded locations to %s/locations.txt",
          stardew.DATA_PATH)
    yield mapname, mnode

def get_location(root, name):
  "Get a named location, for convenience"
  for lname, loc in get_locations(root):
    if lname == name:
      return loc
  logger.warning("Failed to find location named %r", name)
  return None

def map_get_features(mnode, large=False):
  """
  Get terrain features within a game location

  This considerably simplifies the get_features() logic
  """
  small_node = xmltools.getNodeChild(mnode, "terrainFeatures")
  for node in xmltools.getNodeChildren(small_node):
    if not is_nil_node(node):
      knode = xmltools.descend(node, "key/Vector2")
      fnode = xmltools.descend(node, "value/TerrainFeature")
      fname = get_obj_name(fnode)
      fpos = node_to_coord(knode)
      yield fname, fpos, fnode
  if large:
    large_node = xmltools.getNodeChild(mnode, "largeTerrainFeatures")
    for node in xmltools.getNodeChildren(large_node):
      fname = get_obj_name(node)
      fpos = node_to_coord(xmltools.descend(node, "tilePosition"))
      yield fname, fpos, node

def get_slime_hutches(root):
  "Get all slime hutch <indoors> nodes"
  for mname, mnode in get_locations(root):
    for bnode in xmltools.descendAll(mnode, "buildings/Building/indoors"):
      if get_obj_name(bnode) == "Slime Hutch":
        yield mname, bnode

def get_objects(root):
  "Get objects"
  for mapname, mnode in get_locations(root):
    for node in xmltools.descendAll(mnode, "objects/Object"):
      if not is_nil_node(node):
        oname = get_obj_name(node)
        objpos = node_to_coord(xmltools.getNodeChild(node, "tileLocation"))
        yield mapname, oname, objpos, node

def get_features(root, large=False):
  "Get terrain features, optionally including large features"
  for mapname, mnode in get_locations(root):
    for fname, fpos, node in map_get_features(mnode, large=large):
      yield mapname, fname, fpos, node

def get_trees(root, fruit=False):
  "Get trees (or fruit trees)"
  for mapname, fname, fpos, node in get_features(root, large=False):
    show = False
    if fname == "Tree" and not fruit:
      show = True
    elif fname == "FruitTree" and fruit:
      show = True
    if show:
      yield mapname, fname, fpos, node

def get_animals(root):
  "Get livestock"
  bpath = "buildings/Building/indoors"
  apath = "animals/item/value/FarmAnimal"
  # modding decision: allow buildings on maps other than Farm
  for mapname, mnode in get_locations(root):
    for bnode in xmltools.descendAll(mnode, bpath):
      btype = bnode.getAttribute("xsi:type")
      logger.debug("Examining building %s", btype)
      for anode in xmltools.descendAll(bnode, apath):
        atype = xmltools.getChildText(anode, "type")
        apos = node_to_coord(xmltools.getNodeChild(anode, "homeLocation"))
        yield mapname, atype, apos, anode

def get_slimes(root):
  "Get slimes within slime hutches"
  for mname, bnode in get_slime_hutches(root):
    for cnode in xmltools.descendAll(bnode, "characters/NPC"):
      tattr = get_type_attr(cnode)
      if tattr and "Slime" in tattr:
        objname = get_obj_name(cnode)
        objpos = node_to_coord(xmltools.getNodeChild(cnode, "Position"))
        yield mname, objname, objpos, cnode

def get_machines(root):
  "Get all machines with something inside them"
  for mapname, objname, objpos, node in get_objects(root):
    item = xmltools.getNodeChild(node, "heldObject")
    ison = xmltools.getChildText(node, "isOn")
    if objname in MACHINE_OMIT:
      continue
    if item is not None and ison == "true":
      yield mapname, objname, objpos, node

def get_type_attr(node):
  "Get the node's xsi:type attribute"
  if node.hasAttribute("xsi:type"):
    return node.getAttribute("xsi:type")
  return None

def get_obj_name(node):
  "Get an object's name, first by <name> or <Name>, then by xsi:type"
  name = xmltools.getChildText(node, "name", ignorecase=True)
  if name:
    return name
  return get_type_attr(node)

def get_obj_type(node):
  "Get an object's <type>"
  otype = xmltools.getChildText(node, "type")
  if otype:
    return otype
  return get_obj_name(node)

def obj_get_map(node):
  "Get the map location containing the given object"
  pnode = node.parentNode
  while pnode:
    if pnode.tagName == "GameLocation":
      return get_obj_name(pnode)
    pnode = pnode.parentNode
  return None

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
      elif isnumber(value):
        value = int(value)
      elif isfloat(value):
        value = float(value)

    # pairs of numbers
    if isinstance(value, (list, tuple)) \
        and len(value) == 2 \
        and isnumber(value[0]) and isnumber(value[1]):
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

def node_to_json(objnode, formatters=None, indent=None):
  "Convert an XML node to JSON (crudely)"
  data = node_to_dict(objnode, formatters=formatters)
  return json.dumps(data, indent=indent, sort_keys=True)

def is_crop(node):
  "True if the node is a non-empty HoeDirt"
  if get_type_attr(node) == "HoeDirt":
    if xmltools.nodeHasChild(node, "crop"):
      cnode = xmltools.descend(node, "crop/seedIndex")
      if cnode and xmltools.getNodeText(cnode) != "-1":
        return True
  return False

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
  if not phase_days: # for ginger
    return True
  if phase_node:
    phase = xmltools.getNodeText(phase_node)
    if isnumber(phase):
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
  "Get the feature's fertilizer ID or name, or None if it has none"
  fertid = xmltools.getChildText(node, "fertilizer")
  if fertid is not None:
    if fertid == "0":
      return None
    if name:
      return stardew.get_object(fertid, field=D.NAME)
    return fertid
  return None

def feature_fertilized(node):
  "True if the feature is a fertilized HoeDirt"
  fertid = feature_get_fertilizer(node)
  if fertid:
    return True
  return False

def machine_ready(node):
  "True if the machine is ready for harvest"
  ready = xmltools.getChildText(node, "readyForHarvest")
  if ready == "true":
    return True
  if ready == "false":
    return False
  item = xmltools.getNodeChild(node, "heldObject")
  if item is not None:
    nmins = xmltools.getChildText(node, "minutesUntilReady")
    imins = xmltools.getChildText(item, "minutesUntilReady")
    if nmins == "0" and imins == "0":
      return True
  return False

def build_object_long_xml(objdef):
  "Convert an object definition to XML (via -L,--long with -f rawxml)"
  root = minidom.Document()
  def add_text_node(parent, name, text):
    "Create a text node, an element to contain it, and add it to the parent"
    cnode = root.createElement(name)
    cnode.appendChild(root.createTextNode(text))
    parent.appendChild(cnode)
  top = root.createElement("MapEntry")
  root.appendChild(top)
  add_text_node(top, "Kind", objdef.kind)
  add_text_node(top, "MapName", objdef.map)
  locnode = root.createElement("Location")
  add_text_node(locnode, "X", f"{objdef.pos[0]}")
  add_text_node(locnode, "Y", f"{objdef.pos[1]}")
  top.appendChild(locnode)
  add_text_node(top, "Name", objdef.name)
  top.appendChild(objdef.node)
  return top

def print_object_long(objdef, formatters):
  "Print an object in long form (via -L,--long)"
  objnode = objdef.node

  as_xml = False
  indent = None
  if formatters:
    if "rawxml" in formatters:
      as_xml = True
    for rule in formatters:
      if rule.startswith("indent="):
        indent = rule[rule.index("=")+1:]
        if indent == "tab":
          indent = "\t"
        elif isnumber(indent):
          indent = " " * int(indent)

  if as_xml:
    obj = build_object_long_xml(objdef)
    if indent is None:
      objstr = obj.toxml().strip()
    else:
      objstr = obj.toprettyxml(indent=indent).strip()
  else:
    objstr = node_to_json(objnode, formatters=formatters, indent=indent)

  print(objstr)

def print_crop(objdef, data_level=LEVEL_BRIEF):
  "Print an object definition representing a HoeDirt feature with a crop"

  crop = xmltools.getNodeChild(objdef.node, "crop")
  fertid = feature_get_fertilizer(objdef.node)

  cropid = xmltools.getChildText(crop, "seedIndex")
  cropname = None
  if isnumber(cropid) and int(cropid) > 0:
    cropname = stardew.get_object(cropid, field=D.NAME)

  labels = [] # colored strings, joined by spaces
  notes = []  # uncolored strings, joined by semicolons

  if crop_is_dead(objdef.node):
    labels.append(C(C.BRN, "dead"))
  if crop_is_ready(objdef.node):
    labels.append(C(C.GRN, C.BOLD, "ready"))

  if data_level >= LEVEL_NORMAL:
    if not feature_fertilized(objdef.node):
      labels.append(C(C.RED, "unfertilized"))

  if data_level >= LEVEL_LONG:
    if fertid:
      fert = stardew.get_object(fertid, field=D.NAME)
      labels.append(C(C.ITAL, C.UND, fert))
    seasons = []
    for snode in xmltools.descendAll(crop, "seasonsToGrowIn/string"):
      stext = xmltools.getNodeText(snode)
      clr = SEASON_COLORS[stardew.Seasons(stext)]
      seasons.append(C(*clr, stext))
    if seasons:
      labels.append(", ".join(seasons))
    if xmltools.getChildText(crop, "forageCrop", to="bool"):
      notes.append("forage")
    regrow = xmltools.getChildText(crop, "regrowAfterHarvest")
    if isfloat(regrow) and int(regrow) > -1:
      notes.append(f"regrows={regrow}")
    extra_chance = xmltools.getChildText(crop, "chanceForExtraCrops")
    if isfloat(extra_chance) and float(extra_chance) > 0:
      notes.append(f"extra={float(extra_chance)*100}%")

  if data_level >= LEVEL_FULL:
    notes.append(f"fertid={fertid}")
    phases_nodes = list(xmltools.descendAll(crop, "phaseDays/int"))
    phases = [xmltools.getNodeText(n) for n in phases_nodes]
    phase = xmltools.getChildText(crop, "currentPhase", to=int)
    phase_day = xmltools.getChildText(crop, "dayOfCurrentPhase", to=int)
    min_harvest = xmltools.getChildText(crop, "minHarvest", to=int)
    max_harvest = xmltools.getChildText(crop, "maxHarvest", to=int)
    chance = xmltools.getChildText(crop, "chanceForExtraCrops")
    notes.append(f"phases=[{', '.join(phases)}]")
    notes.append(f"phase={phase}")
    notes.append(f"phase_day={phase_day}")
    if min_harvest != 1 or max_harvest != 1:
      if min_harvest != max_harvest:
        notes.append(f"min={min_harvest}")
        notes.append(f"max={max_harvest}")
      else:
        notes.append(f"count={min_harvest}")
    notes.append(f"extra-chance={chance}")

  print("{} {} at ({}, {}) {} {}".format(
    C(C.GRN, objdef.map),
    C(C.CYN, C.BOLD, cropname),
    C(C.BOLD, f"{objdef.pos[0]}"),
    C(C.BOLD, f"{objdef.pos[1]}"),
    " ".join(labels),
    "; ".join(notes)).replace("  ", " ").strip())

def print_animal(objdef, data_level=LEVEL_BRIEF):
  "Print an animal"
  mapname = objdef.map
  objname = objdef.name
  objpos = objdef.pos
  objnode = objdef.node

  aname = xmltools.getChildText(objnode, "name")
  age = xmltools.getChildText(objnode, "age")
  love = xmltools.getChildText(objnode, "friendshipTowardFarmer")
  joy = xmltools.getChildText(objnode, "happiness")

  if isnumber(age):
    age_ymd = stardew.format_days(int(age),
        yfmt=C(C.RED_B, C.BOLD, "{}") + C(C.RED, C.ITAL, "y"),
        mfmt=C(C.RED_B, C.BOLD, "{}") + C(C.RED, C.ITAL, "m"),
        dfmt=C(C.RED_B, C.BOLD, "{}") + C(C.RED, C.ITAL, "d"),
        sep=" ")
  else:
    age_ymd = f"{age}d"

  labels = []

  if data_level >= LEVEL_LONG:
    labels.append("at ({}, {})".format(
      C(C.BOLD, f"{objpos[0]}"),
      C(C.BOLD, f"{objpos[1]}")))

  fship = C(C.YEL_B, "friendship") + " " + C(C.YEL_B, C.BOLD, love)
  happy = C(C.GRN_B, "happiness") + " " + C(C.GRN_B, C.BOLD, joy)

  if LEVEL_NORMAL <= data_level < LEVEL_FULL:
    if isnumber(love) and int(love) == stardew.ANIMAL_FRIENDSHIP_MAX:
      fship = C(C.YEL_B, C.BOLD, "max friendship")
    if isnumber(joy) and int(joy) == stardew.ANIMAL_HAPPINESS_MAX:
      happy = C(C.GRN_B, C.BOLD, "max happiness")

  if data_level >= LEVEL_NORMAL:
    labels.append(fship)
    labels.append(happy)

  print("{} {} {} {} {}".format(
    C(C.GRN, mapname),
    C(C.CYN, C.BOLD, objname),
    C(C.CYN_B, C.BOLD, C.ITAL, aname),
    age_ymd,
    " ".join(labels)
  ).rstrip())

def print_tree(objdef, data_level=LEVEL_BRIEF): # TODO: reduce LEVEL_BRIEF noise
  "Print a tree"
  objkind = objdef.kind
  mapname = objdef.map
  objname = objdef.name
  objpos = objdef.pos
  objnode = objdef.node

  ttype = xmltools.getChildText(objnode, "treeType")
  stump = xmltools.getChildText(objnode, "stump")
  stage = xmltools.getChildText(objnode, "growthStage")
  health = xmltools.getChildText(objnode, "health")

  if objkind == MAP_FRUIT_TREES:
    objname = stardew.get_fruit_tree(ttype)
  else:
    objname = stardew.get_tree(ttype)

  labels = []
  if data_level >= LEVEL_LONG:
    labels.append("at ({}, {})".format(
      C(C.BOLD, f"{objpos[0]}"),
      C(C.BOLD, f"{objpos[1]}")))
    labels.append("type=" + C(C.BOLD, ttype))
  if stump == "true":
    labels.append(C(C.BRN, C.BOLD, "stump"))

  if isnumber(stage):
    stage_val = stardew.TreeStage.get(int(stage))
    if data_level >= LEVEL_LONG:
      labels.append(C(C.BLU_B, "stage=") + C(C.BLU_B, C.BOLD, stage))
    labels.append(C(C.CYN_B, C.BOLD, stage_val.name.title()))

  if data_level >= LEVEL_LONG:
    labels.append(C(C.RED_B, "health=") + C(C.RED_B, C.BOLD, health))

  if data_level >= LEVEL_NORMAL:
    tapped = xmltools.getChildText(objnode, "tapped")
    seed = xmltools.getChildText(objnode, "hasSeed")
    fertilized = xmltools.getChildText(objnode, "fertilized")
    if tapped == "true":
      labels.append(C(C.GRN, "tapped"))
    if seed == "true":
      labels.append(C(C.GRN_B, "has seed"))
    if fertilized == "true":
      labels.append(C(C.CYN_B, "fertilized"))

  mname = C(C.GRN, mapname)
  oname = C(C.CYN, C.BOLD, objname)

  print("{} {} {}".format(
    mname, oname, " ".join(labels)))

def print_fruit_tree(objdef, data_level=LEVEL_BRIEF):
  "Like print_tree, but print a fruit tree"
  mapname = objdef.map
  objname = objdef.name
  objpos = objdef.pos
  objnode = objdef.node

  ttype = xmltools.getChildText(objnode, "treeType")
  stump = xmltools.getChildText(objnode, "stump")
  stage = xmltools.getChildText(objnode, "growthStage")
  health = xmltools.getChildText(objnode, "health")

  objname = stardew.get_fruit_tree(ttype)

  labels = []
  if data_level >= LEVEL_LONG:
    labels.append("at ({}, {})".format(
      C(C.BOLD, f"{objpos[0]}"),
      C(C.BOLD, f"{objpos[1]}")))
    labels.append("type=" + C(C.BOLD, ttype))

  if stump == "true":
    labels.append(C(C.BRN, C.BOLD, "stump"))

  if isnumber(stage):
    # FIXME: get the correct names for the stages
    # fruit trees are grown at level 4
    stage_val = stardew.TreeStage.get(int(stage) + 1)
    if data_level >= LEVEL_LONG:
      labels.append(C(C.BLU_B, "stage=") + C(C.BLU_B, C.BOLD, stage))
    labels.append(C(C.CYN_B, C.BOLD, stage_val.name.lower()))

  if data_level >= LEVEL_LONG:
    labels.append(C(C.RED_B, "health=") + C(C.RED_B, C.BOLD, health))

  fruit_id = xmltools.getChildText(objnode, "indexOfFruit")
  fruit = stardew.get_object(fruit_id, field=D.NAME)

  greenhouse_tile = xmltools.getChildText(objnode, "greenHouseTileTree")
  greenhouse = xmltools.getChildText(objnode, "greenHouseTree")
  season = xmltools.getChildText(objnode, "fruitSeason")
  fruits = xmltools.getChildText(objnode, "fruitsOnTree")
  struck = xmltools.getChildText(objnode, "struckByLightningCountdown")
  days_until = xmltools.getChildText(objnode, "daysUntilMature")

  if data_level >= LEVEL_NORMAL:
    labels.append(C(*SEASON_COLORS[stardew.Seasons(season)], season))

  if data_level >= LEVEL_NORMAL:
    if isnumber(fruits) and int(fruits) > 0:
      labels.append(C(C.CYN, "fruits=") + C(C.CYN_B, C.BOLD, fruits))

  if data_level >= LEVEL_LONG:
    if fruit:
      labels.append(C(C.CYN, "fruit=") + C(C.CYN_B, fruit))
    if greenhouse == "true":
      labels.append(C(C.CYN, "greenhouse"))
    if greenhouse_tile == "true":
      labels.append(C(C.BLU, "greenhouse-tile"))

  if isnumber(struck) and int(struck) != 0:
    labels.append(C(C.BRN, "coal=") + C(C.BRN, struck))

  if isfloat(days_until):
    ndays = int(days_until)
    if ndays > 0:
      labels.append(" ".join((
        C(C.RED, "ready in"),
        C(C.RED_B, C.BOLD, days_until),
        C(C.RED, "days"))))
    else:
      quality = abs(ndays) // (stardew.DAYS_MONTH * stardew.MONTHS_YEAR)
      qval = stardew.Quality.get(quality)
      qstr = C(*QUALITY_COLORS[qval], qval.name.lower())
      labels.append(qstr)
      if data_level >= LEVEL_LONG:
        labels.append(stardew.format_days(abs(ndays),
          yfmt=C(C.RED_B, C.BOLD, "{}") + C(C.RED, C.ITAL, "y"),
          mfmt=C(C.RED_B, C.BOLD, "{}") + C(C.RED, C.ITAL, "m"),
          dfmt=C(C.RED_B, C.BOLD, "{}") + C(C.RED, C.ITAL, "d"),
          sep=" "))
      # TODO: display "<level> in <days>, at <date>"

  mname = C(C.GRN, mapname)
  oname = C(C.CYN, C.BOLD, objname)

  print("{} {} {}".format(
    mname, oname, " ".join(labels)))

def print_slime(objdef, data_level=LEVEL_BRIEF):
  "Print a slime object"
  mapname = objdef.map
  objname = objdef.name
  objpos = objdef.pos
  objnode = objdef.node

  health = xmltools.getChildText(objnode, "health")
  max_health = xmltools.getChildText(objnode, "maxHealth")
  exp = xmltools.getChildText(objnode, "experienceGained")
  cute = xmltools.getChildText(objnode, "cute")
  ready_to_mate = xmltools.getChildText(objnode, "readyToMate")

  mname = C(C.GRN, mapname)
  oname = C(C.CYN, C.BOLD, objname)
  objx = C(C.BOLD, f"{objpos[0]}")
  objy = C(C.BOLD, f"{objpos[1]}")

  labels = []
  if data_level >= LEVEL_LONG:
    labels.append(f"at ({objx}, {objy})")

  labels.append("HP={}/{}".format(C(C.RED_B, health), C(C.RED_B, max_health)))
  if cute == "true":
    labels.append(C(C.RED_B, "cute"))

  if data_level >= LEVEL_NORMAL:
    if isfloat(ready_to_mate) and ready_to_mate != "-1":
      labels.append("mate?=" + C(C.GRN_B, ready_to_mate))

  if data_level >= LEVEL_LONG:
    labels.append("exp=" + C(C.BOLD, exp))

  label = " ".join(labels)
  print("{} {} {}".format(mname, oname, label))

def print_machine(objdef, data_level=LEVEL_BRIEF):
  "Print a processing machine"
  mapname = objdef.map
  objname = objdef.disp_name()
  objpos = objdef.pos
  objnode = objdef.node

  labels = []

  held = xmltools.getNodeChild(objnode, "heldObject")
  hname = get_obj_name(held)
  if hname == "Chest":
    if data_level >= LEVEL_FULL:
      labels.append(C(C.BOLD, "container"))
    nitems = len(list(xmltools.descendAll(objnode, "items/Item")))
    if nitems == 0:
      labels.append(C(C.BLU_B, "empty"))
    else:
      suff = "item" if nitems == 1 else "items"
      labels.append(C(C.BLU_B, C.BOLD, f"{nitems}") + " " + C(C.BLU_B, suff))

  ready = xmltools.getChildText(objnode, "readyForHarvest")
  if ready == "true":
    labels.append(C(C.GRN_B, C.BOLD, "ready"))

  days = xmltools.getChildText(objnode, "daysToMature")
  minutes = xmltools.getChildText(objnode, "minutesUntilReady")
  if days is not None and isnumber(days) and int(days) > 0:
    # TODO: handle partial progress for casks
    labels.append(C(C.RED_B, "ready in"))
    labels.append(C(C.RED_B, C.BOLD, days))
    labels.append(C(C.RED_B, "days"))
  elif minutes is not None and isnumber(minutes) and int(minutes) > 0:
    ready_in = stardew.format_minutes(int(minutes), sep=" ")
    labels.append(C(C.RED_B, "ready in"))
    labels.append(C(C.RED_B, C.BOLD, ready_in))
    # TODO: exact time when ready

  if data_level >= LEVEL_FULL:
    labels.append(C(C.RED_B, "minutes=") + C(C.RED_B, C.BOLD, minutes))

  if data_level >= LEVEL_FULL:
    labels.append("("
        + C(C.BOLD, f"{objpos[0]}")
        + ", "
        + C(C.BOLD, f"{objpos[1]}")
        + ")")

  print("{} {} {} {}".format(
    C(C.GRN, mapname),
    C(C.CYN, C.BOLD, objname),
    C(C.CYN_B, hname),
    " ".join(labels)
  ))

def print_object(objdef, long=False, formatters=None, data_level=LEVEL_BRIEF):
  "Print an arbitrary map thing"
  objkind = objdef.kind
  mapname = objdef.map
  objname = objdef.name
  objpos = objdef.pos
  objnode = objdef.node

  if long:
    print_object_long(objdef, () if formatters is None else formatters)
  elif objkind == MAP_CROPS and is_crop(objnode):
    print_crop(objdef, data_level=data_level)
  elif objkind == MAP_TREES:
    print_tree(objdef, data_level=data_level)
  elif objkind == MAP_FRUIT_TREES:
    print_fruit_tree(objdef, data_level=data_level)
  elif objkind == MAP_ANIMALS:
    print_animal(objdef, data_level=data_level)
  elif objkind == MAP_SLIMES:
    print_slime(objdef, data_level=data_level)
  elif objkind == MAP_MACHINES:
    print_machine(objdef, data_level=data_level)
  else:
    # TODO: add HoeDirt output (for fertilizer-no-crop)
    mapname = C(C.GRN, mapname)
    objname = C(C.CYN, C.BOLD, objdef.disp_name())
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
  "True if the map is included, False if forbidden, None otherwise"
  if not mapname or not mapnames:
    return None
  has_neg = any(x.startswith("!") for x in mapnames)
  has_pos = any(not x.startswith("!") for x in mapnames)
  match = matches(mapnames, mapname)
  # exclusive logic just changes what None maps to
  if match is None:
    if has_neg and not has_pos:
      match = True
    elif has_pos and not has_neg:
      match = False
  return match

def get_map_things(root, things):
  "Get the requested content; used by filter_map_things"
  show_objs = MAP_OBJECTS in things
  show_crops = MAP_CROPS in things
  show_small = MAP_FEATS_SMALL in things
  show_large = MAP_FEATS_LARGE in things
  show_trees = MAP_TREES in things
  show_fruit_trees = MAP_FRUIT_TREES in things
  show_animals = MAP_ANIMALS in things
  show_slimes = MAP_SLIMES in things
  show_machines = MAP_MACHINES in things

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

  if show_trees:
    for mname, oname, opos, obj in get_trees(root, fruit=False):
      logger.debug("Found %s %s %s %s", mname, oname, opos, obj)
      yield MAP_TREES, mname, oname, opos, obj

  if show_fruit_trees:
    for mname, oname, opos, obj in get_trees(root, fruit=True):
      logger.debug("Found %s %s %s %s", mname, oname, opos, obj)
      yield MAP_FRUIT_TREES, mname, oname, opos, obj

  if show_animals:
    for mname, oname, opos, obj in get_animals(root):
      logger.debug("Found animal %s %s %s %s", mname, oname, opos, obj)
      yield MAP_ANIMALS, mname, oname, opos, obj

  if show_slimes:
    for mname, oname, opos, obj in get_slimes(root):
      logger.debug("Found slime %s %s %s %s", mname, oname, opos, obj)
      yield MAP_SLIMES, mname, oname, opos, obj

  if show_machines:
    for mname, oname, opos, obj in get_machines(root):
      logger.debug("Found machine %s %s %s %s", mname, oname, opos, obj)
      yield MAP_MACHINES, mname, oname, opos, obj

def filter_map_things(root, mapnames, objnames, objtypes, objcats, kinds):
  "Returns all map content (as MapEntry values) matching the given conditions"

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

  def wants(cat):
    "True if the user wants the category"
    return matches(objcats, cat)

  at_pos = None
  if objcats:
    for cat in objcats:
      if re.match("at=[0-9]+,[0-9]+", cat):
        xpos, ypos = cat.split("=", 1)[1].split(",")
        at_pos = (int(xpos), int(ypos))

  things = kinds.split("+")
  for kind, mname, oname, opos, obj in get_map_things(root, things):
    show = None # tri-bool: False, unset, True

    # maps are exclusive and require special logic
    if mapnames and matches_map(mapnames, mname) is False:
      show = False

    if at_pos:
      logger.trace("opos=%r at_pos=%r", opos, at_pos)
      if opos[0] != at_pos[0] or opos[1] != at_pos[1]:
        show = False

    # everything else is inclusive
    if objnames or objtypes or objcats:
      show = test_show(objnames, oname, show)
      show = test_show(objtypes, get_obj_type(obj), show)
      if kind == MAP_OBJECTS:
        if wants("artifact") and oname in stardew.ARTIFACT:
          show = update_show(True, show)
        elif wants("forage") and oname in stardew.FORAGE:
          show = update_show(True, show)
      elif kind == MAP_CROPS:
        seed = crop_get_seed(obj, name=True)
        show = test_show(objnames, seed, show)
        if wants("cropready") and crop_is_ready(obj):
          show = update_show(True, show)
        if wants("cropdead") and crop_is_dead(obj):
          show = update_show(True, show)
        if wants("nofert") and feature_get_fertilizer(obj) is None:
          show = update_show(True, show)
        # TODO: produce filtering
        # TODO: fertilizer filtering
      elif kind == MAP_FEATS_SMALL:
        if wants("fertnocrop") and oname == "HoeDirt":
          if not is_crop(obj) and feature_fertilized(obj):
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
      elif kind == MAP_MACHINES:
        if wants("ready") and machine_ready(obj):
          show = update_show(True, show)
    elif show is None:
      # no specifications matches everything
      show = True

    if show is True:
      logger.debug("Showing %s %s %s %s", kind, mname, oname, opos)
      yield MapEntry(kind, mname, oname, opos, obj)

def aggregate_map_things(objs, maps=()):
  "Aggregate map entries by map, optionally restricting the maps processed"
  bykey = collections.defaultdict(list)
  bymap = collections.defaultdict(dict)
  for objdef in objs:
    objmap = objdef.map
    objkey = "{}-{}".format(objdef.kind, objdef.disp_name())
    bykey[objkey].append(objdef)
    ocount = bymap[objmap].get(objkey, 0)
    bymap[objmap][objkey] = ocount + 1

  byname = collections.defaultdict(int)
  for mapname, objnames in bymap.items():
    if not maps or matches(maps, mapname):
      for objname, objcount in objnames.items():
        byname[objname] += objcount

  bykey = dict(bykey)
  bymap = dict(bymap)

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

  entries = sorted(byname.items(), key=entry_sort_key)

  # Transform back to MapEntry values
  for name, _ in entries:
    yield bykey[name]

def _deduce_feature_kinds(includes, categories):
  "Deduce what kinds of things the user wants to examine"
  kinds = set()
  if includes:
    for want_kind in includes:
      kinds.update(MAP_ITEM_TYPES[want_kind].split("+"))
  if categories:
    for catval in categories:
      typeval = CATEGORY_MAP.get(catval)
      if typeval is not None and typeval not in kinds:
        kinds.add(typeval)
  if not kinds:
    # default to objects
    kinds.add(MAP_OBJECTS)
  return "+".join(kinds)

def _main_print_saves(savepath):
  "Print a list of available saves"
  for svname in os.listdir(savepath):
    svpath = os.path.join(savepath, svname)
    if is_farm_save(svpath):
      print(svpath)

def _main_print_counts(objs, maps):
  "Print aggregate counts"
  prefix = C(C.GRN, C.ITAL, "anywhere")
  if maps:
    prefix = ", ".join(C(C.GRN, m) for m in maps)

  for values in aggregate_map_things(objs, maps=maps):
    objcount = len(values)
    objname = values[0].disp_name()
    print("{} {} {}".format(prefix, C(C.CYN, objname), objcount))

def _main_print_objects(objs, sort, long, formatters, level):
  "Print the selected objects"
  if sort:
    def sort_key(odef):
      return (odef.map, odef.disp_name(), odef.name, odef.pos)
    objs.sort(key=sort_key)
  for objdef in objs:
    print_object(objdef, long=long, formatters=formatters, data_level=level)

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
  ap = argparse.ArgumentParser(epilog=textwrap.dedent("""
  You can specify which save to process by one of the following:
    1) The farm's name
    2) The farm's name and ID (the name of the save file)
    3) Path to the farm's save directory
    4) Path to the farm's save file
  Use --list to enumerate the available saves. Use -P,--save-path to specify a
  different save directory.

  Arguments labelled (multi) can be specified more than once.

  The following arguments support negation by prefixing the value with '!' and
  simple glob patterns using fnmatch:
    -n,--name  -m,--map  -t,--type
  For example,
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
    machines    processing machines
    features    both small and large terrain features
    all         everything listed above

  -C,--category acts as a filter and accepts the following values:
    forage      forageables
    artifact    artifact spots (equivalent to -n "Artifact Spot")
    cropready   list only the crops that are ready for harvest
    cropdead    list only the crops that are dead
    nofert      list crops without fertilizer
    fertnocrop  list fertilized HoeDirt with no crop
    ready       list only machines that are ready

  Note that -C,--category can be specified without -i,--include:
    forage      implies -i objects
    artifact    implies -i objects
    cropready   implies -i crops
    cropdead    implies -i crops
    nofert      implies -i crops
    fertnocrop  implies -i small
    ready       implies -i objects

  -F,--formatter applies transformation to the output of -L,--long:
    false       omit elements with value "false"
    zero        omit elements with value "0"
    points      transform "X", "Y" to pairs of numbers

  Pass -v once for verbose logging or twice (or -vv) for trace logging.
  """).format(B=LEVEL_BRIEF, N=LEVEL_NORMAL, L=LEVEL_LONG, F=LEVEL_FULL),
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
      help="things to display (see -h,--help for list)")
  ag.add_argument("-n", "--name", action="append", metavar="NAME",
      dest="names",
      help="select objects based on name")

  ag = ap.add_argument_group("output configuration")
  ag.add_argument("-c", "--count", action="store_true",
      help="show aggregate information about object counts")
  ag.add_argument("-s", "--sort", action="store_true",
      help="sort output where possible")
  ag.add_argument("-l", "--data-level", choices=DATA_LEVELS.keys(),
      default="normal",
      help="amount of crop information to display (see -h,--help for list)")
  ag.add_argument("--no-color", action="store_true",
      help="disable color output")

  ag = ap.add_argument_group("output filtering")
  ag.add_argument("-m", "--map", action="append", metavar="MAP",
      dest="maps",
      help="limit output to items within specific map(s)")
  ag.add_argument("-t", "--type", action="append", metavar="TYPE",
      dest="types",
      help="limit objects to those with a specific <type></type> value")
  ag.add_argument("-C", "--category", action="append", metavar="CATEGORY",
      choices=CATEGORY_MAP.keys(), dest="categories",
      help="categories of objects to show")
  ag.add_argument("--at-pos", action="append", metavar="X,Y",
      help="select things at the given tile position")

  ag = ap.add_argument_group("detailed output configuration")
  ag.add_argument("-L", "--long", action="store_true",
      help="display detailed long-form object information")
  ag.add_argument("-F", "--formatter", action="append", metavar="FORMATTER",
      choices=FORMATTERS, dest="formatters",
      help="apply formatter(s) on long-form output")
  ag.add_argument("--indent", metavar="NUM",
      help="number of spaces or the word 'tab'")

  ag = ap.add_argument_group("logging and diagnostics")
  mg = ag.add_mutually_exclusive_group()
  mg.add_argument("-v", "--verbose", action="count",
      help="-v for verbose output, -vv for trace output")

  args = ap.parse_args()
  if args.verbose is not None:
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
      _main_print_saves(args.save_path)
    else:
      sys.stderr.write("No farm specified; see -h,--help for usage\n")
    raise SystemExit(0)

  root = load_save_file(savepath)

  objcats = args.categories if args.categories else []
  if args.at_pos:
    for pos in args.at_pos:
      objcats.append(f"at={pos}")

  objs = list(filter_map_things(root,
    mapnames=args.maps,
    objnames=args.names,
    objtypes=args.types,
    objcats=objcats,
    kinds=_deduce_feature_kinds(args.includes, args.categories)))

  if args.count:
    _main_print_counts(objs, args.maps)
  else:
    formatters = args.formatters if args.formatters else []
    if args.indent:
      formatters.append(f"indent={args.indent}")
    data_level = DATA_LEVELS[args.data_level]
    _main_print_objects(objs, args.sort, args.long, formatters, data_level)

if __name__ == "__main__":
  main()

# vim: set ts=2 sts=2 sw=2:
