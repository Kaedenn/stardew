# Stardew Valley Save Interrogation
The `savefile.py` module displays information contained within a Stardew Valley save file, such as the locations of forage objects, locations and progress of crops, and locations of terrain features.

# Usage

## List available farms

`python stardew.py --list`

## Examine a specific farm

`python stardew.py <farm> [arguments...]`

# Additional documentation coming soon

# Development

## Adding new NPCs, game locations, or objects

You can edit the files within the `data` directory to add modded resources. Text files (`.txt`) require one entry per line. JSON (`.json`) files require valid JSON: double quotes and commas on all values except the last within an object or array.

## Notes on `xsi:type` vs `<Name>` usage

This script uses the following logic to determine the name of a given NPC, game location, terrain feature, or object:

```python
def get_node_name(node):
  # Try the xsi:type attribute first
  if node.hasAttribute("xsi:type"):
    return node.getAttribute("xsi:type")
  # Try to find a <name> child element
  if node.hasChild("name"):
    return node.getChild("name").text
  # Try to find a <Name> child element
  if node.hasChild("Name"):
    return node.getChild("Name").text
  # Give up
  return None
```

This is because not all game locations have `xsi:type` attributes.

This affects NPCs, objects, and game locations.

Note that this causese a small issue as there are three separate `IslandLocation` locations: Qi's nut room, the shipwreck room, and the north mushroom cave. I'll probably refactor things to prefer the `<name>` element or something.

