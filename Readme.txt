# Project README

This project includes a script for generating FIPS codes for a list of addresses and calculating the distance and ADI (Area Deprivation Index) for those addresses. Below are the necessary steps and requirements to run this script successfully.

## Input File Requirements

1. **Data Excel File**: This file should contain at least one column named 'Address'. This column is case-sensitive and is used by the script to geocode addresses, generate FIPS codes, and calculate distances and ADI ranks.

## Necessary Software and Libraries

- Python 3.10 or later
- Libraries: pandas, geopandas, googlemaps, re, shapely, os

## Other Necessary Files and Keys

- Google Maps API key
- ADI lookup CSV file - included in the project folder, but can also be downloaded from [Neighborhood Atlas](https://www.neighborhoodatlas.medicine.wisc.edu/)
- Census block group shapefiles for each state included in the data set, available from the Census Bureau: [Census Bureau Shapefiles](https://www.census.gov/cgi-bin/geo/shapefiles/index.php?year=2023&layergroup=Block+Groups)

## Steps

1. Create a Google Account and Generate an API Key for Google Maps**:
   - Follow Google's documentation to create an API key for accessing the Google Maps services.

2. Prepare the Census Block Group Shapefiles**:
   - Download the shapefiles for each state you're interested in from the provided Census Bureau link.
   - Place each state's folder from the website into the parent folder along with the combined script.

3. Prepare the Data Excel File**:
   - Place the data Excel file in the parent folder. Ensure that there is an 'Address' column (case sensitive).

4. Update and Run the Combined Script**:
   - Update the file paths and API key in the combined script.
   - For the folders section, place the file path to each folder for each state.
   - Run the script. The final output file will be `Updated_with_distance_ADI.xlsx`.

## Additional Notes

- Ensure all file paths and API keys are correctly updated in the scripts before running them.
- For detailed instructions on generating a Google Maps API key and enabling the necessary API services, refer to Google's official documentation.

— Andrew Tran, MD