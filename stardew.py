#!/usr/bin/env python3

"""
Constants and functions related to Stardew Valley game data

This module provides access to the several names, locations, and objects
defined in the game. Exported identifiers include the following:

NPCS            tuple containing names of all NPCs
LOCATIONS       tuple containing names of all locations
OBJECTS_RAW     dict of object ID to object data string (see data/objects.json)
OBJECTS         dict of object ID to object definition (see help(stardew.Data))
FORAGE          tuple containing names of all forage objects
FORAGE_<set>    tuple containing names of the particular forage set

To add modded NPCs, either add their names to data/npcs.txt or create a new
file in the data directory with NPC names, one per line, and call
  stardew.load_npcs(your_filename)

To add modded locations, follow the above steps for data/locations.txt or call
  stardew.load_locations(your_filename)

To add modded objects, either update data/objects.json or create a new JSON
file with object ID keys and object definition string values, and call
  stardew.load_objects(your_filename)

You do not need to call the load_* functions if you edit existing data files.
"""

import enum
import json
import os
import platform

# Path to this script's data files
DATA_PATH = "data"

DAYS_MONTH = 28
MONTHS_YEAR = 4

NPC_UNKNOWN = "<unknown>"     # "undetermined NPC" literal
LOC_UNKNOWN = "<unknown>"     # "undetermined location" literal
ARTIFACT = ("Artifact Spot",) # objects satisfying the "artifact" category

ANIMAL_FRIENDSHIP_MAX = 1000
ANIMAL_HAPPINESS_MAX = 255

def get_game_dir():
  "Get the path to the game's data directory (containing the Saves directory)"
  if "STARDEW_PATH" in os.environ:
    return os.environ["STARDEW_PATH"]
  data_dir = os.path.expanduser("~/.config")
  if platform.system() == "Linux":
    data_dir = os.environ.get("XDG_DATA_DIR", data_dir)
  elif platform.system() == "Windows":
    data_dir = os.environ.get("APPDATA")
  return os.path.join(data_dir, "StardewValley")

def split_days(ndays):
  "Convert a number of days to a (years, months, days) triple"
  years = ndays // DAYS_MONTH // MONTHS_YEAR
  months = ndays // DAYS_MONTH % MONTHS_YEAR
  days = ndays % DAYS_MONTH
  return (years, months, days)

def format_days(ndays, yfmt="{}y", mfmt="{}m", dfmt="{}d", sep=""):
  "Format a number of days to '%dy%dm%dd'"
  years, months, days = split_days(ndays)
  result = []
  if years:
    result.append(yfmt.format(years))
  if months:
    result.append(mfmt.format(months))
  if days:
    result.append(dfmt.format(days))
  return sep.join(result)

def format_minutes(nminutes, dfmt="{}d", hfmt="{}h", mfmt="{}m", sep=""):
  "Format a number of minutes to %dd%dh%dm"
  mins = nminutes % 60
  hours = (nminutes // 60) % 24
  days = (nminutes // 60) // 24
  result = []
  if days:
    result.append(dfmt.format(days))
  if hours:
    result.append(hfmt.format(hours))
  if mins:
    result.append(mfmt.format(mins))
  return sep.join(result)

class Seasons(enum.Enum):
  "The four seasons"
  SPRING = "spring"
  SUMMER = "summer"
  FALL = "fall"
  WINTER = "winter"
  ISLAND = "island"
SEASONS = tuple(s.value for s in Seasons)

class Data(enum.Enum):
  """
  Object definition keys

  Use these when accessing OBJECT[oid] fields.
  """
  ID = "id"
  NAME = "name"
  VALUE = "value"
  EDIBILITY = "edibility"
  TYPE = "type"
  CATEGORY = "category"
  DISPLAY = "display"
  DESCRIPTION = "description"
  EXTRAS = "extras"

class TreeStage(enum.Enum):
  "Phases of a tree's growth"
  SAPLING = 1
  SPROUT = 2
  BUSH = 3
  SMALL = 4
  GROWN = 5
  @classmethod
  def get(cls, val):
    "Convert a numeric stage (possibly > 5) to an enum value"
    if val < cls.SAPLING.value:
      return cls.SAPLING
    if cls.SAPLING.value <= val <= cls.GROWN.value:
      return cls(val)
    return cls.GROWN

class Quality(enum.Enum):
  "Quality constants"
  NORMAL = 0
  SILVER = 1
  GOLD = 2
  IRIDIUM = 3
  @classmethod
  def get(cls, val):
    "Convert a number (possibly > 3) to an enum value"
    if val < cls.NORMAL.value:
      return cls.NORMAL
    if cls.NORMAL.value <= val <= cls.IRIDIUM.value:
      return cls(val)
    return cls.IRIDIUM

def get_data_path():
  "Determine the path to the data directory by trying pwd, then __file__"
  for base in (os.path.curdir, os.path.dirname(__file__)):
    dpath = os.path.join(base, DATA_PATH)
    if os.path.isdir(dpath):
      return dpath
  raise IOError("Failed to find data path {!r}".format(DATA_PATH))

def _load_data(name, reader=None, to=None): # pylint: disable=invalid-name
  "Load a file from the data directory with the given name"
  if reader is None:
    reader = lambda fobj: fobj.read().splitlines()
  with open(os.path.join(get_data_path(), name), "rt") as fobj:
    entries = reader(fobj)
  if to is not None:
    entries = to(entries)
  return entries

def _parse_object(oid, odef):
  "Parse a raw object definition into a dict with the above keys"
  fields = odef.split("/")
  name = fields[0]
  value = fields[1]
  edibility = fields[2]
  otype = fields[3]
  category = None
  if " " in fields[3]:
    otype, category = fields[3].split(None, 1)
  disp_name = fields[4]
  description = fields[5]
  extras = fields[6:]
  return {
    Data.ID: oid,
    Data.NAME: name,
    Data.VALUE: value,
    Data.EDIBILITY: edibility,
    Data.TYPE: otype,
    Data.CATEGORY: category,
    Data.DISPLAY: disp_name,
    Data.DESCRIPTION: description,
    Data.EXTRAS: extras
  }

NPCS = _load_data("npcs.txt", to=list) + [NPC_UNKNOWN]
LOCATIONS = _load_data("locations.txt", to=list) + [LOC_UNKNOWN]
OBJECTS_RAW = _load_data("objects.json", reader=json.load)
OBJECTS = {oid: _parse_object(oid, odef) for oid, odef in OBJECTS_RAW.items()}
FORAGE_SETS = _load_data("forage.json", reader=json.load)

def load_npcs(fname, reader=None):
  "Load NPCs from the given file"
  NPCS.extend(_load_data(fname, reader=reader))

def load_locations(fname, reader=None):
  "Load locations from the given file"
  LOCATIONS.extend(_load_data(fname, reader=reader))

def load_objects(fname):
  "Load objects from the given JSON file"
  new_objs = _load_data(fname, reader=json.load)
  OBJECTS_RAW.update(new_objs)
  for oid, odef in new_objs.items():
    OBJECTS[oid] = _parse_object(oid, odef)

FORAGE_SPRING = tuple(FORAGE_SETS["spring"])
FORAGE_SUMMER = tuple(FORAGE_SETS["summer"])
FORAGE_FALL = tuple(FORAGE_SETS["fall"])
FORAGE_WINTER = tuple(FORAGE_SETS["winter"])
FORAGE_BEACH = tuple(FORAGE_SETS["beach"])
FORAGE_MINES = tuple(FORAGE_SETS["mines"])
FORAGE_DESERT = tuple(FORAGE_SETS["desert"])
FORAGE_ISLAND = tuple(FORAGE_SETS["island"])
FORAGE = tuple(set.union(*(set(v) for v in FORAGE_SETS.values())))

def get_object(oid, field=None):
  """
  Get the object with the given ID (either int or str allowed).
  Returns a single field if requested and the entire object otherwise. See the
  Data enum above for allowed values.
  """
  if not isinstance(oid, str):
    oid = f"{oid}"
  if oid in OBJECTS:
    obj = OBJECTS[oid]
    if field is not None:
      return obj[field]
    return obj
  return None

def get_seeds(name=False):
  "Get the objects with type Seeds"
  for oid in OBJECTS:
    obj = OBJECTS[oid]
    if obj[Data.TYPE] == "Seeds":
      if name:
        yield obj[Data.NAME]
      yield obj

def get_tree(ttype):
  "Get the name for a tree type"
  tmap = {
    #"0": "",
    "1": "Oak Tree",
    "2": "Maple Tree",
    "3": "Pine Tree",
    #"4": "",
    #"5": "",
    "6": "Desert Palm Tree",
    "7": "Big Mushroom",
    "8": "Mahogany Tree",
    "9": "Island Palm Tree"
  }
  return tmap.get(ttype, "<unknown>")

def get_fruit_tree(ttype):
  "Get the name for a fruit tree type"
  tmap = {
    "0": "Cherry Tree",
    "1": "Apricot Tree",
    "2": "Orange Tree",
    "3": "Peach Tree",
    "4": "Pomegranate Tree",
    "5": "Apple Tree",
    #"6": "",
    "7": "Banana Tree",
    "8": "Mango Tree"
  }
  return tmap.get(ttype, "<unknown>")

# vim: set ts=2 sts=2 sw=2:
