#!/usr/bin/env python3

"""
Constants and functions related to Stardew Valley
"""

NPC_UNKNOWN = "<unknown>"
LOCATION_UNKNOWN = "<unknown>"
ARTIFACT = ("Artifact Spot",)

NPCS = (
  "Abigail",
  "Alex",
  "Birdie",
  "Bouncer",
  "Caroline",
  "Clint",
  "Demetrius",
  "Dwarf",
  "Elliott",
  "Emily",
  "Evelyn",
  "George",
  "Gunther",
  "Gus",
  "Haley",
  "Harvey",
  "Henchman",
  "Jas",
  "Jodi",
  "Krobus",
  "Leah",
  "Lewis",
  "Linus",
  "Marlon",
  "Marnie",
  "Maru",
  "Mister Qi",
  "Pam",
  "Penny",
  "Pierre",
  "Robin",
  "Sam",
  "Sandy",
  "Sebastian",
  "Shane",
  "Vincent",
  "Willy",
  "Wizard",
  NPC_UNKNOWN
)

LOCATIONS = (
  "AbandonedJojaMart",
  "AdventureGuild",
  "AnimalShop",
  "Backwoods",
  "BathHousePool",
  "BathHouse_Entry",
  "BathHouse_MensLocker",
  "BathHouse_WomensLocker",
  "Beach",
  "BeachNightMarket",
  "Blacksmith",
  "BoatTunnel",
  "BugLand",
  "BusStop",
  "Caldera",
  "Cellar",
  "Club",
  "CommunityCenter",
  "Desert",
  "ElliottHouse",
  "Farm",
  "FarmCave",
  "FarmHouse",
  "FishShop",
  "Forest",
  "Greenhouse",
  "HaleyHouse",
  "HarveyRoom",
  "Hospital",
  "IslandEast",
  "IslandFarmCave",
  "IslandFarmHouse",
  "IslandFieldOffice",
  "IslandHut",
  "IslandLocation",
  "IslandNorth",
  "IslandShrine",
  "IslandSouth",
  "IslandSouthEast",
  "IslandSouthEastCave",
  "IslandWest",
  "IslandWestCave1",
  "JojaMart",
  "JoshHouse",
  "LeahHouse",
  "LeoTreeHouse",
  "LibraryMuseum",
  "ManorHouse",
  "MermaidHouse",
  "Mine",
  "Mountain",
  "MovieTheater",
  "Railroad",
  "Saloon",
  "SamHouse",
  "SandyHouse",
  "ScienceHouse",
  "SebastianRoom",
  "SeedShop",
  "Sewer",
  "SkullCave",
  "Submarine",
  "Summit",
  "Sunroom",
  "Tent",
  "Town",
  "Trailer",
  "Trailer_Big",
  "Tunnel",
  "WitchHut",
  "WitchSwamp",
  "WitchWarpCave",
  "WizardHouse",
  "WizardHouseBasement",
  "Woods",
  LOCATION_UNKNOWN
)

# Map Objects {{{0

FORAGE_SPRING = (
  "Wild Horseradish",
  "Daffodil",
  "Leek",
  "Dandelion",
  "Spring Onion",
  "Common Mushroom",
  "Morel",
  "Salmonberry"
)

FORAGE_SUMMER = (
  "Grape",
  "Spice Berry",
  "Sweet Pea",
  "Red Mushroom",
  "Fiddlehead Fern",
  "Common Mushroom"
)

FORAGE_FALL = (
  "Common Mushroom",
  "Wild Plum",
  "Hazelnut",
  "Blackberry",
  "Chanterelle",
  "Red Mushroom",
  "Purple Mushroom"
)

FORAGE_WINTER = (
  "Winter Root",
  "Crystal Fruit",
  "Snow Yam",
  "Crocus",
  "Holly"
)

FORAGE_BEACH = (
  "Nautilus Shell",
  "Coral",
  "Sea Urchin",
  "Rainbow Shell",
  "Clam",
  "Cockle",
  "Mussel",
  "Oyster",
  "Seaweed"
)

FORAGE_MINES = (
  "Red Mushroom",
  "Purple Mushroom",
  "Cave Carrot"
)

FORAGE_DESERT = (
  "Cactus Fruit",
  "Coconut"
)

FORAGE_ISLAND = (
  "Ginger",
  "Magma Cap"
)

FORAGE = set(
    FORAGE_SPRING +
    FORAGE_SUMMER +
    FORAGE_FALL +
    FORAGE_WINTER +
    FORAGE_BEACH +
    FORAGE_MINES +
    FORAGE_DESERT +
    FORAGE_ISLAND)

# 0}}}



# vim: set ts=2 sts=2 sw=2:
