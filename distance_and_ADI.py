import pandas as pd
import googlemaps as gm
import re

# Insert google maps API key here
gmaps = gm.Client(key='API key')

# Specify the target address
target_address = 'Target Addresss'

# Load the data CSV file, may need to update the path/name. Make sure you have an Address column and a FIPS column
data_df = pd.read_excel('data file with Address and FIPS.xlsx', engine='openpyxl')

# Load the lookup CSV file, may need to update the path
lookup_df = pd.read_csv('./US_2021_ADI_Census_Block_Group_v4_0_1.csv')

# Convert lookup_df to a dictionary with FIPS as keys and (ADI_NATRANK, ADI_STATERNK) as values
lookup_dict = {row['FIPS']: (row['ADI_NATRANK'], row['ADI_STATERNK']) for index, row in lookup_df.iterrows()}

# Initialize columns for Distance, ADI_NATRANK, and ADI_STATERNK
data_df['ADI_NATRANK'] = pd.NA
data_df['ADI_STATERNK'] = pd.NA
data_df['Distance'] = pd.NA

# Function to check if an address is a PO Box
def is_po_box(address):
    # Define a regex pattern for a PO Box
    po_box_pattern = r'\b[P|p][.|\s]*[O|o][.|\s]*[B|b][O|o|0][X|x]\b|\b[P|p][O|o|0][S|s][T|t][.|\s]*[O|o][F|f|0][F|f][I|i][Cc][E|e]\b|\b[P|p][O|o|0][S|s][T|t][.|\s]*[B|b][O|o|0][X|x]\b'
    return re.search(po_box_pattern, address) is not None

# Function to fetch distance
def get_distance(source_address, target_address):
    try:
        # Get distance between source and target addresses
        distance_result = gmaps.distance_matrix(source_address, target_address, mode="driving", units='imperial')['rows'][0]['elements'][0]
        distance = distance_result['distance']['text']
        return distance
    except Exception as e:
        print(f"Error fetching distance for {source_address}: {e}")
        return None

# Iterate over the data_df
for index, row in data_df.iterrows():
    # Check if the address is a PO Box
    if is_po_box(row['Address']):
        continue  # Skip this iteration if it's a PO Box
    # Calculate distance if not a PO Box
    distance = get_distance(row['Address'], target_address)
    data_df.at[index, 'Distance'] = distance
    # Lookup ADI ranks if not a PO Box
    fips_code = row['FIPS']
    if fips_code in lookup_dict:
        data_df.at[index, 'ADI_NATRANK'] = lookup_dict[fips_code][0]
        data_df.at[index, 'ADI_STATERNK'] = lookup_dict[fips_code][1]

data_df = data_df.astype(str)

# Write the updated DataFrame to a new CSV file
data_df.to_excel('Updated_with_distance_ADI.xlsx', index=False, engine= 'openpyxl')
