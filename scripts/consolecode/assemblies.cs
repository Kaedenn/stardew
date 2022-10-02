
/* Display the loaded assemblies */
{
  List<string> messages = new();
  List<string> assemblies = new();

  mIncludeMicrosoft = false;
  mIncludeStardewValley = false;
  mIncludeOther = false;

  foreach (var arg in args) {
    if (arg == "-h" || arg == "--help") {
      return String.Join("\n",
          "usage: cs --script assemblies.cs [-h] [-a | [-m] [-s] [-o]] [-T]",
          "options:",
          "\t-h\tthis message",
          "\t-a\tinclude all assemblies",
          "\t-m\tinclude Microsoft assemblies",
          "\t-s\tinclude StardewValley assemblies",
          "\t-o\tinclude other (eg. ConsoleCode) assemblies",
          "\t-T\tinclude types defined in these assemblies");
    } else if (arg == "-a") {
      mIncludeMicrosoft = true;
      mIncludeStardewValley = true;
      mIncludeOther = true;
    } else if (arg == "-m") {
      mIncludeMicrosoft = true;
    } else if (arg == "-s") {
      mIncludeStardewValley = true;
    } else if (arg == "-o") {
      mIncludeOther = true;
    } else if (arg == "-T") {
      mShowTypes = true;
    } else {
      messages.Add($"Ignoring unknown argument {arg}");
    }
  }

  foreach (var asm in AppDomain.CurrentDomain.GetAssemblies()) {
    try {
      foreach (var line in GetAssemblyInfo(asm)) {
        assemblies.Add(line);
      }
    }
    catch (Exception e) {
      messages.Add(e.ToString());
    }
  }

  assemblies.Sort();

  List<string> results = new();
  if (messages.Count > 0) {
    results.Add($"Errors: {messages.Count}");
    foreach (var msg in messages) {
      results.Add(msg);
    }
  }
  foreach (var str in assemblies) {
    results.Add(str);
  }
  return String.Join("\n", results);
}

}

static List<string> GetAssemblyInfo(System.Reflection.Assembly asm) {
  List<string> lines = new();
  if (ShouldInclude(asm)) {
    string aname = asm.GetName().Name;
    if (mShowTypes) {
      foreach (var mod in asm.Modules) {
        string mname = mod.ToString();
        if (mname.StartsWith(aname)) {
          lines.Add(mname);
        } else {
          lines.Add(aname + "; module: " + mname);
        }
      }
    } else {
      lines.Add(asm.ToString());
    }
  }
  return lines;
}

const int KIND_SYSTEM = 1;
const int KIND_SDV = 2;
const int KIND_OTHER = 3;

static bool mIncludeMicrosoft = false;
static bool mIncludeStardewValley = false;
static bool mIncludeOther = false;
static bool mShowTypes = false;

public static bool ShouldInclude(int kind) {
  if (kind == KIND_SYSTEM && !mIncludeMicrosoft) return false;
  if (kind == KIND_SDV && !mIncludeStardewValley) return false;
  if (kind == KIND_OTHER && !mIncludeOther) return false;
  return true;
}

public static bool ShouldInclude(System.Reflection.Assembly asm) {
  int kind = 0;
  string aname = asm.GetName().Name;
  if (aname == "Microsoft.GeneratedCode") {
    kind = KIND_OTHER;
  } else if (aname == "System" || aname.StartsWith("System.")) {
    kind = KIND_SYSTEM;
  } else if (aname == "StardewValley" || aname.StartsWith("StardewValley.")) {
    kind = KIND_SDV;
  } else {
    kind = KIND_OTHER;
  }

  return ShouldInclude(kind);
}

public static object dummy() {

// vim: set ts=2 sts=2 sw=2 nocindent cinoptions=:
