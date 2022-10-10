
/* Display artifact spots that have yet to be harvested
cs --script objects.cs

FIXME: Warping to the desert occasionally invokes the bus arrival animation
TODO: Gemstone handling
 */
{
  var objects = new List<StardewValley.Object>();
  var objmap = new Dictionary<string, List<Tuple<string, StardewValley.Object>>>();

  bool argGiven = false;
  bool argArtifact = false;
  bool argObject = false;
  bool argForage = false;
  bool argReady = false;
  foreach (var arg in args) {
    if (arg == "-h" || arg == "--help") {
      return String.Join("\n",
          "cs --script objects.cs [-h] [-aofr] [-m] [-w] [-nvV]",
          "options:",
          "\t-h\tthis message",
          "\t--all\tshow everything",
          "\t-a\tshow artifacts",
          "\t-o\tshow artifacts, clay stone, and bone rocks",
          "\t-f\tshow forage items",
          "\t-r\tshow machines ready for harvest",
          "\t-m\tlimit search to the current map",
          "\t-w\twarp player to the first match",
          "\t-n\tdon't display \"debug warp\" commands",
          "\t-v\tinclude additional information",
          "\t-V\tinclude a lot of additional information");
    } else if (arg == "--all") {
      argGiven = true;
      argArtifact = true;
      argObject = true;
      argForage = true;
      argReady = true;
    } else if (arg == "-a") {
      argGiven = true;
      argArtifact = true;
    } else if (arg == "-o") {
      argGiven = true;
      argObject = true;
    } else if (arg == "-f") {
      argGiven = true;
      argForage = true;
    } else if (arg == "-r") {
      argGiven = true;
      argReady = true;
    } else if (arg == "-m") {
      mCurrMap = true;
    } else if (arg == "-w") {
      mWarp = true;
    } else if (arg == "-n") {
      mPrintWarps = false;
    } else if (arg == "-v" || arg == "-V") {
      mDebug = true;
      mTrace = (arg == "-V");
    }
  }

  if (argGiven) {
    if (argObject || argArtifact) {
      mShowArtifacts = true;
    }
    if (argObject) {
      mShowObjects = true;
    }
    if (argForage) {
      mShowForage = true;
    }
    if (argReady) {
      mShowReady = true;
    }
  } else {
    mShowArtifacts = true;
    mShowObjects = true;
    mShowForage = true;
  }

  /* Add the location and object to the objmap collection */
  var addItem =
    new Action<string, StardewValley.Object>((loc, obj) => {
      var key = GetName(obj);
      if (!objmap.ContainsKey(key)) {
        objmap[key] = new List<Tuple<string, StardewValley.Object>>();
      }
      var ovalue = new Tuple<string, StardewValley.Object>(loc, obj);
      objmap[key].Add(ovalue);
    });

  /* Determine the location(s) we're scanning */
  var locations = new List<GameLocation>();
  if (mCurrMap) {
    locations.Add(Game1.currentLocation);
  } else {
    locations.AddRange(Game1.locations);
  }

  foreach (var loc in locations) {
    foreach (var obj in loc.Objects.Values) {
      string category = Categorize(obj);
      if (category == CAT_FORAGE && mShowForage
          || category == CAT_OBJECT && mShowObjects
          || category == CAT_ARTIFACT && mShowArtifacts
          || category == CAT_MACHINE && mShowReady) {
        addItem(loc.name, obj);
        objects.Add(obj);
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
      var command = $"warp {omap} {oloc.X} {oloc.Y}";
      var commandShow = $"\n\tdebug {command}";
      if (mWarp && warpCommand == "") {
        warpCommand = command;
        commandShow = $"\n\texec debug {command}";
      }
      if (mPrintWarps) {
        result += commandShow;
      }
      if (mTrace) {
        result += "\n" + Kae.ObjectToStr.ToString(obj);
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

static bool mShowArtifacts = false;
static bool mShowObjects = false;
static bool mShowForage = false;
static bool mShowReady = false;
static bool mShowClumps = false;
static bool mCurrMap = false;
static bool mPrintWarps = true;
static bool mWarp = false;
static bool mDebug = false;
static bool mTrace = false;

static void Info(string message) {
  Game1.chatBox.addInfoMessage(message);
}

static bool RunDebugCommand(string command) {
  return StardewValley.Program.gamePtr.parseDebugInput(command);
}

const string CAT_ARTIFACT = "artifact";
const string CAT_OBJECT = "object";
const string CAT_FORAGE = "forage";
const string CAT_MACHINE = "machine";
const string CAT_OTHER = "other";

/* Get the name of an object for display */
static string GetName(StardewValley.Object obj) {
  string name = obj.DisplayName;
  if (obj.ParentSheetIndex == 816) name += " (Fossil)";
  else if (obj.ParentSheetIndex == 817) name += " (Fossil)";
  else if (obj.ParentSheetIndex == 818) name += " (Clay)";
  else if (obj.ParentSheetIndex == 751) name += " (Copper)";
  else if (obj.ParentSheetIndex == 290) name += " (Silver)";
  else if (obj.ParentSheetIndex == 764) name += " (Gold)";
  // TODO: add gemstones
  else if (obj.Name != obj.DisplayName) {
    name = obj.DisplayName + " (" + obj.Name + ")";
  }

  if (mDebug) {
    name += $" [{obj.ParentSheetIndex}]";
  }

  return name;
}

/* Return a string (one of the CAT_ constants) describing the given object */
static string Categorize(StardewValley.Object obj) {
  /* Omit these specifically as they can also satisfy the "Ready" logic */
  if (obj is StardewValley.Objects.ItemPedestal) {
    return CAT_OTHER;
  }

  /* Machines are big craftables and ready for harvest */
  if (obj.bigCraftable.Value == true) {
    if (obj.readyForHarvest.Value == true) {
      return CAT_MACHINE;
    }
    return CAT_OTHER;
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
    case 430: // Truffle
    case 718: // Cockle
    case 719: // Mussel
    case 723: // Oyster
    case 829: // Ginger
    case 851: // Magma Cap
      return CAT_FORAGE;
    case 590: // Artifact Spot
      return CAT_ARTIFACT;
    case 816: // Fossil Stone (large)
    case 817: // Fossil Stone
    case 818: // Clay Stone
    case 819: // Stone
    case 751: // Copper Node
    case 290: // Silver Node
    case 764: // Gold Node
      return CAT_OBJECT;
    default:
      return CAT_OTHER;
  }
}

} // class UserCode
} // namespace ConsoleCode

namespace Kae {
  using System.Reflection;
  using Microsoft.CodeAnalysis.CSharp;

  public static class ObjectToStr {
    public static string ToLiteral(string valueText) {
      return SymbolDisplay.FormatLiteral(valueText, false);
    }

    public class FormatRules {
      public string blockBegin;
      public string blockEnd;
      public string fieldsSeparator;
      public string fieldValueSeparator;
      public bool withTypes;
      public bool showStatic;
      public bool showPrivate;
      public FormatRules() {
        blockBegin = "{";
        blockEnd = "}";
        fieldsSeparator = ";";
        fieldValueSeparator = "=";
        withTypes = true;
        showStatic = false;
        showPrivate = false;
      }

      public BindingFlags GetBinding() {
        var binding = BindingFlags.DeclaredOnly
          | BindingFlags.Instance
          | BindingFlags.Public;
        if (showStatic) binding |= BindingFlags.Static;
        if (showPrivate) binding |= BindingFlags.NonPublic;
        return binding;
      }
    }
    public static int CompareFields(FieldInfo left, FieldInfo right) {
      return left.Name.CompareTo(right.Name);
    }

    private static string FieldToString(
        object obj,
        FieldInfo field,
        FormatRules fmt)
    {
      Type ftype = field.FieldType;
      object fvalue = field.GetValue(obj);
      string keystr = field.Name;
      string valstr;
      if (ftype == typeof(string)) {
        valstr = ToLiteral(fvalue as string);
      } else if (ftype.HasElementType) {
        keystr = $"{field.Name}[?]";
        valstr = "{...}";
      } else if (fvalue == null) {
        valstr = "null";
      } else {
        valstr = fvalue.ToString();
      }
      if (fmt.withTypes) {
        keystr = ftype.Name + " " + keystr;
      }
      return keystr + fmt.fieldValueSeparator + valstr + fmt.fieldsSeparator;
    }

    public static string ToString(object obj, FormatRules fmt) {
      var sb = new StringBuilder();

      Type type = obj.GetType();
      FieldInfo[] fields = type.GetFields(fmt.GetBinding());
      var flist = new List<FieldInfo>(fields);
      flist.Sort(CompareFields);

      if (fmt.withTypes) {
        sb.Append(type.Name);
        sb.Append(fmt.blockBegin);
      }
      foreach (FieldInfo field in flist) {
        sb.Append(FieldToString(obj, field, fmt));
      }
      if (fmt.withTypes) {
        sb.Append(fmt.blockEnd);
      }
      return sb.ToString();
    }

    public static string ToString(object obj) {
      return ToString(obj, new FormatRules());
    }
  }
}

namespace ConsoleCode {
  class Dummy {
    public object dummy() {

// vim: set ts=2 sts=2 sw=2 nocindent cinoptions=:
