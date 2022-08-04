#!/usr/bin/env python3

"""
Constants and functions related to Stardew Valley
"""

import enum
import json
import os

DATA_PATH = "data"

def _load_data(name, reader=None):
  "Read the given data file"
  with open(os.path.join(DATA_PATH, name), "rt") as fobj:
    if reader is None:
      return fobj.read().splitlines()
    return reader(fobj)

class Obj(enum.Enum):
  "Object field names"
  NAME = "name"
  VALUE = "value"
  EDIBILITY = "edibility"
  TYPE = "type"
  CATEGORY = "category"
  DISPLAY = "display"
  DESCRIPTION = "description"
  EXTRAS = "extras"

def _parse_object(odef):
  "Parse a raw object definition"
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
    Obj.NAME: name,
    Obj.VALUE: value,
    Obj.EDIBILITY: edibility,
    Obj.TYPE: otype,
    Obj.CATEGORY: category,
    Obj.DISPLAY: disp_name,
    Obj.DESCRIPTION: desc,
    Obj.EXTRAS: extras
  }

NPC_UNKNOWN = "<unknown>"
LOCATION_UNKNOWN = "<unknown>"
ARTIFACT = ("Artifact Spot",)

NPCS = tuple(_load_data("npcs.txt")) + (NPC_UNKNOWN,)
LOCATIONS = tuple(_load_data("locations.txt")) + (LOCATION_UNKNOWN,)
OBJECTS_RAW = _load_data("objects.json", reader=json.load)
OBJECTS = {oid: _parse_object(odef) for oid, odef in OBJECTS_RAW.items()}

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

# Map Object Sets {{{0

FORAGE_SPRING = (
  "Wild Horseradish",
  "Daffodil",
  "Leek",
  "Dandelion",
  "Spring Onion",
  "Common Mushroom",
  "Morel",
  "Salmonberry"
)

FORAGE_SUMMER = (
  "Grape",
  "Spice Berry",
  "Sweet Pea",
  "Red Mushroom",
  "Fiddlehead Fern",
  "Common Mushroom"
)

FORAGE_FALL = (
  "Common Mushroom",
  "Wild Plum",
  "Hazelnut",
  "Blackberry",
  "Chanterelle",
  "Red Mushroom",
  "Purple Mushroom"
)

FORAGE_WINTER = (
  "Winter Root",
  "Crystal Fruit",
  "Snow Yam",
  "Crocus",
  "Holly"
)

FORAGE_BEACH = (
  "Nautilus Shell",
  "Coral",
  "Sea Urchin",
  "Rainbow Shell",
  "Clam",
  "Cockle",
  "Mussel",
  "Oyster",
  "Seaweed"
)

FORAGE_MINES = (
  "Red Mushroom",
  "Purple Mushroom",
  "Cave Carrot"
)

FORAGE_DESERT = (
  "Cactus Fruit",
  "Coconut"
)

FORAGE_ISLAND = (
  "Ginger",
  "Magma Cap"
)

FORAGE = set(
  FORAGE_SPRING +
  FORAGE_SUMMER +
  FORAGE_FALL +
  FORAGE_WINTER +
  FORAGE_BEACH +
  FORAGE_MINES +
  FORAGE_DESERT +
  FORAGE_ISLAND
)

# 0}}}



# vim: set ts=2 sts=2 sw=2:
