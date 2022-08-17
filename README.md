# Stardew Valley Save Interrogation
The `savefile.py` module displays information contained within a Stardew Valley save file, such as the locations of forage objects, locations and progress of crops, and locations of terrain features.

# Save files

There are a couple ways to specify where you keep your Stardew Valley saves. By default, `savefile.py` will determine the default location based on your OS. If that fails, or if you have your saves stored somewhere else, you have two options:

1. Specify the path using `-P,--save-path`. For example, if you keep your saves in `$HOME/games/StardewValley`, specify `python stardew.py -C "$HOME/games/StardewValley"` or `python stardew.py --save-path "$HOME/games/StardewValley"`.
2. Specify the path using the `STARDEW_PATH` environment variable. This is intended for developer use.

# List available farms

`python stardew.py --list`

`python stardew.py --save-path "<path>" --list`

# Examine a specific farm

By name: `python stardew.py <farm> <arguments>`

By path: `python stardew.py "C:\games\StardewValley\<farm>" <arguments>"`

## Show forageables

`python stardew.py <farm> -C forage`

## Show artifact spots

`python stardew.py <farm> -C artifact`

`python stardew.py <farm> -n "Artifact Spot"`

# Additional documentation coming soon

# Development

## Adding new NPCs, game locations, or objects

You can edit the files within the `data` directory to add modded resources. Text files (`.txt`) require one entry per line. JSON (`.json`) files require valid JSON: double quotes and commas on all values except the last within an object or array.

