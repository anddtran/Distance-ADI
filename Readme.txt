# Project README

This project includes a script for generating FIPS codes for a list of addresses and calculating the distance and ADI (Area Deprivation Index) for those addresses. Below are the necessary steps and requirements to run this script successfully.

## Input File Requirements

1. Data Excel File**: This file should contain at least one column named 'Address'. This column is case-sensitive and is used by the script to geocode addresses, generate FIPS codes, and calculate distances and ADI ranks.

## Necessary Software and Libraries

- Python 3.10 or later
- Libraries: pandas, googlemaps, re, requests, math, concurrent.futures, os

## Other Necessary Files and Keys

- Google Maps API key
- ADI lookup CSV file - included in the project folder, but can also be downloaded from [Neighborhood Atlas](https://www.neighborhoodatlas.medicine.wisc.edu/)

## Steps

1. Create a Google Account and Generate an API Key for Google Maps**:
   - Follow Google's documentation to create an API key for accessing the Google Maps services.

2. Prepare the Data Excel File**:
   - Ensure the data Excel file contains an 'Address' column (case sensitive).
   - Place the data Excel file in the same folder as the script.

3. Run the Script**:
   - When you run the script, you will be prompted to enter your Google Maps API key, the target address, and the path to the data Excel file.
   - The ADI lookup CSV file should be in the same folder as the script.
   - The final output file, `Updated_with_distance_ADI.xlsx`, will be generated in the same folder as the script.

## Additional Notes

- Ensure all file paths and API keys are correctly updated in the scripts before running them.
- For detailed instructions on generating a Google Maps API key and enabling the necessary API services, refer to Google's official documentation.

— Andrew Tran, MD