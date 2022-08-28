#!/usr/bin/env python3

"""
Constants and functions related to Stardew Valley game data

This module provides access to the several names, locations, and objects
defined in the game. Exported identifiers include the following:

NPCS            tuple containing names of all NPCs
LOCATIONS       tuple containing names of all locations
OBJECTS         dict of object ID to object definition (see help(stardew.Data))
FORAGE          tuple containing names of all forage objects
FORAGE_<set>    tuple containing names of the particular forage set
"""

import enum
import json
import os
import platform

# Path to this script's data files
DATA_PATH = "data"

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

def _load_data(name, reader=None):
  """
  Read the given data file.

  If reader is None, this returns file_object.read().splitlines()
  Otherwise, this returns reader(file_object)
  """
  with open(os.path.join(DATA_PATH, name), "rt") as fobj:
    if reader is None:
      return fobj.read().splitlines()
    return reader(fobj)

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

NPC_UNKNOWN = "<unknown>"
LOCATION_UNKNOWN = "<unknown>"
ARTIFACT = ("Artifact Spot",)

NPCS = tuple(_load_data("npcs.txt")) + (NPC_UNKNOWN,)
LOCATIONS = tuple(_load_data("locations.txt")) + (LOCATION_UNKNOWN,)
OBJECTS_RAW = _load_data("objects.json", reader=json.load)
OBJECTS = {oid: _parse_object(oid, odef) for oid, odef in OBJECTS_RAW.items()}
FORAGE_SETS = _load_data("forage.json", reader=json.load)

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

def get_seeds(name=None):
  "Get the objects with type Seeds"
  for oid in OBJECTS:
    obj = OBJECTS[oid]
    if obj[Data.TYPE] == "Seeds":
      yield obj

# vim: set ts=2 sts=2 sw=2:
