#!/usr/bin/env python3

"""
Constants and functions related to Stardew Valley
"""

LOCATION_UNKNOWN = "<unknown>"

LOCATIONS = (
  "AbandonedJojaMart",
  "AdventureGuild",
  "BathHousePool",
  "Beach",
  "BeachNightMarket",
  "BoatTunnel",
  "BugLand",
  "BusStop",
  "Caldera",
  "Cellar",
  "Club",
  "CommunityCenter",
  "Desert",
  "Farm",
  "FarmCave",
  "FarmHouse",
  "FishShop",
  "Forest",
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
  "LibraryMuseum",
  "ManorHouse",
  "MermaidHouse",
  "Mine",
  "Mountain",
  "MovieTheater",
  "Railroad",
  "SeedShop",
  "Sewer",
  "Submarine",
  "Summit",
  "Town",
  "WizardHouse",
  "Woods",
  LOCATION_UNKNOWN
)

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

FORAGE = set(FORAGE_SPRING +
    FORAGE_SUMMER +
    FORAGE_FALL +
    FORAGE_WINTER +
    FORAGE_BEACH +
    FORAGE_MINES +
    FORAGE_DESERT +
    FORAGE_ISLAND)

# vim: set ts=2 sts=2 sw=2:
