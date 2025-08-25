# OSM Geocoding Usage Guide

Complete guide for using the OpenStreetMap-based geocoding system as an alternative to TIGER/ADDRFEAT methods.

## Quick Start

### 1. Install Dependencies
```bash
cd osm_geocoding/setup
python install.py --minimal
```

### 2. Download OSM Data
```bash
# Download Arkansas data (primary state)
python download_osm_data.py --state arkansas

# Download all target states
python download_osm_data.py --all
```

### 3. Test the System
```bash
cd ../tests
python test_osm_geocoding.py --method accuracy
```

### 4. Run Distance Calculations
```bash
cd ../scripts
python osm_distance_calculator.py
```

## Detailed Usage

### Setup and Installation

#### System Requirements
- Python 3.8+
- 6-8 GB disk space for all state data
- 4+ GB RAM for processing large datasets

#### Installing Dependencies
```bash
# Check what you need
python setup/install.py --check

# Install minimal OSM dependencies
python setup/install.py --minimal

# Install everything including optional packages
python setup/install.py --full

# Get system dependency info
python setup/install.py --system-info
```

#### Download OSM Data
```bash
# List available states
python setup/download_osm_data.py --list

# Download specific state
python setup/download_osm_data.py --state arkansas

# Download all target states (~1.4 GB)
python setup/download_osm_data.py --all

# Force re-download existing files
python setup/download_osm_data.py --state arkansas --force
```

### Geocoding Addresses

#### Basic Geocoding
```python
from osm_geocoder import OSMGeocoder

# Initialize geocoder
geocoder = OSMGeocoder()

# Load data for your states
geocoder.load_osm_data(['arkansas', 'tennessee'])

# Geocode a single address
result = geocoder.geocode("123 Main Street, Little Rock, AR")

if result:
    print(f"Coordinates: {result.latitude}, {result.longitude}")
    print(f"Confidence: {result.confidence}")
    print(f"Match type: {result.match_type}")
```

#### Batch Geocoding
```python
addresses = [
    "500 Woodlane Street, Little Rock, AR",
    "1 University Avenue, Fayetteville, AR",
    "1000 Main Street, Conway, AR"
]

results = geocoder.geocode_batch(addresses)

for i, result in enumerate(results):
    if result:
        print(f"{addresses[i]} -> {result.latitude}, {result.longitude}")
```

### Distance Calculations

#### Basic Distance Calculation
```python
from osm_routing import OSMRouter

# Initialize router
router = OSMRouter()

# Load road network
router.load_road_network(['arkansas'])

# Calculate distances
origin = (34.7465, -92.2896)  # Little Rock
destination = (36.0822, -94.1719)  # Fayetteville

result = router.calculate_distance(origin, destination)

print(f"Geodesic distance: {result.geodesic_distance_miles:.2f} miles")
if result.road_distance_miles:
    print(f"Road distance: {result.road_distance_miles:.2f} miles")
    print(f"Travel time: {result.travel_time_minutes:.1f} minutes")
```

#### Batch Distance Calculations
```python
destinations = [
    (36.0822, -94.1719),  # Fayetteville
    (35.0887, -92.4421),  # Conway
    (34.5037, -93.0552)   # Hot Springs
]

results = router.calculate_distances_batch(origin, destinations)

for i, result in enumerate(results):
    print(f"Destination {i+1}: {result.geodesic_distance_miles:.2f} miles")
```

### Complete Workflow

#### Using the Complete Calculator
```python
from osm_distance_calculator import OSMDistanceCalculator

# Initialize calculator
calculator = OSMDistanceCalculator()

# Setup with your data
success = calculator.setup(
    states=['arkansas', 'tennessee'],
    input_file='data/input/data.xlsx',
    target_address='500 Woodlane Street, Little Rock, AR'
)

if success:
    # Process all addresses
    results_df = calculator.process_addresses()
    
    # Save results
    output_file = calculator.save_results(results_df)
    print(f"Results saved to: {output_file}")
```

#### Command Line Usage
```bash
# Interactive mode
python osm_distance_calculator.py

# You'll be prompted for:
# - Target address
# - Input file path (default: data/input/data.xlsx)
# - States to load (default: arkansas)
```

## Testing and Validation

### Accuracy Testing
```bash
# Test geocoding accuracy
python tests/test_osm_geocoding.py --method accuracy

# Test routing accuracy
python tests/test_osm_geocoding.py --method routing

# Performance benchmark
python tests/test_osm_geocoding.py --method performance --benchmark-size 500

# Run all tests
python tests/test_osm_geocoding.py --method all
```

### Method Comparison
```bash
# Compare OSM vs existing methods
python tests/compare_methods.py --test-size medium

# Specify output file
python tests/compare_methods.py --output comparison_results.xlsx
```

## Performance Optimization

### Caching
The system automatically caches:
- **Road network graphs**: Saved after first load
- **Distance calculations**: Cached for repeated queries
- **Geocoding results**: Optional caching available

### Memory Management
```python
# For large datasets, process in chunks
chunk_size = 1000
total_addresses = len(address_list)

for i in range(0, total_addresses, chunk_size):
    chunk = address_list[i:i+chunk_size]
    results = geocoder.geocode_batch(chunk)
    # Process results
    # Clear cache if needed
```

### Multi-State Loading
```python
# Load multiple states efficiently
states = ['arkansas', 'tennessee', 'mississippi']

# This loads and caches all state data
geocoder.load_osm_data(states)
router.load_road_network(states)
```

## Configuration Options

### Data Directories
```python
from pathlib import Path

# Custom data directory
custom_data_dir = Path("/custom/path/to/osm/data")
geocoder = OSMGeocoder(data_dir=custom_data_dir)

# Custom cache directory
custom_cache_dir = Path("/custom/cache/path")
router = OSMRouter(cache_dir=custom_cache_dir)
```

### Geocoding Confidence Thresholds
```python
# Filter results by confidence
results = geocoder.geocode_batch(addresses)
high_confidence = [r for r in results if r and r.confidence > 0.8]
medium_confidence = [r for r in results if r and 0.5 < r.confidence <= 0.8]
```

## Integration with Existing System

### Fallback Strategy
```python
# Use OSM as primary, existing methods as fallback
def geocode_with_fallback(address):
    # Try OSM first
    osm_result = osm_geocoder.geocode(address)
    if osm_result and osm_result.confidence > 0.7:
        return osm_result
    
    # Fall back to ZIP centroid
    zip_result = zip_geocoder.geocode(address)
    return zip_result
```

### Hybrid Distance Calculation
```python
def calculate_hybrid_distance(origin, destination):
    # Get both geodesic and road distances
    result = router.calculate_distance(origin, destination)
    
    return {
        'geodesic_miles': result.geodesic_distance_miles,
        'road_miles': result.road_distance_miles,
        'travel_time_minutes': result.travel_time_minutes,
        'method_used': result.calculation_method
    }
```

## Troubleshooting

### Common Issues

#### "OSM data file not found"
```bash
# Download the required state data
python setup/download_osm_data.py --state [STATE_NAME]
```

#### "Failed to load OSM data"
```bash
# Check file integrity
ls -la data/osm_extracts/
# Re-download if corrupted
python setup/download_osm_data.py --state [STATE_NAME] --force
```

#### "No route found" for distance calculations
- This is normal for very remote areas
- System falls back to geodesic distance
- Consider using larger geographic coverage

#### Memory issues with large datasets
- Process addresses in smaller batches
- Clear caches periodically
- Consider using a machine with more RAM

### Performance Issues

#### Slow geocoding
```python
# Pre-load all required states
geocoder.load_osm_data(['arkansas', 'tennessee', 'mississippi'])

# Use batch processing instead of single calls
results = geocoder.geocode_batch(address_list)
```

#### Slow routing
```python
# Ensure road network is cached
router.load_road_network(states, use_cache=True)

# Save cache after processing
router.save_cache()
```

## Output Formats

### Geocoding Results
```python
# GeocodeResult attributes
result.latitude          # float
result.longitude         # float  
result.confidence        # 0.0 to 1.0
result.match_type        # 'exact', 'interpolated', 'approximate'
result.source           # 'osm_building', 'osm_address', 'osm_street'
result.matched_address  # string description
result.osm_id          # OSM element ID (optional)
```

### Distance Results
```python
# DistanceResult attributes
result.geodesic_distance_miles    # float (always available)
result.road_distance_miles        # float (if route found)
result.travel_time_minutes        # float (if route found)
result.route_found               # boolean
result.calculation_method        # 'geodesic' or 'road_network'
result.intermediate_points       # list of (lat, lon) if requested
```

### Excel Output Columns
- **MRN**: Original identifier
- **Address**: Original address string
- **Longitude/Latitude**: Geocoded coordinates
- **Geocoding_Method**: Method used (osm_address, osm_street, etc.)
- **Geocoding_Confidence**: 0.0 to 1.0 confidence score
- **FIPS**: Census block group FIPS code
- **ADI_NATRANK/ADI_STATERNK**: ADI rankings
- **Distance_Geodesic_Miles**: Straight-line distance
- **Distance_Road_Miles**: Road network distance (if available)
- **Travel_Time_Minutes**: Estimated travel time

## Advanced Usage

### Custom Address Parsing
```python
from osm_geocoder import OSMAddressParser

parser = OSMAddressParser()
parsed = parser.parse_address("123 Main St, Little Rock, AR 72201")

# Parsed components:
# parsed['house_number'] -> '123'
# parsed['street'] -> 'MAIN ST'
# parsed['city'] -> 'LITTLE ROCK'
# parsed['state'] -> 'AR'
# parsed['zipcode'] -> '72201'
```

### Direct OSM Data Access
```python
# Access raw OSM data after loading
addresses_df = geocoder.addresses_df
streets_df = geocoder.streets_df
buildings_df = geocoder.buildings_df

# Filter and analyze
arkansas_streets = streets_df[streets_df['state'] == 'AR']
residential_streets = streets_df[streets_df['highway'] == 'residential']
```

### Route Analysis
```python
# Get detailed route information
result = router.calculate_distance(origin, destination, include_route=True)

if result.intermediate_points:
    print(f"Route has {len(result.intermediate_points)} waypoints")
    for point in result.intermediate_points:
        print(f"  {point[0]:.6f}, {point[1]:.6f}")
```

## Best Practices

1. **Always load required states first** before processing
2. **Use batch processing** for multiple addresses
3. **Set confidence thresholds** based on your accuracy requirements
4. **Cache results** for repeated processing
5. **Monitor memory usage** with large datasets
6. **Validate critical results** manually when possible
7. **Keep OSM data updated** monthly or quarterly

---

For more detailed technical information, see the individual script documentation and the `/docs/` folder.