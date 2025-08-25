# OpenStreetMap Data Sources

## Primary Data Source: Geofabrik

**Website**: https://download.geofabrik.de/north-america/us/

### Target States Coverage

| State | Download URL | File Size (approx) | Update Frequency |
|-------|--------------|-------------------|------------------|
| Arkansas | `https://download.geofabrik.de/north-america/us/arkansas-latest.osm.pbf` | ~50 MB | Daily |
| Tennessee | `https://download.geofabrik.de/north-america/us/tennessee-latest.osm.pbf` | ~120 MB | Daily |
| Mississippi | `https://download.geofabrik.de/north-america/us/mississippi-latest.osm.pbf` | ~80 MB | Daily |
| Louisiana | `https://download.geofabrik.de/north-america/us/louisiana-latest.osm.pbf` | ~90 MB | Daily |
| Texas | `https://download.geofabrik.de/north-america/us/texas-latest.osm.pbf` | ~800 MB | Daily |
| Oklahoma | `https://download.geofabrik.de/north-america/us/oklahoma-latest.osm.pbf` | ~110 MB | Daily |
| Missouri | `https://download.geofabrik.de/north-america/us/missouri-latest.osm.pbf` | ~150 MB | Daily |

**Total Download Size**: ~1.4 GB

## Alternative Sources

### 1. Planet.openstreetmap.org
- **Full Planet**: https://planet.openstreetmap.org/
- **Regional Extracts**: https://planet.openstreetmap.org/extracts/
- **Update Frequency**: Weekly
- **Note**: Larger files, less frequent updates

### 2. BBBike.org
- **Custom Extracts**: https://extract.bbbike.org/
- **Advantage**: Custom geographic boundaries
- **Format Options**: Multiple formats (PBF, XML, Shapefile)

## OSM Data Structure for Geocoding

### Address Information in OSM
```
addr:housenumber    # House number
addr:street         # Street name
addr:city          # City name
addr:postcode      # ZIP/postal code
addr:state         # State
name               # Place/POI names
```

### Road Network Information
```
highway            # Road classification (primary, secondary, residential, etc.)
name               # Street name
maxspeed           # Speed limit
lanes              # Number of lanes
surface            # Road surface type
```

## Data Processing Tools

### Essential Tools for OSM Processing
1. **osmium-tool**: Fast OSM data processing
2. **osm2pgsql**: Import to PostGIS database
3. **osmosis**: Java-based OSM data manipulation
4. **gdal/ogr**: Convert between formats

### Python Libraries
1. **pyosmium**: Python OSM data processing
2. **osmnx**: OSM network analysis
3. **geopandas**: Spatial data processing
4. **shapely**: Geometric operations

## Data Quality Considerations

### Advantages of OSM Data
- ✅ Daily updates from local contributors
- ✅ High detail in urban/suburban areas
- ✅ Open source and free to use
- ✅ No licensing restrictions for local storage
- ✅ Better coverage of new developments than government data

### Potential Limitations
- ❌ Variable quality in rural areas
- ❌ Inconsistent address formatting
- ❌ Requires local validation and cleaning
- ❌ May lack some government-assigned addresses

## Storage Requirements

### Local Storage Planning
- **Raw OSM Data**: ~1.4 GB for all 7 states
- **Processed Database**: ~3-5 GB (PostGIS import)
- **Indexes and Cache**: ~1 GB
- **Total Estimated**: ~6-8 GB disk space

## Update Strategy

### Recommended Approach
1. **Initial Download**: Full state extracts
2. **Incremental Updates**: Daily diff files from Geofabrik
3. **Full Refresh**: Monthly or quarterly
4. **Validation**: Compare with existing TIGER data for accuracy

---

**Next Steps**: Create automated download scripts for these data sources.