
/* Compile and run a C# "script".
 * This is like ConsoleCode and ContentCode, but you can specify an
 * entire source file, including imports, class definitions, and more.
 *
 * This allows executing entire single-file mods without needing to
 * restart the game.
 *
 * Note that the script below heavily abuses the lack of processing or
 * formatting done by the ConsoleCode mod in order to add another
 * method, hence the mismatched braces.
 *
 * This script is dangerous and can lead to major problems if misused.
 * Be careful.
 */

/* Known issues:
 *
 * You can't actually reference the new assembly for some reason.
 * Provide a mechanism to enumerate the things the new assembly
 * defines.
 *
 */
{
  mHelper = Helper;

  var scrargs = new List<string>();

  /* Because we don't get access to the logger */
  var output = new List<string>();

  if (args.Length == 0) {
    return getUsage();
  }

  for (var i = 0; i < args.Length; ++i) {
    string arg = args[i];
    if (arg == "-h" || arg == "--help") {
      return getHelp();
    }
    if (arg == "-v") {
      mVerbose = true;
    } else {
      mScript = resolvePath(arg);
      if (mScript == "") {
        return "failed to find file " + arg;
      }
    }
  }

  mScriptArgs = String.Join(" ", scrargs);

  if (mVerbose) {
    output.Add($"Additional code: {String.Join(" ", scrargs)}");
  }

  /* Read and compile mScript */
  var cmessages = compileAndRun(mScript);
  output.AddRange(cmessages);

  return String.Join("\n", output);
}
}

static IModHelper mHelper;

static string mScript = "";

static string mScriptArgs = "";

static bool mVerbose = false;

public static string resolvePath(string path) {
  if (System.IO.File.Exists(path)) {
    return path;
  }

  string fpath = System.IO.Path.Combine(mHelper.DirectoryPath, path);
  if (System.IO.File.Exists(fpath)) {
    return fpath;
  }
  return "";
}

public static string getUsage() {
  return "usage: cs --script runscript.cs [-h|file|path] [-v]";
}

public static string getHelp() {
  return String.Join("\n",
      getUsage(),
      "options:",
      "\t-h\tthis message",
      "\t-v\tadd additional output",
      "",
      "By default, this script compiles and loads the code within the given",
      "file(s), but does not call any functions or invoke any further code.",
      "You can work around this by executing `cs` an additional time to call",
      "the code you just added.",
      "",
      "Examples TBD");
}

private static List<string> compileAndRun(string file) {
  Microsoft.CodeAnalysis.CSharp.CSharpCompilation codeobj = null;

  //             CSharpCompilation compilation = CSharpCompilation.Create( Path.GetRandomFileName(), new[] { CSharpSyntaxTree.ParseText( code ) }, refs, new CSharpCompilationOptions( OutputKind.DynamicallyLinkedLibrary ) );

  List<string> messages = new();

  string text = System.IO.File.ReadAllText(file);

  List<Microsoft.CodeAnalysis.MetadataReference> refs = new();
  foreach (var asm in AppDomain.CurrentDomain.GetAssemblies()) {
    try {
      refs.Add(Microsoft.CodeAnalysis.MetadataReference.CreateFromFile(asm.Location));
    }
    catch (Exception e) {
      //messages.Add("Error loading assembly: " + e.ToString());
    }
  }

  messages.Add($"Added {refs.Count} reference assemblies");

  string tempPath = System.IO.Path.GetRandomFileName();
  var code = Microsoft.CodeAnalysis.CSharp.CSharpSyntaxTree.ParseText(text);

  codeobj = Microsoft.CodeAnalysis.CSharp.CSharpCompilation.Create(tempPath,
      new[]{ code },
      refs,
      new Microsoft.CodeAnalysis.CSharp.CSharpCompilationOptions(Microsoft.CodeAnalysis.OutputKind.DynamicallyLinkedLibrary));

  System.IO.MemoryStream ms = new();
  var result = codeobj.Emit(ms);

  if (!result.Success) {
    messages.Add($"Compilation of {file} failed:");
  } else {
    messages.Add($"Compilation of {file} succeeded");
  }

  //var errors = result.Diagnostics.Where(d => d.IsWarningAsError || d.Severity == Microsoft.CodeAnalysis.DiagnosticSeverity.Error);
  var errors = result.Diagnostics.Where(d => d.Severity != Microsoft.CodeAnalysis.DiagnosticSeverity.Hidden);
  var dcount = 0;
  foreach (var error in errors) {
    dcount += 1;
    if (error.Severity == Microsoft.CodeAnalysis.DiagnosticSeverity.Hidden) {
      continue;
    }
    messages.Add($"{error.Id}: {error.Severity}: {error.GetMessage()}");
    if (mVerbose) {
      messages.Add(error.ToString());
    }
  }
  messages.Add($"{dcount} total diagnostic messages");

  ms.Seek(0, System.IO.SeekOrigin.Begin);
  var newAsm = System.Runtime.Loader.AssemblyLoadContext.Default.LoadFromStream(ms);
  var asmName = newAsm.GetName().FullName;
  messages.Add($"Loaded assembly {asmName} successfully");

  messages.Add(newAsm.GetName().Name);

  if (mVerbose) {
    messages.Add("---------- BEGIN CODE ----------");
    messages.Add(text);
    messages.Add("---------- END CODE ----------");
  }

  /*
ms.Seek( 0, SeekOrigin.Begin );
Assembly asm = AssemblyLoadContext.Default.LoadFromStream( ms );
Type type = asm.GetType( $"ConsoleCode.UserCode{i}" );
MethodInfo meth = type.GetMethod( "Main" );
return meth;
  */

  return messages;


// vim: set ts=2 sts=2 sw=2 nocindent cinoptions=:
