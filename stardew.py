#!/usr/bin/env python3

"""
Constants and functions related to Stardew Valley game data

This module provides access to the several names, locations, and objects
defined in the game. Exported identifiers include the following:

NPCS            tuple of all NPCs
LOCATIONS       tuple of all location types (or names; see below)
OBJECTS         dict of object ID to object definition (see help(stardew.Data))
FORAGE          tuple containing names of all forage objects
FORAGE_<set>    tuple containing names of the particular forage set

Note on NPCS and LOCATIONS values: these values refer to the xsi:type
attributes, if present, and the Name child element otherwise. See the README
for determining the name of a node.
"""

import enum
import json
import os

DATA_PATH = "data"

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
  NAME = "name"
  VALUE = "value"
  EDIBILITY = "edibility"
  TYPE = "type"
  CATEGORY = "category"
  DISPLAY = "display"
  DESCRIPTION = "description"
  EXTRAS = "extras"

def _parse_object(odef):
  "Parse a raw object definition into a dict with the above keys"
  fields = odef.split("/")
  name = fields[0]
  value = fields[1]
  edibility = fields[2]
  type_cat = fields[3]
  disp_name = fields[4]
  desc = fields[5]
  extras = fields[6:]
  if " " in type_cat:
    otype, category = type_cat.split(None, 1)
  else:
    otype = type_cat
    category = None
  return {
    Data.NAME: name,
    Data.VALUE: value,
    Data.EDIBILITY: edibility,
    Data.TYPE: otype,
    Data.CATEGORY: category,
    Data.DISPLAY: disp_name,
    Data.DESCRIPTION: desc,
    Data.EXTRAS: extras
  }

NPC_UNKNOWN = "<unknown>"
LOCATION_UNKNOWN = "<unknown>"
ARTIFACT = ("Artifact Spot",)

NPCS = tuple(_load_data("npcs.txt")) + (NPC_UNKNOWN,)
LOCATIONS = tuple(_load_data("locations.txt")) + (LOCATION_UNKNOWN,)
OBJECTS_RAW = _load_data("objects.json", reader=json.load)
OBJECTS = {oid: _parse_object(odef) for oid, odef in OBJECTS_RAW.items()}
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

def get_object(oid, fallback=None, field=None):
  "Get the object with the given ID"
  if not isinstance(oid, str):
    oid = f"{oid}"
  if oid in OBJECTS:
    obj = OBJECTS[oid]
    if field is not None:
      return obj[field]
    return obj
  return fallback

# vim: set ts=2 sts=2 sw=2:
