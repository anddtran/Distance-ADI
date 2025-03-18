# Distance-ADI Project

This project provides three different scripts for calculating Area Deprivation Index (ADI) and distances for a list of addresses. Each script offers different trade-offs between API usage and local processing.

## Script Descriptions

### 1. localrun.py (Fully Local Version)
- Uses Nominatim for geocoding (no API key required)
- Uses local Census Block Group shapefile for FIPS lookup
- Best for: Users who want to avoid API usage and costs
- Requirements: Larger local storage for shapefile

### 2. ADI_Distance.py (API Version)
- Uses Google Maps API for geocoding and distance calculations
- Uses Census TIGERweb API for FIPS lookup
- Best for: Users who need highest accuracy and don't mind API costs
- Requirements: Google Maps API key

### 3. ADI_Distance_noAPI.py (Hybrid Version)
- Uses Google Maps API for geocoding and distance calculations
- Uses local shapefiles for FIPS lookup
- Best for: Users who want to reduce API calls while maintaining Google's geocoding accuracy
- Requirements: Google Maps API key and local storage for shapefile

## Setup Instructions

### Required Python Packages
```bash
pip install pandas geopandas geopy googlemaps shapely requests openpyxl
```

### Required Data Files

1. **Input Excel File (data.xlsx)**
   - Must contain an 'Address' column (case-sensitive)
   - Place in the same directory as the scripts
   - Format: One address per row in the Address column

2. **ADI Lookup File**
   - Included: `US_2021_ADI_Census_Block_Group_v4_0_1.csv`
   - Can be downloaded from [Neighborhood Atlas](https://www.neighborhoodatlas.medicine.wisc.edu/) if needed

3. **Census Block Group Shapefile** (Required for localrun.py and ADI_Distance_noAPI.py)
   - Download from: https://www.census.gov/cgi-bin/geo/shapefiles/index.php
   - Select: "Block Groups"
   - Select: "2020"
   - Download the national file
   - Extract and rename to `cb_2020_us_bg_500k.shp`
   - Place in the project directory

### Google Maps API Key (Required for ADI_Distance.py and ADI_Distance_noAPI.py)
1. Create a Google Cloud Project
2. Enable the following APIs:
   - Geocoding API
   - Distance Matrix API
3. Create credentials (API key)
4. Keep your API key secure

## Running the Scripts

### For localrun.py (Fully Local)
```bash
python localrun.py
# You will be prompted for:
# - Target address
```

### For ADI_Distance.py (API Version)
```bash
python ADI_Distance.py
# You will be prompted for:
# - Google Maps API key
# - Target address
```

### For ADI_Distance_noAPI.py (Hybrid Version)
```bash
python ADI_Distance_noAPI.py
# You will be prompted for:
# - Google Maps API key
# - Target address
```

## Output

All scripts generate an Excel file containing:
- Original address data
- FIPS codes
- ADI National Rank
- ADI State Rank
- Distance to target address

The output file will be named `Updated_with_distance_ADI.xlsx` or as specified in the script.

## Notes
- PO Box addresses are automatically detected and skipped
- Distance calculations use driving distance where applicable
- All scripts use multi-threading for improved performance
- Error handling is implemented for geocoding and API requests

## Choosing the Right Script

1. Choose `localrun.py` if you:
   - Want to avoid API costs
   - Don't mind slightly less accurate geocoding
   - Have storage space for the national shapefile

2. Choose `ADI_Distance.py` if you:
   - Need highest accuracy
   - Don't mind API costs
   - Want to minimize local storage usage

3. Choose `ADI_Distance_noAPI.py` if you:
   - Want to reduce API usage
   - Still need Google's geocoding accuracy
   - Have storage space for the national shapefile

— Andrew Tran, MD
