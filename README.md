# Stardew Valley Save Interrogation
The `savefile.py` module displays information contained within a Stardew Valley save file, such as the locations of forage objects, terrain features, locations and progress of crops, animal types, names, and happiness, just to name a few.

# Examples

List artifact spots (hoe spots with three little "worms"):

`python savefile.py <farm> -C artifact`

List forageables:

`python savefile.py <farm> -C forage`

List forageables anywhere but on the farm (note: single-quotes around `!Farm` are required if using a shell with history expansion, such as `bash`):

`python savefile.py <farm> -C forage -m '!Farm'`

List artifact spots anywhere on the island:

`python savefile.py <farm> -C artifact -m 'Island*'`

# Save files

There are a couple ways to specify where you keep your Stardew Valley saves. By default, `savefile.py` will determine the default location based on your OS. If that fails, or if you have your saves stored somewhere else, you have two options:

1. Specify the path using `-P,--save-path`. For example, if you keep your saves in `$HOME/games/StardewValley`, specify `python savefile.py -C "$HOME/games/StardewValley"` or `python savefile.py --save-path "$HOME/games/StardewValley"`.
2. Specify the path using the `STARDEW_PATH` environment variable. This is intended for developer use.

## Listing available save files

`python savefile.py --list`

`python savefile.py --save-path "<path>" --list`

# Usage

Note: Run `python savefile.py -h` for a more complete description of what can be done.

You can specify your save file by name, filename, or path. For instance, I have a farm `Haven_316643857`. I can specify any of the following:

`python savefile.py Haven <arguments>`

`python savefile.py Haven_316643857 <arguments>`

`python savefile.py ~/.config/StardewValley/Saves/Haven_316643857 <arguments>`

## Output selection

### Objects

This includes forageables, artifact spots, machines, and more.

TODO

### Terrain features

This includes things part of the terrain: hoe dirt, flooring, trees, fruit trees, grass, and bushes.

TODO

### Crops

This includes every instance of the `HoeDirt` terrain feature with a `<crop>` child element present.

TODO

### Trees (and fruit trees)

This includes every instance of either the `Tree` or the `FruitTree` terrain features.

TODO

### Animals

This includes every instance of `FarmAnimal` within a building.

TODO

### Slimes

This includes every slime within the Slime Hutch building.

TODO

## Output filtering

## Long-form output

## Adding new NPCs, game locations, or objects

You can edit the files within the `data` directory to add modded resources. Text files (`.txt`) require one entry per line. JSON (`.json`) files require valid JSON: double quotes and commas on all values except the last within an object or array.

