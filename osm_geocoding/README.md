# OSM Geocoding Development

This folder contains experimental OpenStreetMap-based geocoding methods for enhanced local address resolution and road network distance calculations.

## Project Structure

```
osm_geocoding/
├── scripts/                    # OSM-based geocoding scripts
├── data/
│   ├── osm_extracts/          # Downloaded OSM PBF files
│   ├── processed/             # Converted/processed OSM data
│   └── output/                # Results from OSM method
├── setup/                     # Installation and setup scripts
├── docs/                      # Documentation for new method
└── tests/                     # Testing and validation scripts
```

## Objectives

1. **Local-First Approach**: Download OSM data once, operate completely offline
2. **Enhanced Accuracy**: Street-level geocoding with road network distances
3. **Non-Destructive**: Keep existing TIGER/ADDRFEAT system intact
4. **Comparative Testing**: A/B test OSM vs existing methods

## Target Coverage Areas

- Arkansas (primary research state)
- Tennessee, Mississippi, Louisiana, Texas, Oklahoma, Missouri (surrounding states)

## Status

🚧 **Development Phase** - Experimental implementation in progress

---

**Note**: This is a development branch. The main geocoding system remains in `/scripts/` folder.