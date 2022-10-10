
/* Display locations of all berry bushes in the current map */
{
  bool currMap = true;

  foreach (var arg in args) {
    if (arg == "-a") {
      currMap = false;
    }
  }

  var bmap = new Dictionary<string, List<StardewValley.TerrainFeatures.LargeTerrainFeature>>();
  var blist = new List<Tuple<string, StardewValley.TerrainFeatures.LargeTerrainFeature>>();

  foreach (var loc in Game1.locations) {
    if (currMap && loc != Game1.currentLocation) continue;
    foreach (var bush in loc.largeTerrainFeatures.Where(
      feat => feat is StardewValley.TerrainFeatures.Bush b
        && b.inBloom(Game1.currentSeason, Game1.dayOfMonth)
        && !b.townBush
        && b.tileSheetOffset == 1)) {
      if (!bmap.ContainsKey(loc.name)) {
        bmap[loc.name] = new List<StardewValley.TerrainFeatures.LargeTerrainFeature>();
      }
      bmap[loc.name].Add(bush);
      blist.Add(new Tuple<string, StardewValley.TerrainFeatures.LargeTerrainFeature>(loc.name, bush));
    }
  }

  Game1.chatBox.addInfoMessage($"Found {blist.Count} bushes");
  var bmaps = new List<string>(bmap.Keys);
  bmaps.Sort();
  var lines = new List<string>();
  foreach (var mapname in bmaps) {
    foreach (var feat in bmap[mapname]) {
      lines.Add($"\tdebug warp {mapname} {feat.tilePosition.X} {feat.tilePosition.Y}");
    }
  }
  return "\n" + String.Join("\n", lines) + "\n";
}
