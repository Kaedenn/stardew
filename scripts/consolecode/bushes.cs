
/* Display locations of all berry bushes in the current map */
{
  IEnumerable<StardewValley.TerrainFeatures.LargeTerrainFeature> bushes =
    Game1.player.currentLocation.largeTerrainFeatures.Where(
      x => x is StardewValley.TerrainFeatures.Bush b
        && b.inBloom(Game1.currentSeason, Game1.dayOfMonth)
        && !b.townBush
        && b.tileSheetOffset == 1);

  return String.Join("\n", bushes.Select(b => b.tilePosition.ToString()));
}
