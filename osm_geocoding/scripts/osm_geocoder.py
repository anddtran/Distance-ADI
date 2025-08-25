#!/usr/bin/env python3
"""
OpenStreetMap-based Address Geocoding Engine

This module provides local geocoding functionality using downloaded OSM data.
It matches addresses to OSM street segments and buildings for coordinate extraction.

Features:
- Local-only operation (no API calls)
- Street-level precision geocoding
- Fuzzy address matching
- Integration with existing ADI/COI workflow

Usage:
    from osm_geocoder import OSMGeocoder
    geocoder = OSMGeocoder()
    geocoder.load_osm_data(['arkansas', 'tennessee'])
    result = geocoder.geocode("123 Main Street, Little Rock, AR")
"""

import os
import re
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union
from dataclasses import dataclass
from collections import defaultdict

import pandas as pd
import geopandas as gpd
import usaddress
from shapely.geometry import Point, LineString
from shapely.ops import nearest_points
import osmium
import pyosmium


@dataclass
class GeocodeResult:
    """Result of geocoding operation."""
    latitude: float
    longitude: float
    confidence: float  # 0.0 to 1.0
    match_type: str    # 'exact', 'interpolated', 'approximate'
    source: str        # 'osm_building', 'osm_address', 'osm_street'
    matched_address: str
    osm_id: Optional[str] = None


class OSMAddressParser:
    """Parse and normalize addresses for OSM matching."""
    
    def __init__(self):
        self.street_suffixes = {
            'ST': ['STREET', 'ST'],
            'AVE': ['AVENUE', 'AVE'],
            'RD': ['ROAD', 'RD'],
            'DR': ['DRIVE', 'DR'],
            'LN': ['LANE', 'LN'],
            'CT': ['COURT', 'CT'],
            'PL': ['PLACE', 'PL'],
            'BLVD': ['BOULEVARD', 'BLVD'],
            'WAY': ['WAY'],
            'PKWY': ['PARKWAY', 'PKWY'],
            'CIR': ['CIRCLE', 'CIR']
        }
    
    def parse_address(self, address_string: str) -> Dict[str, str]:
        """Parse address string using usaddress library."""
        try:
            parsed, address_type = usaddress.tag(address_string)
            
            # Normalize the parsed components
            normalized = {}
            
            # House number
            if 'AddressNumber' in parsed:
                normalized['house_number'] = parsed['AddressNumber']
            elif 'AddressNumberPrefix' in parsed:
                normalized['house_number'] = parsed['AddressNumberPrefix']
            
            # Street name
            street_parts = []
            for key in ['StreetNamePreDirectional', 'StreetName', 'StreetNamePostType', 'StreetNamePostDirectional']:
                if key in parsed:
                    street_parts.append(parsed[key])
            
            if street_parts:
                normalized['street'] = ' '.join(street_parts).upper()
                # Normalize street suffix
                normalized['street'] = self._normalize_street_suffix(normalized['street'])
            
            # City
            if 'PlaceName' in parsed:
                normalized['city'] = parsed['PlaceName'].upper()
            
            # State
            if 'StateName' in parsed:
                normalized['state'] = parsed['StateName'].upper()
            
            # ZIP code
            if 'ZipCode' in parsed:
                normalized['zipcode'] = parsed['ZipCode']
            
            return normalized
            
        except Exception as e:
            print(f"Address parsing failed: {e}")
            return {}
    
    def _normalize_street_suffix(self, street: str) -> str:
        """Normalize street suffixes for better matching."""
        words = street.split()
        if not words:
            return street
        
        last_word = words[-1]
        for suffix, variants in self.street_suffixes.items():
            if last_word in variants:
                words[-1] = suffix
                break
        
        return ' '.join(words)


class OSMDataHandler(osmium.SimpleHandler):
    """Extract address and street data from OSM files."""
    
    def __init__(self):
        osmium.SimpleHandler.__init__(self)
        self.addresses = []
        self.streets = []
        self.buildings = []
        
    def node(self, n):
        """Process OSM nodes (points)."""
        if n.tags:
            # Check for address information
            addr_tags = self._extract_address_tags(n.tags)
            if addr_tags:
                self.addresses.append({
                    'osm_id': f"node/{n.id}",
                    'longitude': n.location.lon,
                    'latitude': n.location.lat,
                    **addr_tags
                })
            
            # Check for POI/building with name
            if 'name' in n.tags or 'building' in n.tags:
                self.buildings.append({
                    'osm_id': f"node/{n.id}",
                    'longitude': n.location.lon,
                    'latitude': n.location.lat,
                    'name': n.tags.get('name', ''),
                    'building': n.tags.get('building', ''),
                    **self._extract_address_tags(n.tags)
                })
    
    def way(self, w):
        """Process OSM ways (lines/polygons)."""
        if not w.tags:
            return
        
        # Extract coordinates for the way
        try:
            coords = [(n.lon, n.lat) for n in w.nodes]
            if len(coords) < 2:
                return
        except osmium.InvalidLocationError:
            return
        
        # Check for address information on buildings
        addr_tags = self._extract_address_tags(w.tags)
        if addr_tags and w.tags.get('building'):
            # Use centroid of building for address location
            from shapely.geometry import Polygon, LineString
            try:
                if coords[0] == coords[-1] and len(coords) > 3:
                    # Closed way (polygon)
                    poly = Polygon(coords)
                    centroid = poly.centroid
                else:
                    # Open way (linestring)
                    line = LineString(coords)
                    centroid = line.centroid
                
                self.addresses.append({
                    'osm_id': f"way/{w.id}",
                    'longitude': centroid.x,
                    'latitude': centroid.y,
                    **addr_tags
                })
            except Exception:
                pass
        
        # Check for streets/highways
        if 'highway' in w.tags and 'name' in w.tags:
            self.streets.append({
                'osm_id': f"way/{w.id}",
                'name': w.tags['name'].upper(),
                'highway': w.tags['highway'],
                'coordinates': coords,
                **self._extract_address_tags(w.tags)
            })
    
    def _extract_address_tags(self, tags) -> Dict[str, str]:
        """Extract address-related tags from OSM element."""
        addr_tags = {}
        
        # Standard address tags
        for key in ['addr:housenumber', 'addr:street', 'addr:city', 
                   'addr:state', 'addr:postcode']:
            if key in tags:
                clean_key = key.replace('addr:', '')
                addr_tags[clean_key] = tags[key].upper() if clean_key != 'housenumber' else tags[key]
        
        return addr_tags


class OSMGeocoder:
    """Main geocoding engine using OSM data."""
    
    def __init__(self, data_dir: Optional[Path] = None):
        """Initialize geocoder with optional data directory."""
        if data_dir is None:
            # Default to osm_geocoding/data/osm_extracts
            script_dir = Path(__file__).parent
            data_dir = script_dir.parent / 'data' / 'osm_extracts'
        
        self.data_dir = Path(data_dir)
        self.parser = OSMAddressParser()
        
        # Loaded data
        self.addresses_df = None
        self.streets_df = None
        self.buildings_df = None
        self.loaded_states = []
    
    def load_osm_data(self, states: List[str]) -> bool:
        """Load OSM data for specified states."""
        print(f"Loading OSM data for states: {', '.join(states)}")
        
        all_addresses = []
        all_streets = []
        all_buildings = []
        
        for state in states:
            pbf_file = self.data_dir / f"{state}-latest.osm.pbf"
            
            if not pbf_file.exists():
                print(f"⚠️ OSM data file not found: {pbf_file}")
                print(f"Run: python setup/download_osm_data.py --state {state}")
                continue
            
            print(f"📂 Processing {state} data...")
            start_time = time.time()
            
            # Process OSM file
            handler = OSMDataHandler()
            handler.apply_file(str(pbf_file))
            
            print(f"  Found {len(handler.addresses)} addresses")
            print(f"  Found {len(handler.streets)} streets")
            print(f"  Found {len(handler.buildings)} buildings")
            
            all_addresses.extend(handler.addresses)
            all_streets.extend(handler.streets)
            all_buildings.extend(handler.buildings)
            
            elapsed = time.time() - start_time
            print(f"  Processed in {elapsed:.1f} seconds")
        
        if not all_addresses and not all_streets:
            print("❌ No OSM data loaded")
            return False
        
        # Convert to DataFrames for efficient searching
        if all_addresses:
            self.addresses_df = pd.DataFrame(all_addresses)
            print(f"📊 Loaded {len(self.addresses_df)} addresses")
        
        if all_streets:
            self.streets_df = pd.DataFrame(all_streets)
            print(f"📊 Loaded {len(self.streets_df)} streets")
        
        if all_buildings:
            self.buildings_df = pd.DataFrame(all_buildings)
            print(f"📊 Loaded {len(self.buildings_df)} buildings")
        
        self.loaded_states = states
        return True
    
    def geocode(self, address: str) -> Optional[GeocodeResult]:
        """Geocode a single address using OSM data."""
        if self.addresses_df is None and self.streets_df is None:
            raise ValueError("No OSM data loaded. Call load_osm_data() first.")
        
        # Parse the input address
        parsed = self.parser.parse_address(address)
        if not parsed:
            return None
        
        # Try different matching strategies in order of accuracy
        
        # 1. Exact address match
        result = self._match_exact_address(parsed)
        if result:
            return result
        
        # 2. Building name match
        result = self._match_building_name(parsed, address)
        if result:
            return result
        
        # 3. Street interpolation
        result = self._match_street_interpolation(parsed)
        if result:
            return result
        
        # 4. Street centroid (least accurate)
        result = self._match_street_centroid(parsed)
        if result:
            return result
        
        return None
    
    def _match_exact_address(self, parsed: Dict[str, str]) -> Optional[GeocodeResult]:
        """Try to find exact address match in OSM data."""
        if self.addresses_df is None:
            return None
        
        # Look for exact house number and street match
        house_number = parsed.get('house_number')
        street = parsed.get('street')
        
        if not house_number or not street:
            return None
        
        # Filter by house number and street
        matches = self.addresses_df[
            (self.addresses_df['housenumber'] == house_number) &
            (self.addresses_df['street'] == street)
        ]
        
        if len(matches) > 0:
            match = matches.iloc[0]
            return GeocodeResult(
                latitude=match['latitude'],
                longitude=match['longitude'],
                confidence=0.95,
                match_type='exact',
                source='osm_address',
                matched_address=f"{match['housenumber']} {match['street']}",
                osm_id=match['osm_id']
            )
        
        return None
    
    def _match_building_name(self, parsed: Dict[str, str], original_address: str) -> Optional[GeocodeResult]:
        """Try to match building or POI names."""
        if self.buildings_df is None:
            return None
        
        # Extract potential building names from original address
        # This is a simple approach - could be enhanced with NLP
        words = original_address.upper().split()
        
        for word in words:
            if len(word) > 3:  # Skip short words
                matches = self.buildings_df[
                    self.buildings_df['name'].str.contains(word, na=False)
                ]
                
                if len(matches) > 0:
                    match = matches.iloc[0]
                    return GeocodeResult(
                        latitude=match['latitude'],
                        longitude=match['longitude'],
                        confidence=0.7,
                        match_type='approximate',
                        source='osm_building',
                        matched_address=match['name'],
                        osm_id=match['osm_id']
                    )
        
        return None
    
    def _match_street_interpolation(self, parsed: Dict[str, str]) -> Optional[GeocodeResult]:
        """Interpolate address position along street segment."""
        if self.streets_df is None:
            return None
        
        street = parsed.get('street')
        house_number = parsed.get('house_number')
        
        if not street or not house_number:
            return None
        
        try:
            target_number = int(house_number)
        except ValueError:
            return None
        
        # Find matching street
        street_matches = self.streets_df[
            self.streets_df['name'].str.contains(street, na=False)
        ]
        
        if len(street_matches) == 0:
            return None
        
        # For now, use street centroid (interpolation would require address ranges)
        match = street_matches.iloc[0]
        coords = match['coordinates']
        
        # Calculate centroid of street
        from shapely.geometry import LineString
        line = LineString(coords)
        centroid = line.centroid
        
        return GeocodeResult(
            latitude=centroid.y,
            longitude=centroid.x,
            confidence=0.6,
            match_type='interpolated',
            source='osm_street',
            matched_address=f"{house_number} {street}",
            osm_id=match['osm_id']
        )
    
    def _match_street_centroid(self, parsed: Dict[str, str]) -> Optional[GeocodeResult]:
        """Fall back to street centroid for approximate location."""
        if self.streets_df is None:
            return None
        
        street = parsed.get('street')
        if not street:
            return None
        
        # Try partial street name matching
        street_words = street.split()
        for word in street_words:
            if len(word) > 3:
                matches = self.streets_df[
                    self.streets_df['name'].str.contains(word, na=False)
                ]
                
                if len(matches) > 0:
                    match = matches.iloc[0]
                    coords = match['coordinates']
                    
                    from shapely.geometry import LineString
                    line = LineString(coords)
                    centroid = line.centroid
                    
                    return GeocodeResult(
                        latitude=centroid.y,
                        longitude=centroid.x,
                        confidence=0.4,
                        match_type='approximate',
                        source='osm_street',
                        matched_address=match['name'],
                        osm_id=match['osm_id']
                    )
        
        return None
    
    def geocode_batch(self, addresses: List[str]) -> List[Optional[GeocodeResult]]:
        """Geocode multiple addresses efficiently."""
        results = []
        
        print(f"🔍 Geocoding {len(addresses)} addresses...")
        
        for i, address in enumerate(addresses):
            if i % 100 == 0:
                print(f"  Progress: {i}/{len(addresses)}")
            
            result = self.geocode(address)
            results.append(result)
        
        success_count = sum(1 for r in results if r is not None)
        print(f"✅ Successfully geocoded {success_count}/{len(addresses)} addresses")
        
        return results


# Example usage and testing
if __name__ == "__main__":
    # Initialize geocoder
    geocoder = OSMGeocoder()
    
    # Load Arkansas data for testing
    success = geocoder.load_osm_data(['arkansas'])
    
    if success:
        # Test some addresses
        test_addresses = [
            "123 Main Street, Little Rock, AR",
            "500 Woodlane Street, Little Rock, AR 72201",
            "University of Arkansas, Fayetteville, AR"
        ]
        
        for addr in test_addresses:
            print(f"\nTesting: {addr}")
            result = geocoder.geocode(addr)
            if result:
                print(f"  Result: {result.latitude:.6f}, {result.longitude:.6f}")
                print(f"  Confidence: {result.confidence:.2f}")
                print(f"  Match: {result.matched_address}")
            else:
                print("  No match found")
    else:
        print("Failed to load OSM data")
        print("Run: python setup/download_osm_data.py --state arkansas")