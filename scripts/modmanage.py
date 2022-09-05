#!/usr/bin/env python3

"""
Convenient mod management utility
"""

import argparse
import ast
import glob
import json
import logging
import os
import shlex
import sys
import textwrap
import zipfile

logging.basicConfig(format="%(module)s:%(lineno)s: %(levelname)s: %(message)s",
                    level=logging.INFO)
logger = logging.getLogger(__name__)

BASE = os.path.join(os.path.dirname(__file__), os.pardir)

try:
  from utility.colorterm import ColorFormatter as C
except ImportError:
  sys.path.append(BASE)
  from utility.colorterm import ColorFormatter as C

class SVMod:
  "Simple class representing an unzipped mod"
  def __init__(self, mfile, text=None):
    self.mfile = mfile
    if not text:
      with open(mfile, "rt") as fobj:
        text = fobj.read()
    self.data = parse_manifest(text, mpath=self.mfile)

  def get(self, field):
    "Get an entry in the manifest file"
    return self.data[field]

  name = property(lambda self: self.get("Name"))
  author = property(lambda self: self.get("Author"))
  description = property(lambda self: self.get("Description"))
  version = property(lambda self: self.get("Version"))
  uniqueid = property(lambda self: self.get("UniqueID"))
  update_keys = property(lambda self: self.get("UpdateKeys"))

  def __repr__(self):
    "repr(self)"
    return repr(self.data)

def parse_manifest(data, mpath=None):
  "Parse a manifest file"
  if isinstance(data, bytes):
    data = data.decode()
  if data:
    if ord(data[0]) > 0xf000:
      data = data[1:]
  try:
    return json.loads(data)
  except json.JSONDecodeError as e:
    logger.debug("%s: malformed JSON: %s", mpath, e)
  return ast.literal_eval(data)

def find_game_path():
  "Attempt to locate the Stardew Valley game folder"
  steam_path = os.path.expanduser("~/.local/share/Steam")
  if not os.path.isdir(steam_path):
    raise IOError("Failed to locate Steam directory, please use -P")
  if os.path.exists(os.path.join(steam_path, "SteamApps")):
    steam_path = os.path.join(steam_path, "SteamApps")
  elif os.path.exists(os.path.join(steam_path, "steamapps")):
    steam_path = os.path.join(steam_path, "steamapps")
  else:
    raise IOError(f"{steam_path!r} doesn't contain steamapps directory")

  game_path = os.path.join(steam_path, "common/Stardew Valley")
  if not os.path.isdir(game_path):
    raise IOError(f"{game_path!r} not a directory")
  return game_path

def enumerate_mods(mods_path):
  "Enumerate the mods in the given path"
  for mfile in glob.glob(os.path.join(mods_path, "*/manifest.json")):
    logger.debug("Found manifest file %s", mfile)
    yield SVMod(mfile)

def enumerate_zipped_mods(zip_path):
  "Enumerate zipped mods in the given path"
  zmods = {}
  zpaths = {}
  for zfile in glob.glob(os.path.join(zip_path, "*.zip")):
    moddef = parse_mod_zip(zfile)
    if moddef is not None:
      if moddef.uniqueid in zmods:
        # We just saw this mod; is this a newer version?
        oldver = zmods[moddef.uniqueid].version
        newver = moddef.version
        if cmp_version(oldver, newver) >= 0:
          continue
      zmods[moddef.uniqueid] = moddef
      zpaths[moddef.uniqueid] = zfile
  return zmods, zpaths

def parse_mod_zip(zpath):
  "Parse a compressed (downloaded) mod"
  zf = zipfile.ZipFile(zpath)
  for zentry in zf.filelist:
    if os.path.basename(zentry.filename) == "manifest.json":
      logger.debug("Found manifest %s %r", zpath, zentry)
      mtext = zf.read(zentry.filename).decode()
      return SVMod(os.path.join(zpath, zentry.filename), text=mtext)
  return None

def cmp_version(ver1, ver2):
  "Compare two versions and return -1 if less, 0 if equal, 1 if greater"
  for p1, p2 in zip(ver1.split("."), ver2.split(".")):
    p1 = int(p1)
    p2 = int(p2)
    if p1 < p2:
      return -1
    if p1 > p2:
      return 1
  return 0

def print_mod(moddef, installed=False, available=False, upgrade=None):
  "Print a mod definition to the host terminal"
  name = C(C.BLU_B, C.BOLD, moddef.name)
  version = C(C.GRN_B, C.BOLD, moddef.version)
  author = C(C.GRN, moddef.author)
  description = C(C.CYN, moddef.description)

  if upgrade is not None:
    currver = C(C.GRN_B, C.BOLD, upgrade.version)
    mode = C(C.GRN_B, C.ITAL, C.BOLD, "upgrade from ") + currver
  elif installed:
    mode = C(C.GRN_B, C.ITAL, "installed")
  elif available:
    mode = C(C.GRN_B, C.ITAL, C.BOLD, "available")
  else:
    mode = C(C.GRN, C.ITAL, "not installed")
  print(f"{name} {version} by {author} - {description} [{mode}]")

def main():
  "Entry point"
  ap = argparse.ArgumentParser(epilog=textwrap.dedent("""
  List installed mods and compare those against downloaded mod zip files.

  Pass your downloads directory to -p,--zip-path to have this script compare
  your downloaded mods with those you have installed.
  """), formatter_class=argparse.RawDescriptionHelpFormatter)
  ap.add_argument("-P", "--game-path", metavar="PATH",
      help="path to Stardew Valley game directory (default: infer)")
  ap.add_argument("-p", "--zip-path", metavar="PATH",
      help="path to downloaded zip files")
  ap.add_argument("-l", "--list-installed", action="store_true",
      help="list installed mods and their versions")
  ap.add_argument("-v", "--verbose", action="store_true", help="verbose output")
  args = ap.parse_args()
  if args.verbose:
    logger.setLevel(logging.DEBUG)

  game_path = args.game_path
  if not game_path:
    game_path = find_game_path()

  mods_path = os.path.join(game_path, "Mods")
  if not os.path.isdir(mods_path):
    ap.error(f"{game_path} lacks Mods directory")

  mods = {}
  for moddef in enumerate_mods(mods_path):
    logger.debug("Found mod %s version %s", moddef.name, moddef.version)
    mods[moddef.uniqueid] = moddef
  logger.info("Scanned %d installed mods", len(mods))

  if args.list_installed:
    for moddef in sorted(mods.values(), key=lambda v: v.name):
      print_mod(moddef, installed=True)

  upgrades = []

  zmods = {}
  zpaths = {}
  if args.zip_path:
    zmods, zpaths = enumerate_zipped_mods(args.zip_path)
    logger.info("Scanned %d zip files", len(zmods))

    for mid, moddef in sorted(zmods.items(), key=lambda kv: kv[1].name):
      if mid in mods:
        iver = mods[mid].version
        zver = moddef.version
        logger.debug("%s: installed %s zip %s", moddef.name, iver, zver)
        if cmp_version(iver, zver) < 0:
          zpath = zpaths[moddef.uniqueid]
          upgrades.append((zpath, moddef))
          print_mod(moddef, upgrade=mods[mid])
      else:
        print_mod(moddef)
  else:
    for moddef in sorted(mods.values(), key=lambda v: v.name):
      print_mod(moddef, installed=True)

  navail = len(upgrades)
  print(f"{navail} upgrade{'' if navail == 1 else 's'} available")
  if upgrades:
    print("Run the following commands to install them:")
  for zpath, moddef in upgrades:
    cmd = "unzip {} -d {}".format(shlex.quote(zpath), shlex.quote(mods_path))
    print(C(C.BOLD, cmd))

if __name__ == "__main__":
  main()

# vim: set ts=2 sts=2 sw=2:
