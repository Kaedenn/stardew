
/* Display artifact spots that have yet to be harvested
cs --script objects.cs

TODO:
  Argument to restrict output to current map
  Argument to warp the player to the first result (desert handling?)
 */
{
  var objects = new List<StardewValley.Object>();
  var objmap = new Dictionary<string, List<Tuple<string, StardewValley.Object>>>();

  bool mShowArtifacts = true;
  bool mShowObjects = true;
  bool mShowForage = true;
  bool mCurrMap = false;
  bool mWarp = false;

  foreach (var arg in args) {
    if (arg == "-h" || arg == "--help") {
      return String.Join("\n",
          "cs --script objects.cs [-h] [-a] [-o] [-f] [-m] [-w]",
          "options:",
          "\t-h\tthis message",
          "\t-a\tshow only artifacts",
          "\t-o\tshow only artifacts, clay stone, and bone rocks",
          "\t-f\tshow only forage items",
          "\t-m\tlimit output to only the current map",
          "\t-w\twarp player to the first match");
    } else if (arg == "-a") {
      mShowArtifacts = true;
      mShowObjects = false;
      mShowForage = false;
    } else if (arg == "-o") {
      mShowObjects = true;
      mShowForage = false;
    } else if (arg == "-f") {
      mShowArtifacts = false;
      mShowObjects = false;
      mShowForage = true;
    } else if (arg == "-m") {
      mCurrMap = true;
    } else if (arg == "-w") {
      mWarp = true;
    }
  }

  /* Get a printable name for a StardewValley.Object */
  var getName =
    new Func<StardewValley.Object, string>((obj) => {
      if (obj.ParentSheetIndex == 816) return "Stone (Fossil)";
      if (obj.ParentSheetIndex == 817) return "Stone (Fossil)";
      if (obj.ParentSheetIndex == 818) return "Stone (Clay)";
      if (obj.ParentSheetIndex == 751) return "Node (Copper)";
      if (obj.ParentSheetIndex == 290) return "Node (Silver)";
      if (obj.ParentSheetIndex == 764) return "Node (Gold)";
      var name = obj.Name;
      var dname = obj.DisplayName;
      if (name != dname) {
        return name + " " + dname;
      }
      return name;
    });

  /* Add the location and object to the objmap collection */
  var addItem =
    new Action<string, StardewValley.Object>((loc, obj) => {
      var key = getName(obj);
      if (!objmap.ContainsKey(key)) {
        objmap[key] = new List<Tuple<string, StardewValley.Object>>();
      }
      var ovalue = new Tuple<string, StardewValley.Object>(loc, obj);
      objmap[key].Add(ovalue);
    });

  var locations = new List<StardewValley.GameLocation>();
  if (mCurrMap) {
    locations.Add(StardewValley.Game1.currentLocation);
  } else {
    locations = new List<StardewValley.GameLocation>(Game1.locations);
  }
  foreach (var loc in locations) {
    /* Process objects */
    foreach (var obj in loc.Objects.Values) {
      bool showme = false;
      if (obj.bigCraftable.Value == true) {
        continue;
      }
      switch (obj.ParentSheetIndex) {
        case 16: // Wild Horseradish (Cheese Press)
        case 18: // Daffodil
        case 20: // Leek (Recycling Machine)
        case 22: // Dandelion
        case 78: // Cave Carrot
        case 88: // Coconut
        case 90: // Cactus Fruit (Bone Mill)
        case 152: // Seaweed (Wooden Lamp Post)
        case 257: // Morel
        case 259: // Fiddlehead Fern
        case 281: // Chanterelle
        case 283: // Holly
        case 296: // Salmonberry
        case 372: // Clam
        case 392: // Nautilus Shell
        case 393: // Coral
        case 394: // Rainbow Shell
        case 396: // Spice Berry
        case 397: // Sea Urchin
        case 398: // Grape
        case 399: // Spring Onion
        case 402: // Sweet Pea
        case 404: // Common Mushroom
        case 406: // Wild Plum
        case 408: // Hazelnut
        case 410: // Blackberry
        case 412: // Winter Root
        case 414: // Crystal Fruit
        case 416: // Snow Yam
        case 418: // Crocus
        case 420: // Red Mushroom
        case 422: // Purple Mushroom
        case 718: // Cockle
        case 719: // Mussel
        case 723: // Oyster
        case 829: // Ginger
        case 851: // Magma Cap
          if (mShowForage) {
            addItem(loc.name, obj);
            objects.Add(obj);
          }
          break;
        case 590: // Artifact Spot
          if (mShowObjects || mShowArtifacts) {
            addItem(loc.name, obj);
            objects.Add(obj);
          }
          break;
        case 816: // Fossil Stone (large)
        case 817: // Fossil Stone
        case 818: // Clay Stone
        case 819: // Stone
        case 751: // Copper Node
        case 290: // Silver Node
        case 764: // Gold Node
          if (mShowObjects) {
            addItem(loc.name, obj);
            objects.Add(obj);
          }
          break;
      }
    }
  }

  string result = $"objects: {objects.Count}";
  var onames = new List<string>(objmap.Keys);
  onames.Sort();

  Info($"Discovered {objects.Count} objects");

  string warpCommand = "";
  foreach (var oname in onames) {
    var ovalue = objmap[oname];
    result += $"\n{oname}: {ovalue.Count}";
    foreach (var objdef in ovalue) {
      var omap = objdef.Item1;
      var obj = objdef.Item2;
      var oloc = obj.tileLocation;
      var pos = $"{oloc.X} {oloc.Y}";
      var command = $"warp {omap} {pos}";
      if (mWarp && warpCommand == "") {
        warpCommand = command;
        result += $"\n\texec debug {command}";
      } else {
        result += $"\n\tdebug {command}";
      }
    }
  }
  result += "\n";

  if (warpCommand != "") {
    Info(warpCommand + "...");
    if (!RunDebugCommand(warpCommand)) {
      Info($"Failed to execute command \"{warpCommand}\"");
    }
  }

  return result;
}
} // Main

static void Info(string message) {
  Game1.chatBox.addInfoMessage(message);
}

static bool RunDebugCommand(string command) {
  return StardewValley.Program.gamePtr.parseDebugInput(command);
}

} // class UserCode
} // namespace ConsoleCode

/*
namespace Kae {
  public class ObjectCommandMod : Mod {
    public override void Entry(IModHelper helper) {
      this.Monitor.Log("Loaded ObjectCommandMod", LogLevel.Info);
    }
    private void onObjectsCommand(string command, string[] args) {
      this.Monitor.Log($"Received command '{command}' args '{String.Join("\n", args)}");
    }
  }
}
*/

namespace ConsoleCode {
  class Dummy {
    public object dummy() {

// vim: set ts=2 sts=2 sw=2 nocindent cinoptions=:
