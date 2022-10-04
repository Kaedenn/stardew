# Stardew Valley Save Interrogation
The `savefile.py` module displays information contained within a Stardew Valley save file, such as the locations of forage objects, terrain features, locations and progress of crops, animal types, names, and happiness, just to name a few.

NOTE: This README file (and the rest of this repository, for that matter) are a work in progress.

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

1. Specify the path using `-P,--save-path`. For example, if you keep your saves in `$HOME/games/StardewValley`, specify `python savefile.py -P "$HOME/games/StardewValley"` or `python savefile.py --save-path "$HOME/games/StardewValley"`.
2. Specify the path using the `STARDEW_PATH` environment variable. This is intended for developer use.

## Listing available save files

`python savefile.py --list`

`python savefile.py --save-path "<path>" --list`

# Usage

Note: Run `python savefile.py -h` for a more complete description of what can be done.

You can specify your save file by name, name and ID, or path. For instance, with the farm `Haven_316643857`, you can specify any of the following:

`python savefile.py Haven <arguments>`

`python savefile.py Haven_316643857 <arguments>`

`python savefile.py ~/.config/StardewValley/Saves/Haven_316643857 <arguments>`

## Linting

This repository supplies a pre-commit hook in the `scripts/` directory. See the comment at the top of the file for a complete description of what can be done.

That said, if you wish to use the included `pylintrc` file, invoke the following:

`git config hooks.pylintrc pylintrc`

## Pattern matching

The following arguments accept crude glob-like patterns: `-n,--name`, `-m,--map`, and `-t,--type`.

These patterns support two special symbols: `*` which matches zero or more characters, and a leading `!` which negates the match. For example,

* `-m Farm` limits output to things on the farm
* `-m '!Farm'` limits output to things anywhere except the farm
* `-m 'Island*' -m '!IslandWest'` limits output to things on the island, except for the island farm
* `-n '*Sprinkler'` limits output to any type of sprinkler

The single-quotes `''` around `!` are required if using a shell with history substitution, like bash. The single-quotes are required around `*` to avoid filename glob expansion.

## Output selection

Select output types using the `-i,--include` argument. In addition to those listed below, the following special values are also available:

| Value       | Behavior |
| ----------- | -------- |
| `alltrees`  | `-i trees -i fruittrees` |
| `features`  | `-i small -i large` |
| `all`       | Everything |

### `objects`

This includes forageables, artifact spots, machines, and more.

The `-l,--data-level` argument has no effect on the output.

The `-C,--category` argument has the following effects:
| Category | Behavior |
| -------- | -------- |
| `forage` | Only display objects included in the `FORAGE` set (see `data/forage.json`) |
| `artifact` | Only display artifact spots |

### `small`, `large`, `features`

This includes things part of the terrain: hoe dirt, flooring, trees, fruit trees, grass, and bushes. `features` includes both `small` and `large` terrain features.

The `-l,--data-level` argument has no effect on the output.

Because crops are small terrain features, all categories that apply to crops will also apply to small terrain features.

### `crops`

This includes every `HoeDirt` terrain feature with a `<crop>` child element present.

The `-l,--data-level` argument has the following effects:
| Level     | Effect |
| --------- | ------ |
| `brief`   | Output map name, crop name, dead status, and ready-for-harvest status |
| `normal`  | Include the string `"unfertilized"` if crop is not fertilized |
| `long`    | Include fertilizer type, seasons, whether or not this is a forage crop, regrow delay if the crop regrows, and the percent chance for extra crops at harvest, if non-zero |
| `full`    | Include numeric fertilizer ID, phase values, current phase, current phase day, minimum and maximum harvest count if applicable, and the exact chance for extra crops |

The `-C,--category` argument has the following effects:
| Category | Behavior |
| -------- | -------- |
| `cropready` | Only display crops ready for harvest |
| `cropdead` | Only display dead crops |
| `nofert` | Only display crops that are unfertilized |
| `fertnocrop` | Only display `HoeDirt` spots that are fertilized but lack a crop |

### `trees`

This includes every `Tree` terrain feature. Does not include fruit trees.

The `-l,--data-level` argument has the following effects:
| Level     | Effect |
| --------- | ------ |
| `brief`   | Output map name, tree kind, and growth stage |
| `normal`  | Include `"tapped"`, `"has seed"`, or `"fertilized"` if the tree is tapped, has a seed, or if the tree is fertilized, respectively |
| `long`    | Include tile position, numeric tree type, numeric growth stage, and health |
| `full`    | No additional behavior |

The `-C,--category` argument has no effect here.

### `fruittrees`

This includes every `FruitTree` terrain feature. Does not include normal trees.

The `-l,--data-level` argument has the following effects:
| Level     | Effect |
| --------- | ------ |
| `brief`   | Output map name, tree kind, whether or not the tree is a stump, coal days (see below), and either days until ready or current quality |
| `normal`  | Include season information and number of fruits |
| `long`    | Include tile position, numeric tree type, numberic growth stage, health, and age in years, months, and days |
| `full`    | No additional behavior |

When a tree is struck by lightning, it will produce coal instead of its normal fruit for a few days.

The `-C,--category` argument has no effect here.

### `animals`

This includes all `FarmAnimal`s within a building interior.

The `-l,--data-level` argument has the following effects:
| Level     | Effect |
| --------- | ------ |
| `brief`   | Output map name, animal type, animal name, and age |
| `normal`  | Include friendship and happiness values. If friendship is maxed, output `"max friendship"` instead of its value. If happiness is maxed, output `"max happiness"` instead of its value |
| `long`    | Include tile position |
| `full`    | Always output numeric friendship and happiness values. Disables the special logic for maxed values |

The `-C,--category` argument has no effect here.

### `slimes`

This includes slimes within the Slime Hutch buildings.

The `-l,--data-level` argument has the following effects:
| Level     | Effect |
| --------- | ------ |
| `brief`   | Output map name, slime type, current health, and maximum health |
| `normal`  | Include numeric `readyToMate` value |
| `long`    | Include both pixel coordinates and experience gained upon killing |
| `full`    | No additional behavior |

The `-C,--category` argument has no effect here.

### `machines`

This includes machines that contain an object and are on.

The `-l,--data-level` argument has no effect on the output.

The `-C,--category` argument has the following singular effect:
| Category | Behavior |
| -------- | -------- |
| `ready` | Only display machines ready for harvest |

## Output filtering

Filter results using the `-C,--category`, `-n,--name`, `-m,--map`, `-t,--type`, and `--at-pos`. All of these can be specified more than once.

### `-C,--category`

For convenience, certain `-C,--category` values will automatically add their necessary `-i,--include` value if the value isn't already given.

| `-C` argument   | `-i` argument | Behavior |
| --------------- | ------------- | -------- |
| `-C forage`     | `-i object`   | Select objects listed in the `FORAGE` set |
| `-C artifact`   | `-i object`   | Behave as if `-n "Artifact Spot"` was given |
| `-C cropready`  | `-i crops`    | Select crops that are ready for harvest |
| `-C cropdead`   | `-i crops`    | Select crops that are dead |
| `-C nofert`     | `-i crops`    | Select crops that lack fertilizer |
| `-C fertnocrop` | `-i small`    | Select fertilized tiles without crops |
| `-C ready`      | `-i machines` | Select machines that are ready |

Therefore, specifying `-C forage` will act as if you specified `-C forage -i object` regardless if `-i object` was given.

### `-n,--name`

This matches the value's display name. Quotes are required if the name contains spaces.

### `-m,--map`

For a list of supported maps, see `data/locations.txt`.

### `-t,--type`

This matches the `<type></type>` field that `object`s have. Sensible values should be those listed by the SMAPI `list_item_types` console command:

`BigCraftable`, `Boots`, `Clothing`, `Flooring`, `Furniture`, `Hat`, `Object`, `Ring`, `Tool`, `Wallpaper`, `Weapon`

### `--at-pos`

Limit output to things at the specified coordinate. For example, `--at-pos 12,13` would omit everything not at tile position `12,13`. This value can be specified more than once.

## Long-form output via `-L,--long`

There are two different kinds of long-form output: JSON and XML. Pass `-f rawxml` to generate XML.

<!-- TODO: document formatters and the indent argument -->

### XML long-form structure

```xml
<MapEntry>
  <Kind>one of the MAP_ITEM_TYPES values</Kind>
  <MapName>data/locations.txt entry</MapName>
  <Location>
    <X>x tile position</X>
    <Y>y tile position</Y>
  </Location>
  <Name>object name</Name>
  <-- object node goes here -->
</MapEntry>
```

The "object node" is exactly what the save file contains. Tag name and content depends on the `<Kind>` value.

## The `-c,--count` argument

## The `-s,--sort` argument

## Adding new NPCs, game locations, or objects

You can edit the files within the `data` directory to add modded resources. Text files (`.txt`) require one entry per line. JSON (`.json`) files require valid JSON: double quotes and commas on all values except the last within an object or array.

<!-- TODO: support custom files -->

## Diagnostics

<!-- TODO: document the -v, -vv arguments -->
